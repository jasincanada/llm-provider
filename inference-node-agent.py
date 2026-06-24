#!/usr/bin/env python3
"""Enroll and heartbeat a GPU / Ollama worker with the LLM gateway control plane.

Modes:
  1) Provider handshake (default for llm-provider) — no API keys to copy.
     Provider signs in on /provider/, approves device while agent polls.
  2) Legacy INW_TOKEN — owner/admin-created nodes (LAN operators).

Environment:
  GATEWAY_URL                — e.g. https://llm.cryptocomputer.ca or http://192.168.1.160:18081
  HANDSHAKE                  — 1 to use provider handshake (default when INW_TOKEN unset)
  DEVICE_ID                  — optional; auto-generated dev_… if unset
  INW_TOKEN                  — legacy inw_… enrollment token (skips handshake)
  OLLAMA_URL                 — local Ollama, e.g. http://ollama:11434
  INFERENCE_LAN_URL          — LAN fallback when gateway is not on worker Docker network
  VRAM_GB, HEARTBEAT_S
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

TOKEN_FILE = Path(os.environ.get("INW_TOKEN_FILE", "/data/inw_token"))


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _host_header(gateway_url: str) -> str:
    parsed = urlparse(gateway_url)
    host = parsed.hostname or ""
    if parsed.port:
        return f"{host}:{parsed.port}"
    return host


def _request(
    method: str,
    url: str,
    *,
    token: str = "",
    gateway_url: str = "",
    body: dict | None = None,
    extra_headers: dict | None = None,
    timeout: float = 15.0,
) -> dict:
    headers = {
        "Accept": "application/json",
        "User-Agent": "llm-provider-agent/6.12",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if gateway_url:
        host = _host_header(gateway_url)
        if host:
            headers["Host"] = host
    if extra_headers:
        headers.update(extra_headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _ollama_models(base_url: str) -> list[str]:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=8.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []


def _save_token(token: str) -> None:
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token, encoding="utf-8")
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass


def _load_saved_token() -> str:
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _device_id() -> str:
    custom = _env("DEVICE_ID")
    if custom:
        return custom
    saved = Path("/data/device_id")
    try:
        if saved.is_file():
            return saved.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    new_id = f"dev_{secrets.token_urlsafe(18)}"
    try:
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(new_id, encoding="utf-8")
    except OSError:
        pass
    return new_id


def _handshake_acquire_token(gateway: str, device_id: str) -> str:
    import socket

    label = _env("AGENT_LABEL") or socket.gethostname()
    _request(
        "POST",
        f"{gateway}/v1/provider/handshake/device/register",
        gateway_url=gateway,
        body={"device_id": device_id, "agent_label": label},
    )
    connect_hint = f"{gateway.rstrip('/')}/provider/#/connect?device={device_id}"
    print("Provider handshake started.")
    print(f"  device_id: {device_id}")
    print(f"  While signed in on Provider, open: {connect_hint}")
    print("  Waiting for approval…")

    while True:
        try:
            status = _request(
                "GET",
                f"{gateway}/v1/provider/handshake/device/{device_id}",
                gateway_url=gateway,
            )
        except urllib.error.HTTPError as exc:
            print(f"handshake poll HTTP {exc.code}", file=sys.stderr)
            time.sleep(5)
            continue
        except urllib.error.URLError as exc:
            print(f"handshake poll unreachable: {exc}", file=sys.stderr)
            time.sleep(5)
            continue

        state = status.get("status", "")
        if state == "expired":
            print("handshake expired — restart agent", file=sys.stderr)
            raise SystemExit(1)
        if state == "enrolled" and _load_saved_token():
            return _load_saved_token()
        token = status.get("worker_token", "")
        if token and token.startswith("inw_"):
            _save_token(token)
            print("handshake approved — credentials received automatically")
            return token
        time.sleep(3)


def _resolve_token(gateway: str) -> tuple[str, str]:
    token = _env("INW_TOKEN") or _load_saved_token()
    device_id = ""
    if token:
        return token, device_id
    use_handshake = _env("HANDSHAKE", "1") not in ("0", "false", "no")
    if not use_handshake:
        print("INW_TOKEN or HANDSHAKE=1 required", file=sys.stderr)
        raise SystemExit(1)
    device_id = _device_id()
    token = _handshake_acquire_token(gateway, device_id)
    return token, device_id


def main() -> int:
    gateway = _env("GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")
    ollama = _env("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    enroll_base = ollama
    enroll_fallback = (
        _env("INFERENCE_LAN_URL")
        or _env("INFERENCE_BASE_URL_FALLBACK")
        or _env("INFERENCE_BASE_URL")
    ).rstrip("/")

    token, device_id = _resolve_token(gateway)
    if not token.startswith("inw_"):
        print("invalid worker token", file=sys.stderr)
        return 1

    vram_raw = _env("VRAM_GB")
    vram_gb = float(vram_raw) if vram_raw else None
    heartbeat_s = max(10, int(_env("HEARTBEAT_S", "30") or "30"))

    print(
        f"gateway={gateway} ollama={ollama} "
        f"enroll_docker={enroll_base} enroll_lan_fallback={enroll_fallback or '(none)'}"
    )

    enrolled = False
    while not enrolled:
        models = _ollama_models(ollama)
        enroll_body: dict = {"base_url": enroll_base, "models": models}
        if enroll_fallback:
            enroll_body["base_url_fallback"] = enroll_fallback
        if vram_gb is not None:
            enroll_body["vram_gb"] = vram_gb
        extra = {"X-Provider-Device-Id": device_id} if device_id else None
        try:
            result = _request(
                "POST",
                f"{gateway}/v1/inference/nodes/enroll",
                token=token,
                gateway_url=gateway,
                body=enroll_body,
                extra_headers=extra,
            )
            print(f"enrolled slug={result.get('slug')} base_url={result.get('base_url')}")
            enrolled = True
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            if exc.code == 400:
                print(f"enroll skipped or failed: {body_text}")
                enrolled = True
            else:
                print(f"enroll HTTP {exc.code}: {body_text}", file=sys.stderr)
                time.sleep(min(heartbeat_s, 30))
        except urllib.error.URLError as exc:
            print(f"enroll unreachable: {exc}", file=sys.stderr)
            time.sleep(min(heartbeat_s, 30))

    while True:
        models = _ollama_models(ollama)
        healthy = bool(models)
        body = {"healthy": healthy, "models": models}
        if not healthy:
            body["last_error"] = "ollama /api/tags unreachable or empty"
        try:
            _request(
                "POST",
                f"{gateway}/v1/inference/nodes/heartbeat",
                token=token,
                gateway_url=gateway,
                body=body,
            )
            print(f"heartbeat ok models={len(models)} healthy={healthy}")
        except urllib.error.HTTPError as exc:
            print(
                f"heartbeat HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}",
                file=sys.stderr,
            )
        except urllib.error.URLError as exc:
            print(f"heartbeat unreachable: {exc}", file=sys.stderr)
        time.sleep(heartbeat_s)


if __name__ == "__main__":
    raise SystemExit(main())
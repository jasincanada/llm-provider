"""CLI message bundles — GitHub #213 / #207."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_LOCALES = Path(__file__).resolve().parent / "locales" / "cli"
_DEFAULT = "en"


def _active_locale() -> str:
    raw = os.environ.get("PROVIDER_LANG", os.environ.get("GATEWAY_LANG", _DEFAULT)).strip()
    return raw or _DEFAULT


@lru_cache(maxsize=8)
def _load(locale: str) -> dict[str, str]:
    path = _LOCALES / f"{locale}.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, *, fallback: str | None = None, **vars: str | int | bool) -> str:
    locale = _active_locale()
    bundle = _load(locale)
    en = _load(_DEFAULT)
    text = bundle.get(key) or en.get(key) or fallback or key
    for name, value in vars.items():
        text = text.replace(f"{{{name}}}", str(value))
    return text
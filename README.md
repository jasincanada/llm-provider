# llm-provider

**GPU contributor product** — separate from the [llm-gateway](https://github.com/jasincanada/llm-gateway) control plane and [Jas AI](https://ai.cryptocomputer.ca/jas-ai/) chat homepage.

## What this is

| Product | Role |
|---------|------|
| **llm-gateway** | Control plane — routing, billing, admin, Jas config |
| **llm-provider** (this repo) | Your GPU box — Ollama + enrollment agent |
| **Jas AI** | Public chat homepage — anonymous edge handshake (3 wishes), then sign-in |

## Connect your GPU (no API keys to copy)

1. Register at your gateway's **Provider** portal (`/provider/`).
2. On this machine:
   ```bash
   export GATEWAY_URL=https://llm.cryptocomputer.ca
   docker compose up -d
   ```
3. The agent prints an approve link — open it **while signed in** on Provider.
4. Click **Approve GPU connection**. Credentials flow automatically.
5. Wait for admin approval before paid jobs.

## Legacy operator nodes

Owner-created LAN nodes may still use `INW_TOKEN=inw_…` with `HANDSHAKE=0`.

## License

Same operator policy as llm-gateway — contributor stack is the public product surface.
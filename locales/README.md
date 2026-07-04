# llm-provider locales

Provider SPA locale bundles are authored in **llm-gateway** (`locales/provider/`) and deployed with gateway static builds.

## Parity contract (GitHub #207)

1. `registry.yaml` here mirrors `llm-gateway/locales/registry.yaml`.
2. Run `python v6-dev-os/scripts/i18n_audit.py --app provider` from llm-gateway before release.
3. Agent install strings: localize in `inference-node-agent.py` using `detail_key` pattern from gateway API.

## Sync from gateway

```bash
# On epyc after gateway pull
cp ~/dockersites/llm-gateway/locales/provider/*.json ~/dockersites/llm-provider/locales/provider/
```
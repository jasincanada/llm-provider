# llm-provider — agent entry

Paste into any AI coding agent working on the GPU contributor node.

---

## Hardware & context (5900X baseline)

| Constraint | Rule |
|------------|------|
| Dev GPU | RTX 3070 Ti 8 GB — local Ollama `qwen3:8b` class |
| Agent context | ~150k tokens — one file or small package per task |
| Edit path | `C:\dev\llm-provider` only — never epyc runtime trees |

## Module rules

| Threshold | Lines | Action |
|-----------|-------|--------|
| Target | ≤ 250 | Default |
| Soft warn | > 300 | Split on next touch |
| Hard fail | > 600 | Do not ship |

**Current:** `inference-node-agent.py` (~230 LOC) — OK today; split into `agent/` package before 300 LOC.

## Ship

Commit → push from this repo. Gateway changes use `git ship` from `C:\dev\llm-gateway`.

Multi-repo context: `C:\dev\AGENT.md`
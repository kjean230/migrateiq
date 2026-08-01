# MigrateIQ — Claude Code Context

Read `docs/migrateiq-architecture.md` before any non-trivial change. It is canonical.

## Scope guard
Phase 1 only: Excel in → Excel out, insurance domain.
Reject any request that adds PDF/Word/PPTX/SQL/email parsing or a non-insurance
domain. If asked, say so and stop. §6: "Phase 1 scope is sacred."

## Hard rules
- No layer may import from a layer downstream of it.
- `contracts/` imports nothing from the project. All layers import from it.
- `validation/` is pure Python: no LangChain, no Spark, no LLM calls.
- Parser normalizes only — never interprets. Interpretation is the agent's job.
- Validation rules live in `config/validation_rules.yaml`, never hardcoded.
- Never commit real policy data. Fixtures are synthetic. `.gitignore` denies
  *.xlsx by default with explicit fixture allowlist.
- Never edit `notebooks/` — Databricks Repos owns that directory. Local edits
  can be clobbered by bidirectional sync with the remote.

## Commands
make setup | make test | make lint | make uat-local

## Conventions
Python 3.11+, ruff, mypy strict on src/, pytest. Type hints required.
Every new validation rule needs a fixture in fixtures/excel/ and an
expected ValidationReport in fixtures/expected/.

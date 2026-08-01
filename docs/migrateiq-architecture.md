migrateiq/
├── pyproject.toml                    # py3.11+, deps, ruff/mypy/pytest config
├── README.md                         # clone→run in <10 min (Phase 1 success criterion)
├── Makefile                          # make setup | test | uat-local | run
├── .env.example                      # ANTHROPIC_API_KEY, DATABRICKS_*, MIGRATEIQ_ENV
├── .gitignore
│
├── config/
│   ├── settings.py                   # pydantic-settings loader, env resolution
│   ├── insurance_schema.yaml         # canonical field names + aliases (policy_id, member_id, …)
│   ├── domains.yaml                  # dental|medical|life|vision|claims + coverage_type synonyms
│   ├── validation_rules.yaml         # §3.2 eight rules: id, code, severity, threshold, enforcement_point
│   └── output_profiles.yaml          # findings-sheet layout, column order, styling
│
├── src/migrateiq/
│   ├── __init__.py
│   ├── errors.py                     # ParserError, ContractViolation, ValidationBlocked, UATGateFailure
│   ├── pipeline.py                   # orchestrator: parse → agent → output → uat
│   │
│   ├── contracts/                    # ← STEP 2 lives here. Zero deps on other layers.
│   │   ├── enums.py                  # PolicyDomain, ChangeType, AnomalyCode, SourceFormat, GateResult
│   │   ├── normalized.py             # NormalizedDocument (§2.2 output contract)
│   │   ├── field_map.py              # FieldMap / FieldBinding
│   │   ├── findings.py               # FindingsDict, DomainBreakdown, ChangeCounts
│   │   ├── validation.py             # ValidationReport, Anomaly, RuleResult
│   │   └── run.py                    # MigrationRun (history row written to Delta)
│   │
│   ├── parser/                       # LAYER 1 — reads + normalizes, never interprets
│   │   ├── base.py                   # SourceParser ABC → NormalizedDocument
│   │   ├── excel.py                  # openpyxl/pandas workbook reader, tab + header discovery
│   │   ├── schema_detect.py          # column header → candidate field bindings (lexical, no LLM)
│   │   ├── domain_hint.py            # heuristic domain *hint* only — see deviation 5
│   │   └── metadata.py               # record count, date range, sheet inventory, checksum
│   │
│   ├── agent/                        # LAYER 2 — intelligence
│   │   ├── state.py                  # MigrationState (LangGraph TypedDict) — STEP 3
│   │   ├── graph.py                  # node/edge wiring, retry loop, compiled graph
│   │   ├── nodes.py                  # one node fn per tool + terminal nodes
│   │   ├── llm.py                    # Claude client, structured-output binding, retries
│   │   ├── prompts/
│   │   │   ├── schema_mapping.md
│   │   │   └── extraction.md
│   │   └── tools/
│   │       ├── schema_mapping.py     # NormalizedDocument → FieldMap
│   │       ├── extraction.py         # FieldMap + content → FindingsDict
│   │       ├── validation.py         # thin adapter → validation.engine (deviation 1)
│   │       └── format_selection.py   # source format + override → SourceFormat
│   │
│   ├── validation/                   # RULES ENGINE — pure, no LLM, no agent import
│   │   ├── engine.py                 # loads config, runs registry, emits ValidationReport
│   │   ├── registry.py               # @rule decorator, id→callable map
│   │   ├── rules.py                  # STEP 4: eight pure fns (record, params) → RuleResult|None
│   │   └── anomalies.py              # code taxonomy, counters, threshold escalation
│   │
│   ├── output/                       # LAYER 3
│   │   ├── base.py                   # OutputGenerator ABC (registry keyed by SourceFormat)
│   │   ├── excel.py                  # copy source workbook, append Findings Summary tab
│   │   └── findings_sheet.py         # renders FindingsDict + ValidationReport into cells
│   │
│   ├── uat/                          # LAYER 4
│   │   ├── gates.py                  # 8 gate checks (§2.5 + §3.2 UAT-enforced rules)
│   │   ├── runner.py                 # backend-agnostic gate executor
│   │   ├── backends/
│   │   │   ├── local.py              # pandas impl — runs on every feature branch (deviation 3)
│   │   │   └── spark.py              # PySpark impl, Databricks only
│   │   ├── history.py                # Delta Lake writer for MigrationRun
│   │   └── spark_session.py
│   │
│   └── api/                          # FastAPI
│       ├── main.py                   # app factory, OpenAPI at /docs
│       ├── deps.py
│       ├── schemas.py                # request/response DTOs (≠ contracts/)
│       └── routes/
│           ├── migrations.py         # POST /migrations, GET /migrations/{id}
│           └── health.py
│
├── tests/
│   ├── conftest.py                   # fixture loaders, frozen clock, fake LLM
│   ├── contract/                     # schema round-trip + backward-compat on contracts/
│   ├── unit/
│   │   ├── parser/ agent/ validation/ output/ uat/
│   ├── integration/
│   │   ├── test_pipeline_excel.py    # fixture in → golden xlsx out
│   │   └── test_uat_gate_local.py
│   └── golden/                       # expected output workbooks
│
├── fixtures/
│   ├── excel/
│   │   ├── clean_dental_5k.xlsx
│   │   ├── mixed_domain.xlsx
│   │   ├── null_policy_ids.xlsx      # one fixture per anomaly code
│   │   ├── negative_claim.xlsx
│   │   ├── inverted_dates.xlsx
│   │   ├── orphaned_claims.xlsx
│   │   ├── unknown_coverage.xlsx
│   │   └── count_mismatch.xlsx
│   └── expected/                     # ValidationReport JSON per fixture
│
├── notebooks/                        # Databricks-only, not importable
│   ├── 01_uat_gate.py
│   └── 02_migration_history.py
│
└── scripts/
    ├── run_local.py                  # CLI: file in → file out, no API
    └── seed_fixtures.py
"""Standalone validation package. Pure Python — no LangChain, no Spark.

Public API (run_agent_rules, run_uat_rules, REGISTRY) lands with engine.py.

verify_registry() must be called HERE, after `from . import rules`, and not in
registry.py — REGISTRY is empty at registry.py import time, so the guard would
pass vacuously.

Once rules.py exists:

    from . import rules  # noqa: F401 — imported for registration side effect
    from .registry import REGISTRY, RegistryError, verify_registry

    verify_registry()
"""

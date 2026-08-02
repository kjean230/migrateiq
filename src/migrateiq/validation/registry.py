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
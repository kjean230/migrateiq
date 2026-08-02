# src/migrateiq/validation/spec.py
"""Rule metadata. rules.yaml is the serialized form of this model."""

from pydantic import Field, model_validator

from ..contracts.base import Contract
from ..contracts.enums import (
    RULE_ANOMALY_CODE, AnomalyCode, BlockingMode, EnforcementPoint,
    EnforcementScope, RuleId, Severity,
)

_AGENT_POINTS = frozenset({
    EnforcementPoint.AGENT_VALIDATION, EnforcementPoint.AGENT_SCHEMA_MAPPING,
})


class RuleSpec(Contract):
    rule_id: RuleId
    scope: EnforcementScope
    enforcement_point: EnforcementPoint
    severity: Severity
    blocking: BlockingMode
    tolerance: float | None = Field(default=None, ge=0.0, le=1.0)
    blocking_threshold: float | None = Field(default=None, gt=0.0, le=1.0)
    description: str = Field(min_length=1)

    @property
    def anomaly_code(self) -> AnomalyCode:
        return RULE_ANOMALY_CODE[self.rule_id]

    @model_validator(mode="after")
    def _coherent(self):
        if self.scope is EnforcementScope.UAT:
            if self.enforcement_point is not EnforcementPoint.UAT_GATE:
                raise ValueError(f"{self.rule_id}: UAT scope requires UAT_GATE point")
        elif self.enforcement_point not in _AGENT_POINTS:
            raise ValueError(f"{self.rule_id}: AGENT scope requires an agent point")

        if self.blocking is BlockingMode.THRESHOLD:
            if self.blocking_threshold is None:
                raise ValueError(f"{self.rule_id}: THRESHOLD needs blocking_threshold")
        elif self.blocking_threshold is not None:
            raise ValueError(f"{self.rule_id}: blocking_threshold only for THRESHOLD")

        if self.blocking is not BlockingMode.NEVER and self.severity is not Severity.ERROR:
            raise ValueError(f"{self.rule_id}: blocking rules must be ERROR")
        return self
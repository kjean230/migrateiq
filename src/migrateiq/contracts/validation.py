from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field
from .base import Contract, RecordRef, SCHEMA_VERSION
from .enums import (AnomalyCode, EnforcementPoint, ReportStatus, RuleId,
                    RuleStatus, Severity)

class RuleResult(Contract):
    rule_id: RuleId
    enforcement_point: EnforcementPoint
    status: RuleStatus
    severity: Severity
    blocking: bool                                # true => output generator must not run
    affected_record_count: int = Field(default=0, ge=0)
    affected_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    threshold: float | None = None                # e.g. 0.01 for DQ001, 0.001 for DQ008
    anomaly_code: AnomalyCode | None = None
    message: str
    samples: list[RecordRef] = Field(default_factory=list, max_length=20)

class ValidationReport(Contract):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    document_id: UUID
    source_sha256: str
    validated_at: datetime
    validator_version: str                        # validation/ package version
    enforcement_scope: EnforcementPoint           # AGENT_VALIDATION or UAT_GATE
    results: list[RuleResult] = Field(min_length=1)

    @property
    def blocking_failures(self) -> list[RuleResult]:
        return [r for r in self.results if r.status is RuleStatus.FAIL and r.blocking]

    @property
    def status(self) -> ReportStatus:
        if self.blocking_failures:
            return ReportStatus.FAIL
        if any(r.status is RuleStatus.FAIL for r in self.results):
            return ReportStatus.PASS_WITH_WARNINGS
        return ReportStatus.PASS

    @property
    def cleared_for_output(self) -> bool:
        return not self.blocking_failures
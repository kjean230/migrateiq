from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import Field
from .base import Contract, Metric, RecordRef, SCHEMA_VERSION
from .enums import AnomalyCode, CanonicalField, Domain

class ChangeCounts(Contract):
    inserts: Metric
    updates: Metric
    soft_deletes: Metric

class DomainSlice(Contract):
    domain: Domain
    record_count: int = Field(ge=0)
    amount_billed_total: Decimal | None = None
    amount_paid_total: Decimal | None = None

class Anomaly(Contract):
    code: AnomalyCode
    record: RecordRef | None = None
    field: CanonicalField | None = None
    observed: str | None = None
    message: str

class Findings(Contract):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    document_id: UUID
    source_sha256: str
    domain: Domain
    source_record_count: int = Field(ge=0)        # echoed from NormalizedDocument
    extracted_record_count: int = Field(ge=0)
    change_counts: ChangeCounts
    coverage_breakdown: list[DomainSlice] = Field(default_factory=list)
    period_start: date | None = None
    period_end: date | None = None
    anomalies: list[Anomaly] = Field(default_factory=list)
    missing_fields: list[CanonicalField] = Field(default_factory=list)
    domain_hint_disagreement: bool | None = None  # carried from FieldMap
    extraction_attempts: int = Field(default=1, ge=1)   # LangGraph retry count
    generated_at: datetime
    agent_model: str

    @property
    def anomaly_counts(self) -> dict[AnomalyCode, int]:
        out = {c: 0 for c in AnomalyCode}
        for a in self.anomalies:
            out[a.code] += 1
        return out
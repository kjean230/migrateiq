from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from .base import Confidence, Contract, SCHEMA_VERSION
from .enums import CanonicalField, Domain, REQUIRED_FIELDS

class FieldMapping(Contract):
    canonical: CanonicalField
    sheet: str
    source_column: str
    confidence: Confidence
    rationale: str | None = None

class FieldMap(Contract):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    document_id: UUID
    source_sha256: str                            # binds map to exact parsed file
    domain: Domain                                # authoritative, agent-assigned
    domain_confidence: Confidence
    domain_hint: Domain | None = None             # copied forward for the signal
    mappings: list[FieldMapping]
    unmapped_columns: list[str] = Field(default_factory=list)
    unknown_coverage_values: list[str] = Field(default_factory=list)   # feeds DQ005
    mapped_at: datetime
    agent_model: str

    @property
    def hint_disagrees(self) -> bool | None:
        """Findings signal, not a §3.2 rule. None when parser gave no hint."""
        return None if self.domain_hint is None else self.domain_hint != self.domain

    @property
    def missing_required(self) -> frozenset[CanonicalField]:
        return REQUIRED_FIELDS - {m.canonical for m in self.mappings}

    @model_validator(mode="after")
    def _one_column_per_canonical(self):
        seen = [m.canonical for m in self.mappings]
        if len(seen) != len(set(seen)):
            raise ValueError("duplicate canonical field in mappings")
        return self
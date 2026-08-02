from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import Field, model_validator
from .base import Confidence, Contract, SCHEMA_VERSION
from .enums import ChangeType, Domain, SourceFormat

class SourceMetadata(Contract):
    path: str
    filename: str
    format: SourceFormat
    sha256: str = Field(min_length=64, max_length=64)
    size_bytes: int = Field(ge=0)
    ingested_at: datetime
    parser_version: str

class SourceColumn(Contract):
    name: str                               # header text, verbatim
    index: int = Field(ge=0)
    inferred_dtype: Literal["string", "integer", "float", "date", "datetime",
                            "boolean", "empty", "mixed"]
    non_null_count: int = Field(ge=0)
    distinct_count: int | None = Field(default=None, ge=0)
    sample_values: list[Any] = Field(default_factory=list, max_length=5)

class ContentBlock(Contract):
    """One worksheet. Structure + metadata always; row payload by value or by reference."""
    sheet: str
    sheet_index: int = Field(ge=0)
    header_row_number: int | None = Field(default=None, ge=1)
    columns: list[SourceColumn]
    row_count: int = Field(ge=0)
    records: list[dict[str, Any]] | None = None   # keyed by SourceColumn.name
    records_uri: str | None = None                # parquet spill for large sheets

    @model_validator(mode="after")
    def _exactly_one_payload(self):
        if (self.records is None) == (self.records_uri is None):
            raise ValueError("set exactly one of records / records_uri")
        return self

class NormalizedDocument(Contract):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    document_id: UUID
    source: SourceMetadata
    blocks: list[ContentBlock] = Field(min_length=1)
    total_record_count: int = Field(ge=0)         # baseline for DQ008
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    domain_hint: Domain | None = None             # hint only — agent is authoritative
    domain_hint_confidence: Confidence | None = None
    change_type_hint: ChangeType | None = None
    parse_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _hint_pairing(self):
        if (self.domain_hint is None) != (self.domain_hint_confidence is None):
            raise ValueError("domain_hint and domain_hint_confidence are set together")
        return self
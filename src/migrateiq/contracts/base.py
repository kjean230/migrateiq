from typing import Annotated, Final, Literal
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Final = "1.0"
MISSING: Final = "[MISSING]"
MissingMetric = Literal["[MISSING]"]        # §2.3: never coerce absence to 0
Metric = int | MissingMetric
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]

class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False,
                              str_strip_whitespace=True)

class RecordRef(Contract):
    """Row-level traceability. Every anomaly resolves to exactly one of these."""
    sheet: str
    source_row_number: int = Field(ge=1)    # 1-based, as seen in Excel
    policy_id: str | None = None
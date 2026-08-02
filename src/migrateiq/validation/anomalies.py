# src/migrateiq/validation/anomalies.py
"""Sole construction path for Anomaly inside validation/.

Rules never name an AnomalyCode. They name their own RuleId, which the
decorator already binds, and the code derives from RULE_ANOMALY_CODE — so
config, enum and rule body cannot drift apart.

Replaces the anomaly() methods sketched on the context types: RecordContext
carries no RuleSpec (hot path, one instance per row), so it cannot derive a
code without the caller supplying it, which defeats the point.
"""

from ..contracts.base import RecordRef
from ..contracts.enums import RULE_ANOMALY_CODE, CanonicalField, RuleId
from ..contracts.findings import Anomaly


def record_anomaly(
    rule_id: RuleId,
    ref: RecordRef,
    message: str,
    field: CanonicalField | None = None,
    observed: str | None = None,
) -> Anomaly:
    """Row-level anomaly. ref is required — DQ001-006 always have a row."""
    return Anomaly(
        code=RULE_ANOMALY_CODE[rule_id],
        record=ref,
        field=field,
        observed=observed,
        message=message,
    )


def document_anomaly(
    rule_id: RuleId,
    message: str,
    field: CanonicalField | None = None,
    observed: str | None = None,
) -> Anomaly:
    """Aggregate anomaly, record=None. Only DQ007/DQ008 may call this —
    Anomaly._record_matches_code rejects record=None for any other code."""
    return Anomaly(
        code=RULE_ANOMALY_CODE[rule_id],
        record=None,
        field=field,
        observed=observed,
        message=message,
    )
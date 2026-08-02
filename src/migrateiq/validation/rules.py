# src/migrateiq/validation/rules.py
"""The eight §3.2 rules. Flat by design — a rules/ subpackage would put the
registration side effect behind eight imports instead of one.

Rules are pure and deterministic: no I/O, no clock, no logging, no config
access. A rule reads its context and returns anomalies. Blocking, thresholds
and status are the engine's business, driven by RuleSpec.

Record rules return None when the row is not evaluable — an unmapped column
is not a clean pass. Returning [] means "evaluated, no violation".
"""

from typing import cast

from ..contracts.base import MISSING, RecordRef
from ..contracts.enums import KNOWN_COVERAGE_DOMAINS, RuleId
from ..contracts.enums import CanonicalField as CF
from ..contracts.findings import Anomaly
from .anomalies import document_anomaly, record_anomaly
from .context import ReconContext, RecordContext
from .registry import aggregate_rule, record_rule

# =============================================================================
# Record rules — EnforcementScope.AGENT, one call per row
# =============================================================================


@record_rule(RuleId.POLICY_ID_NOT_NULL)
def policy_id_not_null(ctx: RecordContext) -> list[Anomaly] | None:
    """DQ001. policy_id non-null on every record. THRESHOLD @ 1%.

    An unmapped policy_id column is a schema problem, not a data problem, and
    is not this rule's to report — it surfaces via Findings.missing_fields.
    """
    if not ctx.is_mapped(CF.POLICY_ID):
        return None
    if not ctx.is_null(CF.POLICY_ID):
        return []
    return [
        record_anomaly(
            RuleId.POLICY_ID_NOT_NULL,
            ctx.ref,
            message="policy_id is null or blank",
            field=CF.POLICY_ID,
            observed=repr(ctx.get(CF.POLICY_ID)),
        )
    ]


# =============================================================================
# Aggregate rules — EnforcementScope.UAT, one call per document
# =============================================================================


@aggregate_rule(RuleId.CHANGE_COUNTS_RECONCILE)
def change_counts_reconcile(ctx: ReconContext) -> list[Anomaly]:
    """DQ007. inserts + updates + soft_deletes == records processed. ALWAYS.

    Fails closed on [MISSING]: an unknown change count cannot be shown to
    reconcile, and coercing it to 0 would let a broken CDC read pass the gate.
    """
    missing = ctx.missing_change_counts
    if missing:
        return [
            document_anomaly(
                RuleId.CHANGE_COUNTS_RECONCILE,
                message=(
                    "change counts cannot be reconciled; "
                    f"{', '.join(missing)} absent from source"
                ),
                observed=MISSING,
            )
        ]

    cc = ctx.change_counts
    # Narrowed by the guard above — every field is int past this point.
    total = (
        cast(int, cc.inserts) + cast(int, cc.updates) + cast(int, cc.soft_deletes)
    )
    processed = ctx.findings.extracted_record_count
    if total == processed:
        return []

    return [
        document_anomaly(
            RuleId.CHANGE_COUNTS_RECONCILE,
            message=(
                f"change counts sum to {total} but {processed} records were "
                f"processed (delta {total - processed:+d})"
            ),
            observed=str(total),
        )
    ]
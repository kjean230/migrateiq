# enums.py
"""Canonical enums and field sets for MigrateIQ contracts.

Zero dependencies outside the stdlib. Imported by every layer, including the
Spark-side UAT gate — nothing here may ever import LangChain, pandas, or pyspark.
"""

from enum import StrEnum

class SourceFormat(StrEnum):
    XLSX = "xlsx"  # Phase 1: only member. Do not pre-add PDF/DOCX.


class Domain(StrEnum):
    """Document-level domain classification.

    MIXED and UNKNOWN are document-level answers only. They are NOT valid
    coverage_type cell values — DQ005 validates against KNOWN_COVERAGE_DOMAINS.
    """

    DENTAL = "dental"; MEDICAL = "medical"; LIFE = "life"
    VISION = "vision"; CLAIMS = "claims"; MIXED = "mixed"; UNKNOWN = "unknown"


#: DQ005 target set. A coverage_type cell reading "mixed" or "unknown" is a
#: violation, not a pass — hence this is narrower than Domain.
KNOWN_COVERAGE_DOMAINS = frozenset({
    Domain.DENTAL, Domain.MEDICAL, Domain.LIFE, Domain.VISION, Domain.CLAIMS,
})


class ChangeType(StrEnum):
    SNAPSHOT = "snapshot"; DELTA = "delta"; CDC = "cdc"; UNKNOWN = "unknown"


class ChangeOp(StrEnum):
    INSERT = "insert"; UPDATE = "update"; SOFT_DELETE = "soft_delete"


class PolicyStatus(StrEnum):
    """Policy lifecycle status. Distinct from CLAIM_STATUS.

    Required by DQ002: termination_date is only mandatory once a policy has
    actually terminated. UNKNOWN means the source did not supply status, in
    which case DQ002 cannot be evaluated and returns NOT_APPLICABLE.
    """

    ACTIVE = "active"; TERMINATED = "terminated"; UNKNOWN = "unknown"

class CanonicalField(StrEnum):
    POLICY_ID = "policy_id"; MEMBER_ID = "member_id"; COVERAGE_TYPE = "coverage_type"
    EFFECTIVE_DATE = "effective_date"; TERMINATION_DATE = "termination_date"
    POLICY_STATUS = "policy_status"; CLAIM_STATUS = "claim_status"
    AMOUNT_BILLED = "amount_billed"; AMOUNT_PAID = "amount_paid"
    CHANGE_OP = "change_op"


#: §2.5 UAT gate: no nulls permitted in these fields.
REQUIRED_FIELDS = frozenset({
    CanonicalField.POLICY_ID,
    CanonicalField.EFFECTIVE_DATE,
    CanonicalField.COVERAGE_TYPE,
})

#: §3.2 names a single `claim_amount`; MigrateIQ splits it billed/paid.
#: DQ004 iterates this set and attributes the anomaly to the specific field.
CLAIM_AMOUNT_FIELDS = frozenset({
    CanonicalField.AMOUNT_BILLED,
    CanonicalField.AMOUNT_PAID,
})

class AnomalyCode(StrEnum):
    """§3.3 taxonomy, extended.

    MISSING_COVERAGE_PERIOD and the two reconciliation codes are deviations:
    §3.3 predates the agent/UAT scope split and defines only five codes for
    eight rules, which left DQ007/DQ008 unable to emit an Anomaly at all.
    """

    MISSING_FIELD = "MISSING_FIELD"
    MISSING_COVERAGE_PERIOD = "MISSING_COVERAGE_PERIOD"   # DQ002 (was MISSING_FIELD)
    INVALID_DATE = "INVALID_DATE"
    NEGATIVE_CLAIM = "NEGATIVE_CLAIM"
    UNKNOWN_DOMAIN = "UNKNOWN_DOMAIN"
    ORPHANED_CLAIM = "ORPHANED_CLAIM"
    RECONCILIATION_MISMATCH = "RECONCILIATION_MISMATCH"   # DQ007
    VOLUME_DRIFT = "VOLUME_DRIFT"                         # DQ008


class EnforcementPoint(StrEnum):
    """Which component calls the rule."""

    PARSER = "parser"; AGENT_SCHEMA_MAPPING = "agent_schema_mapping"
    AGENT_VALIDATION = "agent_validation"; UAT_GATE = "uat_gate"


class EnforcementScope(StrEnum):
    """Which run a rule belongs to. The registry filter discriminator.

    AGENT -> DQ001-006 (row-level, needs records)
    UAT   -> DQ007-008 (aggregate, needs only Findings + source counts)
    """

    AGENT = "agent"; UAT = "uat"


class RuleId(StrEnum):  # §3.2, one per row, order preserved
    POLICY_ID_NOT_NULL = "DQ001_POLICY_ID_NOT_NULL"
    COVERAGE_PERIOD_PRESENT = "DQ002_COVERAGE_PERIOD_PRESENT"
    EFFECTIVE_BEFORE_TERMINATION = "DQ003_EFFECTIVE_BEFORE_TERMINATION"
    CLAIM_AMOUNT_NON_NEGATIVE = "DQ004_CLAIM_AMOUNT_NON_NEGATIVE"
    COVERAGE_TYPE_KNOWN_DOMAIN = "DQ005_COVERAGE_TYPE_KNOWN_DOMAIN"
    MEMBER_ID_ON_CLAIMS = "DQ006_MEMBER_ID_ON_CLAIMS"
    CHANGE_COUNTS_RECONCILE = "DQ007_CHANGE_COUNTS_RECONCILE"
    RECORD_COUNT_TOLERANCE = "DQ008_RECORD_COUNT_TOLERANCE"


#: Total map: every rule emits exactly one anomaly code, and no two rules that
#: carry different consequences share one. Enforced by tests/contracts/test_enums.py.
RULE_ANOMALY_CODE: dict[RuleId, AnomalyCode] = {
    RuleId.POLICY_ID_NOT_NULL: AnomalyCode.MISSING_FIELD,
    RuleId.COVERAGE_PERIOD_PRESENT: AnomalyCode.MISSING_COVERAGE_PERIOD,
    RuleId.EFFECTIVE_BEFORE_TERMINATION: AnomalyCode.INVALID_DATE,
    RuleId.CLAIM_AMOUNT_NON_NEGATIVE: AnomalyCode.NEGATIVE_CLAIM,
    RuleId.COVERAGE_TYPE_KNOWN_DOMAIN: AnomalyCode.UNKNOWN_DOMAIN,
    RuleId.MEMBER_ID_ON_CLAIMS: AnomalyCode.ORPHANED_CLAIM,
    RuleId.CHANGE_COUNTS_RECONCILE: AnomalyCode.RECONCILIATION_MISMATCH,
    RuleId.RECORD_COUNT_TOLERANCE: AnomalyCode.VOLUME_DRIFT,
}


class RuleStatus(StrEnum):
    """Per-rule outcome.

    SKIPPED        -> filtered out by EnforcementScope; did not run.
    NOT_APPLICABLE -> in scope, ran, no evaluable records (e.g. DQ006 on a
                      workbook with no claim rows; DQ002 where policy_status
                      is UNKNOWN for every row).
    """

    PASS = "pass"; FAIL = "fail"; SKIPPED = "skipped"; NOT_APPLICABLE = "not_applicable"


class Severity(StrEnum):
    INFO = "info"; WARNING = "warning"; ERROR = "error"


class BlockingMode(StrEnum):
    """How a failing rule affects delivery. Orthogonal to Severity.

    NEVER     -> surfaces in findings, never blocks (DQ002, DQ003).
    THRESHOLD -> blocks once the failure rate exceeds RuleSpec.threshold (DQ001 @ 1%).
    ALWAYS    -> any failure blocks (DQ007, DQ008).
    """

    NEVER = "never"; THRESHOLD = "threshold"; ALWAYS = "always"


class ReportStatus(StrEnum):
    """Overall ValidationReport outcome. Also serves as the UAT gate result —
    GateResult from the step 1 tree was dropped as a duplicate of this.
    """

    PASS = "pass"; PASS_WITH_WARNINGS = "pass_with_warnings"; FAIL = "fail"
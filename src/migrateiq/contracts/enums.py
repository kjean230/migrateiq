from enum import StrEnum

class SourceFormat(StrEnum):
    XLSX = "xlsx"                      # Phase 1: only member. Do not pre-add PDF/DOCX.

class Domain(StrEnum):
    DENTAL = "dental"; MEDICAL = "medical"; LIFE = "life"
    VISION = "vision"; CLAIMS = "claims"; MIXED = "mixed"; UNKNOWN = "unknown"

class ChangeType(StrEnum):
    SNAPSHOT = "snapshot"; DELTA = "delta"; CDC = "cdc"; UNKNOWN = "unknown"

class ChangeOp(StrEnum):
    INSERT = "insert"; UPDATE = "update"; SOFT_DELETE = "soft_delete"

class CanonicalField(StrEnum):
    POLICY_ID = "policy_id"; MEMBER_ID = "member_id"; COVERAGE_TYPE = "coverage_type"
    EFFECTIVE_DATE = "effective_date"; TERMINATION_DATE = "termination_date"
    CLAIM_STATUS = "claim_status"; AMOUNT_BILLED = "amount_billed"
    AMOUNT_PAID = "amount_paid"; CHANGE_OP = "change_op"

REQUIRED_FIELDS = frozenset({CanonicalField.POLICY_ID, CanonicalField.EFFECTIVE_DATE,
                             CanonicalField.COVERAGE_TYPE})

class AnomalyCode(StrEnum):
    MISSING_FIELD = "MISSING_FIELD"; INVALID_DATE = "INVALID_DATE"
    NEGATIVE_CLAIM = "NEGATIVE_CLAIM"; UNKNOWN_DOMAIN = "UNKNOWN_DOMAIN"
    ORPHANED_CLAIM = "ORPHANED_CLAIM"

class EnforcementPoint(StrEnum):
    PARSER = "parser"; AGENT_SCHEMA_MAPPING = "agent_schema_mapping"
    AGENT_VALIDATION = "agent_validation"; UAT_GATE = "uat_gate"

class RuleId(StrEnum):                 # §3.2, one per row, order preserved
    POLICY_ID_NOT_NULL = "DQ001_POLICY_ID_NOT_NULL"
    COVERAGE_PERIOD_PRESENT = "DQ002_COVERAGE_PERIOD_PRESENT"
    EFFECTIVE_BEFORE_TERMINATION = "DQ003_EFFECTIVE_BEFORE_TERMINATION"
    CLAIM_AMOUNT_NON_NEGATIVE = "DQ004_CLAIM_AMOUNT_NON_NEGATIVE"
    COVERAGE_TYPE_KNOWN_DOMAIN = "DQ005_COVERAGE_TYPE_KNOWN_DOMAIN"
    MEMBER_ID_ON_CLAIMS = "DQ006_MEMBER_ID_ON_CLAIMS"
    CHANGE_COUNTS_RECONCILE = "DQ007_CHANGE_COUNTS_RECONCILE"
    RECORD_COUNT_TOLERANCE = "DQ008_RECORD_COUNT_TOLERANCE"

class RuleStatus(StrEnum):
    PASS = "pass"; FAIL = "fail"; SKIPPED = "skipped"; NOT_APPLICABLE = "not_applicable"

class Severity(StrEnum):
    INFO = "info"; WARNING = "warning"; ERROR = "error"

class ReportStatus(StrEnum):
    PASS = "pass"; PASS_WITH_WARNINGS = "pass_with_warnings"; FAIL = "fail"
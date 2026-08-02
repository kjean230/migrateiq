# tests/validation/conftest.py
"""Expected-failure fixtures — one per §3.2 rule, plus clean baselines.

Written before the rule bodies deliberately: each fixture encodes what the
rule must catch, independent of how it is implemented. A rule that passes its
fixture but was written against it is not evidence; a fixture that exists
first is.

Factories rather than bare fixtures because most rules need both a violating
and a clean row, and pytest fixtures cannot be parametrized at the call site.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from migrateiq.contracts.base import MISSING, RecordRef
from migrateiq.contracts.enums import CanonicalField as CF
from migrateiq.contracts.enums import Domain, PolicyStatus
from migrateiq.contracts.findings import ChangeCounts, Findings
from migrateiq.validation.context import ReconContext, RecordContext
from migrateiq.validation.spec import load_specs

_SHA = "0" * 64

#: A fully-mapped, fully-valid row. Every violating fixture is this, mutated.
_CLEAN_ROW: dict = {
    CF.POLICY_ID: "P-1001",
    CF.MEMBER_ID: "M-2001",
    CF.COVERAGE_TYPE: Domain.DENTAL,
    CF.EFFECTIVE_DATE: date(2026, 1, 1),
    CF.TERMINATION_DATE: date(2026, 12, 31),
    CF.POLICY_STATUS: PolicyStatus.ACTIVE,
    CF.AMOUNT_BILLED: Decimal("450.00"),
    CF.AMOUNT_PAID: Decimal("380.00"),
}


@pytest.fixture(scope="session")
def specs():
    return load_specs()


@pytest.fixture
def make_row():
    """Build a RecordContext.

    values overrides _CLEAN_ROW. unmapped removes fields from the mapped set
    WITHOUT nulling them — that is the distinction rules must not collapse:
    an unmapped column is not evaluable, a mapped-but-empty cell is a
    violation. Passing a field in both values and unmapped is a test bug.
    """

    def build(
        row: int = 2,
        domain: Domain = Domain.DENTAL,
        unmapped: frozenset = frozenset(),
        sheet: str = "policies",
        **values,
    ) -> RecordContext:
        keyed = {CF(k): v for k, v in values.items()}
        overlap = keyed.keys() & unmapped
        if overlap:
            raise ValueError(f"field given a value and marked unmapped: {overlap}")

        merged = {**_CLEAN_ROW, **keyed}
        mapped = frozenset(merged) - frozenset(unmapped)
        return RecordContext(
            ref=RecordRef(
                sheet=sheet,
                source_row_number=row,
                policy_id=merged.get(CF.POLICY_ID),
            ),
            values=merged,
            mapped=mapped,
            domain=domain,
        )

    return build


@pytest.fixture
def make_recon(specs):
    """Build a ReconContext. Defaults reconcile exactly and sit at zero drift."""

    def build(
        rule_id,
        source_count: int = 1000,
        extracted_count: int | None = None,
        inserts=600,
        updates=300,
        soft_deletes=100,
        domain: Domain = Domain.DENTAL,
    ) -> ReconContext:
        findings = Findings(
            document_id=uuid4(),
            source_sha256=_SHA,
            domain=domain,
            source_record_count=source_count,
            extracted_record_count=(
                source_count if extracted_count is None else extracted_count
            ),
            change_counts=ChangeCounts(
                inserts=inserts, updates=updates, soft_deletes=soft_deletes
            ),
            generated_at=datetime.now(timezone.utc),
            agent_model="claude-test",
        )
        return ReconContext(
            findings=findings,
            source_record_count=source_count,
            spec=specs[rule_id],
        )

    return build


# --- Record-rule violations ------------------------------------------------


@pytest.fixture
def row_clean(make_row):
    return make_row()


@pytest.fixture
def row_null_policy_id(make_row):
    """DQ001. Mapped and empty — a violation, not an unmapped column."""
    return make_row(policy_id=None)


@pytest.fixture
def row_blank_policy_id(make_row):
    """DQ001. Whitespace-only. is_null must treat this as empty, not present."""
    return make_row(policy_id="   ")


@pytest.fixture
def row_policy_id_unmapped(make_row):
    """DQ001 must NOT flag this — the column was never mapped, so the rule
    has nothing to evaluate. The row that catches is_mapped/is_null collapse."""
    return make_row(unmapped=frozenset({CF.POLICY_ID}))


@pytest.fixture
def row_terminated_no_end_date(make_row):
    """DQ002. Terminated policy with no termination_date."""
    return make_row(policy_status=PolicyStatus.TERMINATED, termination_date=None)


@pytest.fixture
def row_active_no_end_date(make_row):
    """DQ002 must skip: an active policy is not expected to have an end date."""
    return make_row(policy_status=PolicyStatus.ACTIVE, termination_date=None)


@pytest.fixture
def row_status_unknown(make_row):
    """DQ002 not evaluable — status absent from source. NOT_APPLICABLE, not PASS."""
    return make_row(policy_status=PolicyStatus.UNKNOWN, termination_date=None)


@pytest.fixture
def row_dates_inverted(make_row):
    """DQ003. effective_date after termination_date."""
    return make_row(
        effective_date=date(2026, 12, 31), termination_date=date(2026, 1, 1)
    )


@pytest.fixture
def row_negative_paid(make_row):
    """DQ004. Anomaly must attribute to AMOUNT_PAID specifically, not both."""
    return make_row(amount_paid=Decimal("-380.00"))


@pytest.fixture
def row_negative_both(make_row):
    """DQ004 iterates CLAIM_AMOUNT_FIELDS — two anomalies from one row."""
    return make_row(
        amount_billed=Decimal("-450.00"), amount_paid=Decimal("-380.00")
    )


@pytest.fixture
def row_coverage_mixed(make_row):
    """DQ005. 'mixed' is a valid document Domain but never a valid cell value."""
    return make_row(coverage_type=Domain.MIXED)


@pytest.fixture
def row_coverage_garbage(make_row):
    """DQ005. Free-text the mapper could not resolve. observed must survive."""
    return make_row(coverage_type="dentl")


@pytest.fixture
def row_claim_no_member_id(make_row):
    """DQ006. Claim row, member_id mapped but empty."""
    return make_row(coverage_type=Domain.CLAIMS, member_id=None)


@pytest.fixture
def row_non_claim_no_member_id(make_row):
    """DQ006 must not flag: member_id is only required on claim records."""
    return make_row(coverage_type=Domain.DENTAL, member_id=None)


# --- Aggregate-rule violations ---------------------------------------------


@pytest.fixture
def recon_clean(make_recon):
    from migrateiq.contracts.enums import RuleId

    return make_recon(RuleId.CHANGE_COUNTS_RECONCILE)


@pytest.fixture
def recon_counts_mismatch(make_recon):
    """DQ007. 600+300+100 = 1000, but 1200 records processed."""
    from migrateiq.contracts.enums import RuleId

    return make_recon(RuleId.CHANGE_COUNTS_RECONCILE, extracted_count=1200)


@pytest.fixture
def recon_counts_missing(make_recon):
    """DQ007. A [MISSING] change count fails closed — never a TypeError,
    never coerced to 0."""
    from migrateiq.contracts.enums import RuleId

    return make_recon(RuleId.CHANGE_COUNTS_RECONCILE, updates=MISSING)


@pytest.fixture
def recon_within_tolerance(make_recon):
    """DQ008. 1 of 1000 = 0.1%, exactly at the boundary — must PASS."""
    from migrateiq.contracts.enums import RuleId

    return make_recon(RuleId.RECORD_COUNT_TOLERANCE, extracted_count=999)


@pytest.fixture
def recon_outside_tolerance(make_recon):
    """DQ008. 5 of 1000 = 0.5%, past the 0.1% tolerance."""
    from migrateiq.contracts.enums import RuleId

    return make_recon(RuleId.RECORD_COUNT_TOLERANCE, extracted_count=995)
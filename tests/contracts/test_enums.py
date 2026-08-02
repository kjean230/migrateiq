"""Regression guards for the enums contract.

These catch the class of bug that is invisible at import time: duplicate enum
values silently collapsing into aliases, and RuleId -> AnomalyCode drifting out
of totality when a ninth rule is added.

Place at tests/contracts/test_enums.py.
"""

from collections import Counter
from enum import StrEnum

import pytest

from migrateiq.contracts import enums as E

ENUM_CLASSES = [
    c
    for c in vars(E).values()
    if isinstance(c, type) and issubclass(c, StrEnum) and c is not StrEnum
]


@pytest.mark.parametrize("cls", ENUM_CLASSES, ids=lambda c: c.__name__)
def test_no_silent_aliases(cls):
    """Two members sharing a value become aliases, and one vanishes from
    iteration without any error. Every 'for x in Enum' loop then skips it."""
    aliases = set(cls.__members__) - {m.name for m in cls}
    assert not aliases, f"{cls.__name__} has aliased members: {aliases}"


def test_rule_anomaly_code_is_total():
    """Every rule must be able to emit an anomaly. DQ007/DQ008 could not until
    RECONCILIATION_MISMATCH and VOLUME_DRIFT were added."""
    assert set(E.RULE_ANOMALY_CODE) == set(E.RuleId)


def test_rule_anomaly_code_is_injective():
    """Anomaly counters are keyed by code. Two rules sharing a code means the
    findings tab cannot distinguish them — DQ001 (blocks at 1%) and DQ002
    (never blocks) previously both reported MISSING_FIELD."""
    dupes = {
        code.value: [r.value for r in E.RULE_ANOMALY_CODE if E.RULE_ANOMALY_CODE[r] is code]
        for code, n in Counter(E.RULE_ANOMALY_CODE.values()).items()
        if n > 1
    }
    assert not dupes, f"anomaly code collisions: {dupes}"


def test_rule_ids_are_contiguous_and_ordered():
    prefixes = [r.value.split("_")[0] for r in E.RuleId]
    assert prefixes == [f"DQ{n:03d}" for n in range(1, 9)]


def test_dq005_target_set_excludes_meta_domains():
    """A coverage_type cell reading 'mixed' or 'unknown' must fail DQ005."""
    assert E.KNOWN_COVERAGE_DOMAINS < set(E.Domain)
    assert E.Domain.MIXED not in E.KNOWN_COVERAGE_DOMAINS
    assert E.Domain.UNKNOWN not in E.KNOWN_COVERAGE_DOMAINS


def test_required_fields_match_spec_2_5():
    assert {f.value for f in E.REQUIRED_FIELDS} == {
        "policy_id",
        "effective_date",
        "coverage_type",
    }


def test_field_sets_reference_real_fields():
    assert E.REQUIRED_FIELDS <= set(E.CanonicalField)
    assert E.CLAIM_AMOUNT_FIELDS <= set(E.CanonicalField)


def test_policy_status_distinct_from_claim_status():
    """DQ002 conditions on policy lifecycle, not claim disposition."""
    assert E.CanonicalField.POLICY_STATUS is not E.CanonicalField.CLAIM_STATUS


def test_str_enum_serializes_bare():
    """Contracts are JSON round-tripped across the FastAPI boundary and into
    Delta. StrEnum members must serialize as their bare values."""
    import json

    payload = {"domain": E.Domain.DENTAL, "blocking": E.BlockingMode.THRESHOLD}
    assert json.loads(json.dumps(payload)) == {"domain": "dental", "blocking": "threshold"}


@pytest.mark.parametrize("cls", [E.Domain, E.RuleId, E.AnomalyCode, E.CanonicalField])
def test_value_lookup_is_total(cls):
    """config/rules.yaml and the parser both reconstruct members from strings."""
    for member in cls:
        assert cls(member.value) is member
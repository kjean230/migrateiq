# tests/validation/test_rules.py
"""DQ001 and DQ007 — one rule of each kind, proving both context types and
the not-evaluable signal before the remaining six are written."""

import pytest

from migrateiq.contracts.base import MISSING
from migrateiq.contracts.enums import AnomalyCode, CanonicalField as CF
from migrateiq.validation.rules import change_counts_reconcile, policy_id_not_null


class TestDQ001:
    def test_clean_row_passes(self, row_clean):
        assert policy_id_not_null(row_clean) == []

    def test_null_flagged(self, row_null_policy_id):
        (anomaly,) = policy_id_not_null(row_null_policy_id)
        assert anomaly.code is AnomalyCode.MISSING_FIELD
        assert anomaly.field is CF.POLICY_ID
        assert anomaly.record.source_row_number == 2

    def test_whitespace_only_flagged(self, row_blank_policy_id):
        assert len(policy_id_not_null(row_blank_policy_id)) == 1

    def test_unmapped_is_not_evaluable(self, row_policy_id_unmapped):
        """None, not [] — an unmapped column must not read as a clean pass."""
        assert policy_id_not_null(row_policy_id_unmapped) is None

    def test_anomaly_is_traceable(self, row_null_policy_id):
        (anomaly,) = policy_id_not_null(row_null_policy_id)
        assert anomaly.record is not None
        assert anomaly.record.sheet == "policies"


class TestDQ007:
    def test_reconciling_counts_pass(self, recon_clean):
        assert change_counts_reconcile(recon_clean) == []

    def test_mismatch_flagged(self, recon_counts_mismatch):
        (anomaly,) = change_counts_reconcile(recon_counts_mismatch)
        assert anomaly.code is AnomalyCode.RECONCILIATION_MISMATCH
        assert "1200" in anomaly.message

    def test_missing_count_fails_closed(self, recon_counts_missing):
        """[MISSING] is a rule failure, never a TypeError and never a 0."""
        (anomaly,) = change_counts_reconcile(recon_counts_missing)
        assert anomaly.observed == MISSING
        assert "updates" in anomaly.message

    def test_aggregate_anomaly_has_no_record(self, recon_counts_mismatch):
        (anomaly,) = change_counts_reconcile(recon_counts_mismatch)
        assert anomaly.record is None
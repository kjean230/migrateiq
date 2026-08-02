# tests/validation/test_registry.py
"""Registry guards. Independent of rules.py — REGISTRY is populated with stubs.

The fixture snapshots and restores the module-level REGISTRY: these tests
mutate global state, and a leaked stub would corrupt every later test.
"""

import pytest

from migrateiq.contracts.enums import (
    BlockingMode, EnforcementPoint, EnforcementScope, RuleId, Severity,
)
from migrateiq.validation import registry as reg
from migrateiq.validation.spec import RuleSpec, load_specs

_AGGREGATE = {RuleId.CHANGE_COUNTS_RECONCILE, RuleId.RECORD_COUNT_TOLERANCE}


@pytest.fixture
def clean_registry():
    """Snapshot REGISTRY, hand back an empty one, restore on teardown."""
    saved = dict(reg.REGISTRY)
    reg.REGISTRY.clear()
    yield reg.REGISTRY
    reg.REGISTRY.clear()
    reg.REGISTRY.update(saved)


@pytest.fixture
def full_registry(clean_registry):
    """All eight RuleIds registered with no-op stubs of the correct kind."""
    for rule_id in RuleId:
        decorate = reg.aggregate_rule if rule_id in _AGGREGATE else reg.record_rule
        decorate(rule_id)(lambda ctx: [])
    return clean_registry


@pytest.fixture
def specs():
    return load_specs()


def test_stub_registry_is_complete(full_registry):
    reg.verify_registry()


def test_missing_implementation_raises(full_registry):
    full_registry.pop(RuleId.POLICY_ID_NOT_NULL)
    with pytest.raises(reg.RegistryError, match="DQ001"):
        reg.verify_registry()


def test_duplicate_registration_raises(full_registry):
    with pytest.raises(reg.RegistryError, match="registered twice"):
        reg.record_rule(RuleId.POLICY_ID_NOT_NULL)(lambda ctx: [])


def test_packaged_specs_pass_verification(full_registry, specs):
    reg.verify_specs(specs)


def test_missing_spec_raises(full_registry, specs):
    del specs[RuleId.MEMBER_ID_ON_CLAIMS]
    with pytest.raises(reg.RegistryError, match="no spec in config"):
        reg.verify_specs(specs)


def test_spec_without_implementation_raises(full_registry, specs):
    full_registry.pop(RuleId.RECORD_COUNT_TOLERANCE)
    with pytest.raises(reg.RegistryError, match="no implementation registered"):
        reg.verify_specs(specs)


def test_kind_scope_mismatch_raises(full_registry, specs):
    """DQ001 is registered as a record rule; specced under UAT it must fail.

    Built through the constructor, not model_copy — model_copy(update=...)
    bypasses validation, so it could produce a RuleSpec that RuleSpec itself
    would reject, and the test would be asserting against an impossible input.
    """
    specs[RuleId.POLICY_ID_NOT_NULL] = RuleSpec(
        rule_id=RuleId.POLICY_ID_NOT_NULL,
        scope=EnforcementScope.UAT,
        enforcement_point=EnforcementPoint.UAT_GATE,
        severity=Severity.ERROR,
        blocking=BlockingMode.ALWAYS,
        description="deliberately misscoped",
    )
    with pytest.raises(reg.RegistryError, match="specced under scope"):
        reg.verify_specs(specs)


def test_load_specs_covers_every_rule(specs):
    assert set(specs) == set(RuleId)


def test_load_specs_blocking_set(specs):
    """Only DQ001/DQ007/DQ008 can block delivery — §3.2 flag-and-surface."""
    blocking = {r for r, s in specs.items() if s.blocking is not BlockingMode.NEVER}
    assert blocking == {
        RuleId.POLICY_ID_NOT_NULL,
        RuleId.CHANGE_COUNTS_RECONCILE,
        RuleId.RECORD_COUNT_TOLERANCE,
    }
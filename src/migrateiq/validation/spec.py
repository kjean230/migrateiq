# src/migrateiq/validation/spec.py
"""Rule metadata. rules.yaml is the serialized form of this model."""

from pydantic import Field, model_validator

from ..contracts.base import Contract
from ..contracts.enums import (
    RULE_ANOMALY_CODE, AnomalyCode, BlockingMode, EnforcementPoint,
    EnforcementScope, RuleId, Severity,
)
from pathlib import Path
import yaml
from collections.abc import Mapping
from importlib.resources import files

_AGENT_POINTS = frozenset({
    EnforcementPoint.AGENT_VALIDATION, EnforcementPoint.AGENT_SCHEMA_MAPPING,
})


class RuleSpec(Contract):
    rule_id: RuleId
    scope: EnforcementScope
    enforcement_point: EnforcementPoint
    severity: Severity
    blocking: BlockingMode
    tolerance: float | None = Field(default=None, ge=0.0, le=1.0)
    blocking_threshold: float | None = Field(default=None, gt=0.0, le=1.0)
    description: str = Field(min_length=1)

    @property
    def anomaly_code(self) -> AnomalyCode:
        return RULE_ANOMALY_CODE[self.rule_id]

    @model_validator(mode="after")
    def _coherent(self):
        if self.scope is EnforcementScope.UAT:
            if self.enforcement_point is not EnforcementPoint.UAT_GATE:
                raise ValueError(f"{self.rule_id}: UAT scope requires UAT_GATE point")
        elif self.enforcement_point not in _AGENT_POINTS:
            raise ValueError(f"{self.rule_id}: AGENT scope requires an agent point")

        if self.blocking is BlockingMode.THRESHOLD:
            if self.blocking_threshold is None:
                raise ValueError(f"{self.rule_id}: THRESHOLD needs blocking_threshold")
        elif self.blocking_threshold is not None:
            raise ValueError(f"{self.rule_id}: blocking_threshold only for THRESHOLD")

        if self.blocking is not BlockingMode.NEVER and self.severity is not Severity.ERROR:
            raise ValueError(f"{self.rule_id}: blocking rules must be ERROR")
        return self
    

_DEFAULT_CONFIG = "rules.yaml"


def load_specs(path: Path | None = None) -> dict[RuleId, RuleSpec]:
    """Load and validate the spec set.

    path=None reads the packaged rules.yaml. Passing a path is the Databricks
    override: a workspace-local config can be loaded and handed to
    verify_specs() before any rule runs against it.

    Pure: reads one file, constructs models, no registry access.
    """
    if path is None:
        raw = (files("migrateiq.validation") / _DEFAULT_CONFIG).read_text()
    else:
        raw = Path(path).read_text()

    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict) or "rules" not in doc:
        raise ValueError(f"rule config missing top-level 'rules' key: {path or _DEFAULT_CONFIG}")
    if doc.get("version") != 1:
        raise ValueError(f"unsupported rule config version: {doc.get('version')!r}")

    out: dict[RuleId, RuleSpec] = {}
    for entry in doc["rules"]:
        spec = RuleSpec(**entry)
        if spec.rule_id in out:
            raise ValueError(f"{spec.rule_id} specced twice in {path or _DEFAULT_CONFIG}")
        out[spec.rule_id] = spec
    return out
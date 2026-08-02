# src/migrateiq/validation/context.py
"""Rule inputs. Two types, one per rule kind.

RecordContext carries one projected row. ReconContext carries aggregate counts
and NO rows — that is what makes DQ007/DQ008 runnable inside a Spark job
without shipping 100K records to the driver. Do not add a rows field.

These are frozen dataclasses, not pydantic models: one RecordContext is built
per row, and per-row validation of an already-validated projection is cost
without a guarantee. Deviation #12.
"""

from dataclasses import dataclass
from collections.abc import Mapping

from ..contracts.base import MISSING, RecordRef
from ..contracts.enums import CanonicalField, Domain
from ..contracts.findings import ChangeCounts, Findings
from .spec import RuleSpec


@dataclass(frozen=True, slots=True)
class RecordContext:
    """One source row projected onto canonical fields.

    The mapped/null distinction is load-bearing. A field absent from the
    FieldMap is NOT EVALUABLE; a mapped field holding None is a VIOLATION.
    Collapsing the two turns an unmapped column into a clean PASS.
    """

    ref: RecordRef
    values: Mapping[CanonicalField, object]
    mapped: frozenset[CanonicalField]
    domain: Domain

    def is_mapped(self, field: CanonicalField) -> bool:
        return field in self.mapped

    def get(self, field: CanonicalField) -> object | None:
        """Value, or None when unmapped or null. Check is_mapped to tell apart."""
        return self.values.get(field)

    def is_null(self, field: CanonicalField) -> bool:
        """Mapped but empty. False when unmapped — that is not evaluable."""
        if field not in self.mapped:
            return False
        v = self.values.get(field)
        return v is None or (isinstance(v, str) and not v.strip())


@dataclass(frozen=True, slots=True)
class ReconContext:
    """Aggregate reconciliation input. No rows, by design.

    source_record_count is authoritative, taken from NormalizedDocument.
    Findings.source_record_count is the agent's echo of it; a disagreement
    between the two is itself a DQ008 signal.
    """

    findings: Findings
    source_record_count: int
    spec: RuleSpec

    @property
    def change_counts(self) -> ChangeCounts:
        return self.findings.change_counts

    @property
    def missing_change_counts(self) -> tuple[str, ...]:
        """Change-count fields holding the [MISSING] sentinel.

        DQ007 must fail closed on these rather than raising TypeError on
        int + str, so it type-narrows through this instead of summing blind.
        """
        cc = self.change_counts
        return tuple(
            name
            for name in ("inserts", "updates", "soft_deletes")
            if getattr(cc, name) == MISSING
        )
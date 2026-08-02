import pytest
from pydantic import ValidationError

from migrateiq.contracts.base import RecordRef
from migrateiq.contracts.enums import AnomalyCode
from migrateiq.contracts.findings import Anomaly


def test_record_level_code_requires_record():
    with pytest.raises(ValidationError):
        Anomaly(code=AnomalyCode.MISSING_FIELD, message="x")


def test_aggregate_code_rejects_record():
    with pytest.raises(ValidationError):
        Anomaly(
            code=AnomalyCode.VOLUME_DRIFT,
            record=RecordRef(sheet="Sheet1", source_row_number=2),
            message="x",
        )
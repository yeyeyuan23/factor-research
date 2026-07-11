import pandas as pd
import pytest

from pb_roe.data.schema import SchemaError, canonical_security_id, normalize_table


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("sh.600000", "600000.SH"), ("000001", "000001.SZ"), ("600001.SH", "600001.SH")],
)
def test_canonical_security_id(raw: str, expected: str) -> None:
    assert canonical_security_id(raw) == expected


def test_invalid_security_id_is_rejected() -> None:
    with pytest.raises(SchemaError):
        canonical_security_id("not-a-stock")


def test_normalize_table_rejects_missing_columns() -> None:
    with pytest.raises(SchemaError, match="missing columns"):
        normalize_table("prices", pd.DataFrame({"security_id": ["000001.SZ"]}))

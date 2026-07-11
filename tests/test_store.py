import pytest

from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.data.store import ParquetStore


def test_parquet_store_round_trip_and_immutability(tmp_path) -> None:
    store = ParquetStore(tmp_path)
    bundle = fixture_bundle()

    stored = store.write_bundle(bundle)
    loaded = store.read_bundle()

    assert {item.name for item in stored} == set(bundle.tables())
    assert len(loaded.prices) == len(bundle.prices)
    with pytest.raises(FileExistsError):
        store.write("prices", bundle.prices)

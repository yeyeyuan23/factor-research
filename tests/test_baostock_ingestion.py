from types import SimpleNamespace

import pandas as pd

from pb_roe.data import ingest_baostock
from pb_roe.data.ingest_baostock import (
    _download_price_jobs,
    _quarter_for_signal,
    reconstruct_membership_intervals,
)
from pb_roe.reproduction.schedule import paper_rebalance_dates


def test_signal_date_maps_to_latest_expected_reporting_quarter() -> None:
    assert _quarter_for_signal(pd.Timestamp("2022-04-30")) == (2022, 1)
    assert _quarter_for_signal(pd.Timestamp("2022-08-31")) == (2022, 2)
    assert _quarter_for_signal(pd.Timestamp("2022-10-31")) == (2022, 3)
    assert _quarter_for_signal(pd.Timestamp("2022-12-30")) == (2022, 4)
    assert _quarter_for_signal(pd.Timestamp("2022-05-09")) == (2022, 1)
    assert _quarter_for_signal(pd.Timestamp("2022-09-01")) == (2022, 2)
    assert _quarter_for_signal(pd.Timestamp("2022-11-01")) == (2022, 3)


def test_membership_snapshots_become_half_open_intervals() -> None:
    snapshots = {
        pd.Timestamp("2022-01-31"): pd.DataFrame(
            {"code": ["sh.600000", "sz.000001"], "code_name": ["A", "B"]}
        ),
        pd.Timestamp("2022-02-28"): pd.DataFrame(
            {"code": ["sh.600000", "sz.000002"], "code_name": ["A", "C"]}
        ),
    }

    membership = reconstruct_membership_intervals(snapshots)

    january = membership[membership["member_from"] == pd.Timestamp("2022-01-31")]
    february = membership[membership["member_from"] == pd.Timestamp("2022-02-28")]
    assert january["member_to"].eq(pd.Timestamp("2022-02-28")).all()
    assert february["member_to"].isna().all()
    assert january["weight"].eq(0.5).all()


def test_paper_schedule_can_use_pre_start_calendar_buffer() -> None:
    calendar = pd.bdate_range("2005-04-18", "2005-05-02")

    dates = paper_rebalance_dates("2005-04-30", "2005-05-02", calendar, ["04-30"])

    assert dates == [pd.Timestamp("2005-04-29")]


def test_price_jobs_reuse_one_baostock_session(monkeypatch, tmp_path) -> None:
    calls = {"login": 0, "logout": 0, "query": 0}

    def login():
        calls["login"] += 1
        return SimpleNamespace(error_code="0", error_msg="")

    def logout():
        calls["logout"] += 1

    def query(*args, **kwargs):
        calls["query"] += 1
        return object()

    raw = pd.DataFrame(
        {
            "date": ["2023-01-03"],
            "code": ["sh.600000"],
            "open": ["10"],
            "high": ["11"],
            "low": ["9"],
            "close": ["10.5"],
            "volume": ["100"],
            "amount": ["1000"],
            "tradestatus": ["1"],
            "isST": ["0"],
            "pbMRQ": ["1.2"],
        }
    )
    monkeypatch.setattr(ingest_baostock.bs, "login", login)
    monkeypatch.setattr(ingest_baostock.bs, "logout", logout)
    monkeypatch.setattr(ingest_baostock.bs, "query_history_k_data_plus", query)
    monkeypatch.setattr(ingest_baostock, "_result_frame", lambda result: raw)
    jobs = [
        ("600000.SH", "2023-01-01", "2023-01-31", str(tmp_path / "600000.SH.parquet")),
        ("000001.SZ", "2023-01-01", "2023-01-31", str(tmp_path / "000001.SZ.parquet")),
    ]

    _download_price_jobs(jobs)

    assert calls == {"login": 1, "logout": 1, "query": 2}


def test_price_jobs_reconnect_after_query_failure(monkeypatch, tmp_path) -> None:
    calls = {"login": 0, "logout": 0, "query": 0}

    def login():
        calls["login"] += 1
        return SimpleNamespace(error_code="0", error_msg="")

    def logout():
        calls["logout"] += 1

    def query(*args, **kwargs):
        calls["query"] += 1
        if calls["query"] == 1:
            raise ConnectionResetError("connection reset")
        return object()

    raw = pd.DataFrame({field: [] for field in ingest_baostock.PRICE_FIELDS.split(",")})
    monkeypatch.setattr(ingest_baostock.bs, "login", login)
    monkeypatch.setattr(ingest_baostock.bs, "logout", logout)
    monkeypatch.setattr(ingest_baostock.bs, "query_history_k_data_plus", query)
    monkeypatch.setattr(ingest_baostock, "_result_frame", lambda result: raw)

    _download_price_jobs(
        [("600000.SH", "2023-01-01", "2023-01-31", str(tmp_path / "price.parquet"))]
    )

    assert calls == {"login": 2, "logout": 2, "query": 2}

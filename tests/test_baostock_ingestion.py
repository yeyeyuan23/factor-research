import pandas as pd

from pb_roe.data.ingest_baostock import _quarter_for_signal, reconstruct_membership_intervals
from pb_roe.reproduction.schedule import paper_rebalance_dates


def test_signal_date_maps_to_latest_expected_reporting_quarter() -> None:
    assert _quarter_for_signal(pd.Timestamp("2022-04-30")) == (2022, 1)
    assert _quarter_for_signal(pd.Timestamp("2022-08-31")) == (2022, 2)
    assert _quarter_for_signal(pd.Timestamp("2022-10-31")) == (2022, 3)
    assert _quarter_for_signal(pd.Timestamp("2022-12-30")) == (2022, 4)


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

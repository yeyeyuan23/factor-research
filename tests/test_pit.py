import pandas as pd

from pb_roe.data.pit import active_members, fundamentals_asof


def test_active_members_respects_half_open_intervals() -> None:
    membership = pd.DataFrame(
        {
            "universe_id": ["CSI300", "CSI300"],
            "security_id": ["000001.SZ", "000002.SZ"],
            "member_from": ["2020-01-01", "2022-02-01"],
            "member_to": ["2022-02-01", None],
        }
    )

    members = active_members(membership, "2022-02-01")

    assert members["security_id"].tolist() == ["000002.SZ"]


def test_fundamentals_asof_never_uses_future_revision() -> None:
    signals = pd.DataFrame(
        {
            "signal_date": ["2022-04-20", "2022-05-20"],
            "security_id": ["000001.SZ", "000001.SZ"],
        }
    )
    fundamentals = pd.DataFrame(
        {
            "security_id": ["000001.SZ", "000001.SZ"],
            "metric": ["roe", "roe"],
            "report_period": ["2021-12-31", "2021-12-31"],
            "effective_date": ["2022-04-01", "2022-05-01"],
            "value": [0.10, 0.08],
        }
    )

    selected = fundamentals_asof(signals, fundamentals)

    assert selected["value"].tolist() == [0.10, 0.08]
    assert (selected["effective_date"] <= selected["signal_date"]).all()


def test_fundamentals_asof_selects_each_metric_independently() -> None:
    signals = pd.DataFrame(
        {"signal_date": ["2022-04-20"], "security_id": ["000001.SZ"]}
    )
    fundamentals = pd.DataFrame(
        {
            "security_id": ["000001.SZ", "000001.SZ", "000001.SZ"],
            "metric": ["pb", "roe", "roe"],
            "report_period": ["2022-03-31", "2021-12-31", "2022-03-31"],
            "effective_date": ["2022-04-10", "2022-04-01", "2022-04-30"],
            "value": [1.2, 0.1, 0.2],
        }
    )

    selected = fundamentals_asof(signals, fundamentals).sort_values("metric")

    assert selected[["metric", "value"]].values.tolist() == [["pb", 1.2], ["roe", 0.1]]

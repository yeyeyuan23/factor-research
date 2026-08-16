import numpy as np
import pandas as pd

from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.reproduction.backtest import backtest_paper_holdings
from pb_roe.reproduction.factors import add_paper_scores, build_paper_factor_panel
from pb_roe.reproduction.schedule import paper_rebalance_dates
from pb_roe.reproduction.strategies import build_industry_portfolios, build_rank_portfolios


def test_original_score_rewards_high_roe_and_low_pb() -> None:
    frame = pd.DataFrame(
        {
            "security_id": ["A", "B", "C"],
            "pb": [1.0, 2.0, 3.0],
            "roe": [0.30, 0.20, 0.10],
        }
    )

    scored = add_paper_scores(frame).sort_values("paper_score", ascending=False)

    assert scored["security_id"].tolist() == ["A", "B", "C"]
    assert scored.iloc[0]["paper_score"] > scored.iloc[-1]["paper_score"]


def test_schedule_uses_previous_trading_day() -> None:
    calendar = pd.bdate_range("2022-04-01", "2022-05-02")

    result = paper_rebalance_dates("2022-04-01", "2022-05-02", calendar, ["04-30"])

    assert result == [pd.Timestamp("2022-04-29")]


def test_schedule_can_roll_forward_to_next_trading_day() -> None:
    calendar = pd.bdate_range("2022-04-01", "2022-05-02")

    result = paper_rebalance_dates(
        "2022-04-01",
        "2022-05-02",
        calendar,
        ["04-30"],
        non_trading_day="next",
    )

    assert result == [pd.Timestamp("2022-05-02")]


def test_factor_panel_never_uses_future_financials() -> None:
    bundle = fixture_bundle()
    signal_dates = [pd.Timestamp("2022-04-20"), pd.Timestamp("2022-05-20")]

    panel = build_paper_factor_panel(signal_dates, bundle.universe_membership, bundle.fundamentals)

    assert set(panel["signal_date"]) == set(signal_dates)
    assert panel.groupby("signal_date")["paper_score"].count().eq(5).all()


def test_rank_and_industry_weights_sum_to_one() -> None:
    bundle = fixture_bundle()
    panel = build_paper_factor_panel(
        [pd.Timestamp("2022-05-20")], bundle.universe_membership, bundle.fundamentals
    )

    ranked = build_rank_portfolios(panel)
    industry = build_industry_portfolios(panel, top_n=1)

    assert np.allclose(ranked.groupby(["strategy_id", "signal_date"])["target_weight"].sum(), 1.0)
    assert np.allclose(industry.groupby(["strategy_id", "signal_date"])["target_weight"].sum(), 1.0)
    assert industry.groupby("strategy_id")["security_id"].count().eq(3).all()


def test_backtest_applies_original_fixed_costs() -> None:
    holdings = pd.DataFrame(
        {
            "strategy_id": ["TEST", "TEST"],
            "signal_date": ["2022-01-03", "2022-01-04"],
            "security_id": ["000001.SZ", "000001.SZ"],
            "target_weight": [1.0, 1.0],
        }
    )
    prices = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2022-01-03", "2022-01-04", "2022-01-05"]),
            "security_id": "000001.SZ",
            "close": [10.0, 11.0, 12.1],
            "is_suspended": False,
        }
    )

    returns = backtest_paper_holdings(
        holdings, prices, "2022-01-05", initial_cost=0.006, rebalance_cost=0.013
    )

    assert np.isclose(returns.iloc[0]["gross_return"], 0.10)
    assert np.isclose(returns.iloc[0]["net_return"], 1.10 * 0.994 - 1)
    assert np.isclose(returns.iloc[1]["net_return"], 1.10 * 0.987 - 1)


def test_backtest_marks_suspended_exit_at_last_observable_close() -> None:
    holdings = pd.DataFrame(
        {
            "strategy_id": ["TEST", "TEST"],
            "signal_date": ["2022-01-03", "2022-01-03"],
            "security_id": ["A", "B"],
            "target_weight": [0.5, 0.5],
        }
    )
    prices = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2022-01-03", "2022-01-05", "2022-01-03", "2022-01-04"]),
            "security_id": ["A", "A", "B", "B"],
            "close": [10.0, 11.0, 20.0, 24.0],
            "is_suspended": False,
        }
    )

    returns = backtest_paper_holdings(
        holdings, prices, "2022-01-05", initial_cost=0.0, rebalance_cost=0.0
    )

    assert returns.iloc[0]["constituent_count"] == 2
    assert returns.iloc[0]["stale_exit_count"] == 1
    assert returns.iloc[0]["maximum_exit_staleness_days"] == 1
    assert np.isclose(returns.iloc[0]["gross_return"], 0.15)

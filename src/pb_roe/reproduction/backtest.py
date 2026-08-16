"""Close-to-close backtest matching the original paper execution convention."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pb_roe.data.schema import require_columns


def _close_lookup(prices: pd.DataFrame) -> pd.Series:
    valid = prices.loc[~prices["is_suspended"].fillna(False)].copy()
    return valid.set_index(["trade_date", "security_id"])["close"].sort_index()


def backtest_paper_holdings(
    holdings: pd.DataFrame,
    prices: pd.DataFrame,
    final_date: object,
    initial_cost: float = 0.006,
    rebalance_cost: float = 0.013,
) -> pd.DataFrame:
    require_columns(
        holdings,
        ("strategy_id", "signal_date", "security_id", "target_weight"),
        "holdings",
    )
    require_columns(prices, ("trade_date", "security_id", "close", "is_suspended"), "prices")
    prices = prices.copy()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"]).dt.normalize()
    close = _close_lookup(prices)
    final = pd.Timestamp(final_date).normalize()
    available_dates = prices["trade_date"].drop_duplicates().sort_values()
    final_candidates = available_dates[available_dates <= final]
    if final_candidates.empty:
        raise ValueError("No price date on or before final_date")
    final = pd.Timestamp(final_candidates.iloc[-1])

    rows: list[dict[str, object]] = []
    for strategy_id, strategy_holdings in holdings.groupby("strategy_id", sort=True):
        signal_dates = sorted(pd.to_datetime(strategy_holdings["signal_date"]).unique())
        for period_index, signal_date in enumerate(signal_dates):
            signal = pd.Timestamp(signal_date).normalize()
            period_end = (
                pd.Timestamp(signal_dates[period_index + 1]).normalize()
                if period_index + 1 < len(signal_dates)
                else final
            )
            selected = strategy_holdings[
                pd.to_datetime(strategy_holdings["signal_date"]).dt.normalize() == signal
            ].copy()
            start_keys = pd.MultiIndex.from_arrays(
                [[signal] * len(selected), selected["security_id"]]
            )
            start_prices = close.reindex(start_keys).to_numpy(dtype=float)
            exit_observations = (
                prices.loc[
                    prices["trade_date"].le(period_end)
                    & ~prices["is_suspended"].fillna(False)
                    & prices["security_id"].isin(selected["security_id"]),
                    ["trade_date", "security_id", "close"],
                ]
                .sort_values(["security_id", "trade_date"])
                .groupby("security_id", as_index=False)
                .tail(1)
                .set_index("security_id")
            )
            end_prices = (
                selected["security_id"].map(exit_observations["close"]).to_numpy(dtype=float)
            )
            exit_dates = pd.to_datetime(
                selected["security_id"].map(exit_observations["trade_date"])
            )
            tradable = np.isfinite(start_prices) & np.isfinite(end_prices) & (start_prices > 0)
            if not tradable.any():
                continue
            weights = selected["target_weight"].to_numpy(dtype=float)[tradable]
            weights = weights / weights.sum()
            asset_returns = end_prices[tradable] / start_prices[tradable] - 1
            exit_staleness = (period_end - exit_dates[tradable]).dt.days
            gross_return = float(np.dot(weights, asset_returns))
            is_benchmark = strategy_id == "R0_UNIVERSE_EW"
            cost = 0.0 if is_benchmark else initial_cost if period_index == 0 else rebalance_cost
            net_return = (1 + gross_return) * (1 - cost) - 1
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "rebalance_date": signal,
                    "period_end": period_end,
                    "gross_return": gross_return,
                    "transaction_cost": cost,
                    "net_return": net_return,
                    "constituent_count": int(tradable.sum()),
                    "stale_exit_count": int(exit_staleness.gt(0).sum()),
                    "maximum_exit_staleness_days": int(exit_staleness.max()),
                }
            )
    returns = pd.DataFrame(rows)
    if returns.empty:
        return returns
    benchmark = returns[returns["strategy_id"] == "R0_UNIVERSE_EW"][
        ["rebalance_date", "gross_return"]
    ].rename(columns={"gross_return": "benchmark_return"})
    return returns.merge(benchmark, on="rebalance_date", how="left", validate="many_to_one")


def summarize_paper_returns(returns: pd.DataFrame) -> pd.DataFrame:
    if returns.empty:
        return pd.DataFrame()
    summaries: list[dict[str, object]] = []
    for strategy_id, periods in returns.groupby("strategy_id", sort=True):
        periods = periods.sort_values("rebalance_date")
        cumulative_gross = float((1 + periods["gross_return"]).prod() - 1)
        cumulative_net = float((1 + periods["net_return"]).prod() - 1)
        days = max((periods["period_end"].max() - periods["rebalance_date"].min()).days, 1)
        years = days / 365.25
        annualized_net = (1 + cumulative_net) ** (1 / years) - 1 if cumulative_net > -1 else -1.0
        excess = periods["gross_return"] - periods["benchmark_return"]
        summaries.append(
            {
                "strategy_id": strategy_id,
                "periods": len(periods),
                "cumulative_gross_return": cumulative_gross,
                "cumulative_net_return": cumulative_net,
                "annualized_net_return": annualized_net,
                "benchmark_win_count": int(excess.gt(0).sum()),
                "benchmark_win_rate": float(excess.gt(0).mean()),
            }
        )
    return pd.DataFrame(summaries)

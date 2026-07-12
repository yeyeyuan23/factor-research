"""Factor sorting, turnover, costs, and long-short spreads."""

from __future__ import annotations

import pandas as pd

from pb_roe.data.schema import require_columns


def assign_quantiles(
    panel: pd.DataFrame,
    factor_column: str,
    quantiles: int = 5,
    date_column: str = "signal_date",
) -> pd.Series:
    require_columns(panel, (date_column, factor_column), "factor_panel")
    if quantiles < 2:
        raise ValueError("At least two quantiles are required")
    assignments = pd.Series(pd.NA, index=panel.index, dtype="Int64")
    for _, snapshot in panel.groupby(date_column):
        valid = snapshot[factor_column].dropna()
        bins = min(quantiles, len(valid))
        if bins < 2:
            continue
        ranks = valid.rank(method="first")
        assignments.loc[valid.index] = pd.qcut(ranks, q=bins, labels=False).astype(int) + 1
    return assignments


def _turnover(previous: pd.Series | None, current: pd.Series) -> float:
    if previous is None:
        return 1.0
    all_securities = previous.index.union(current.index)
    return float(
        0.5
        * (
            current.reindex(all_securities, fill_value=0)
            - previous.reindex(all_securities, fill_value=0)
        )
        .abs()
        .sum()
    )


def quantile_backtest(
    panel: pd.DataFrame,
    factor_column: str,
    return_column: str = "forward_return",
    quantiles: int = 5,
    cost_rate: float = 0.003,
) -> pd.DataFrame:
    require_columns(
        panel,
        ("signal_date", "security_id", factor_column, return_column),
        "factor_panel",
    )
    working = panel.copy()
    working["quantile"] = assign_quantiles(working, factor_column, quantiles)
    rows: list[dict[str, object]] = []
    previous_weights: dict[int, pd.Series] = {}
    for signal_date, snapshot in working.groupby("signal_date", sort=True):
        for quantile, group in snapshot.dropna(subset=["quantile", return_column]).groupby(
            "quantile"
        ):
            quantile = int(quantile)
            weights = pd.Series(1 / len(group), index=group["security_id"])
            turnover = _turnover(previous_weights.get(quantile), weights)
            gross_return = float(group[return_column].mean())
            rows.append(
                {
                    "signal_date": pd.Timestamp(signal_date),
                    "factor": factor_column,
                    "quantile": quantile,
                    "constituent_count": len(group),
                    "turnover": turnover,
                    "gross_return": gross_return,
                    "transaction_cost": turnover * cost_rate,
                    "net_return": gross_return - turnover * cost_rate,
                }
            )
            previous_weights[quantile] = weights
    return pd.DataFrame(rows)


def long_short_spread(quantile_returns: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        quantile_returns,
        (
            "signal_date",
            "factor",
            "quantile",
            "gross_return",
            "transaction_cost",
        ),
        "quantile_returns",
    )
    rows: list[dict[str, object]] = []
    grouping = ["signal_date", "factor"]
    if "cost_rate" in quantile_returns:
        grouping.append("cost_rate")
    for keys, group in quantile_returns.groupby(grouping):
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_values = dict(zip(grouping, keys, strict=True))
        bottom = group.loc[group["quantile"].idxmin()]
        top = group.loc[group["quantile"].idxmax()]
        gross_spread = float(top["gross_return"] - bottom["gross_return"])
        total_cost = float(top["transaction_cost"] + bottom["transaction_cost"])
        rows.append(
            {
                **key_values,
                "gross_spread": gross_spread,
                "turnover": float(top["turnover"] + bottom["turnover"]),
                "transaction_cost": total_cost,
                "net_spread": gross_spread - total_cost,
            }
        )
    return pd.DataFrame(rows)

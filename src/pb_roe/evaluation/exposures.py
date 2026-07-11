"""Industry exposure and cross-factor correlation diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from pb_roe.evaluation.quantiles import assign_quantiles


def top_quantile_industry_exposure(
    panel: pd.DataFrame,
    factor_column: str,
    industry_column: str = "industry",
    quantiles: int = 5,
) -> pd.DataFrame:
    working = panel.dropna(subset=[industry_column]).copy()
    working["quantile"] = assign_quantiles(working, factor_column, quantiles)
    rows: list[dict[str, object]] = []
    for signal_date, snapshot in working.groupby("signal_date", sort=True):
        universe = snapshot[industry_column].value_counts(normalize=True)
        top_id = snapshot["quantile"].max()
        top = snapshot.loc[snapshot["quantile"] == top_id, industry_column].value_counts(
            normalize=True
        )
        for industry in sorted(set(universe.index) | set(top.index)):
            rows.append(
                {
                    "signal_date": pd.Timestamp(signal_date),
                    "factor": factor_column,
                    "industry": industry,
                    "portfolio_weight": float(top.get(industry, 0.0)),
                    "universe_weight": float(universe.get(industry, 0.0)),
                    "active_weight": float(top.get(industry, 0.0) - universe.get(industry, 0.0)),
                }
            )
    return pd.DataFrame(rows)


def mean_factor_correlation(panel: pd.DataFrame, factor_columns: Iterable[str]) -> pd.DataFrame:
    factors = list(factor_columns)
    correlations = [
        snapshot[factors].corr(method="spearman")
        for _, snapshot in panel.groupby("signal_date")
        if len(snapshot) >= 3
    ]
    if not correlations:
        return pd.DataFrame(index=factors, columns=factors, dtype=float)
    stacked = pd.concat(correlations, keys=range(len(correlations)), names=["period", "factor"])
    return stacked.groupby(level="factor").mean().reindex(index=factors, columns=factors)

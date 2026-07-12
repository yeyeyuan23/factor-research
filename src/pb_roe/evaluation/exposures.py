"""Industry exposure and cross-factor correlation diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from pb_roe.data.schema import require_columns
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


def top_quantile_capacity(
    panel: pd.DataFrame,
    factor_column: str,
    quantiles: int = 5,
    participation_rate: float = 0.10,
) -> pd.DataFrame:
    """Estimate conservative equal-weight capacity for a full Top-quantile rebalance."""

    require_columns(
        panel,
        ("signal_date", "security_id", factor_column, "adv_20d"),
        "factor_panel",
    )
    working = panel.copy()
    working["quantile"] = assign_quantiles(working, factor_column, quantiles)
    rows: list[dict[str, object]] = []
    for signal_date, snapshot in working.groupby("signal_date", sort=True):
        top = snapshot[snapshot["quantile"].eq(snapshot["quantile"].max())]
        adv = pd.to_numeric(top["adv_20d"], errors="coerce")
        valid_adv = adv[adv.gt(0)]
        constituents = len(top)
        capacity = (
            float((valid_adv * participation_rate * constituents).min())
            if len(valid_adv) == constituents and constituents
            else float("nan")
        )
        rows.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "factor": factor_column,
                "constituents": constituents,
                "adv_coverage": float(adv.gt(0).mean()) if constituents else 0.0,
                "median_adv_20d": (
                    float(valid_adv.median()) if not valid_adv.empty else float("nan")
                ),
                "full_rebalance_capacity_cny": capacity,
                "participation_rate": participation_rate,
            }
        )
    return pd.DataFrame(rows)

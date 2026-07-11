"""Rank IC time series and HAC-adjusted summary statistics."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pb_roe.data.schema import require_columns


def calculate_ic(
    panel: pd.DataFrame,
    factor_columns: Iterable[str],
    return_column: str = "forward_return",
    date_column: str = "signal_date",
    minimum_observations: int = 3,
) -> pd.DataFrame:
    factors = tuple(factor_columns)
    require_columns(panel, (date_column, return_column, *factors), "factor_panel")
    rows: list[dict[str, object]] = []
    for signal_date, snapshot in panel.groupby(date_column, sort=True):
        for factor in factors:
            valid = snapshot[[factor, return_column]].dropna()
            ic = np.nan
            if (
                len(valid) >= minimum_observations
                and valid[factor].nunique() > 1
                and valid[return_column].nunique() > 1
            ):
                ic = valid[factor].corr(valid[return_column], method="spearman")
            rows.append(
                {
                    "signal_date": pd.Timestamp(signal_date),
                    "factor": factor,
                    "ic": ic,
                    "observations": len(valid),
                }
            )
    return pd.DataFrame(rows)


def _newey_west_tstat(values: pd.Series) -> float:
    clean = values.dropna().astype(float)
    if len(clean) < 3 or clean.std(ddof=1) == 0:
        return float("nan")
    max_lags = max(1, int(np.floor(4 * (len(clean) / 100) ** (2 / 9))))
    model = sm.OLS(clean.to_numpy(), np.ones((len(clean), 1))).fit(
        cov_type="HAC", cov_kwds={"maxlags": max_lags}
    )
    return float(model.tvalues[0])


def summarize_ic(ic_series: pd.DataFrame, annualization: int = 12) -> pd.DataFrame:
    require_columns(ic_series, ("factor", "ic"), "ic_series")
    rows: list[dict[str, object]] = []
    for factor, group in ic_series.groupby("factor", sort=True):
        values = group["ic"].dropna().astype(float)
        mean = float(values.mean()) if not values.empty else np.nan
        standard_deviation = float(values.std(ddof=1)) if len(values) > 1 else np.nan
        rows.append(
            {
                "factor": factor,
                "periods": len(values),
                "ic_mean": mean,
                "ic_std": standard_deviation,
                "icir": (
                    mean / standard_deviation * np.sqrt(annualization)
                    if standard_deviation and np.isfinite(standard_deviation)
                    else np.nan
                ),
                "ic_positive_rate": float(values.gt(0).mean()) if not values.empty else np.nan,
                "newey_west_t": _newey_west_tstat(values),
            }
        )
    return pd.DataFrame(rows)

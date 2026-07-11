"""Cross-sectional winsorization, standardization, and neutralization."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from pb_roe.data.schema import require_columns


def winsorize_zscore(
    frame: pd.DataFrame,
    factor_columns: Iterable[str],
    lower: float = 0.01,
    upper: float = 0.99,
    date_column: str = "signal_date",
) -> pd.DataFrame:
    factors = tuple(factor_columns)
    require_columns(frame, (date_column, *factors), "factor_panel")
    if not 0 <= lower < upper <= 1:
        raise ValueError("Winsor bounds must satisfy 0 <= lower < upper <= 1")
    result = frame.copy()
    for factor in factors:
        processed_column = f"{factor}_z"

        def transform(values: pd.Series) -> pd.Series:
            numeric = pd.to_numeric(values, errors="coerce")
            valid = numeric.dropna()
            if valid.empty:
                return pd.Series(np.nan, index=values.index)
            low, high = valid.quantile([lower, upper])
            clipped = numeric.clip(low, high)
            standard_deviation = clipped.std(ddof=0)
            if not np.isfinite(standard_deviation) or np.isclose(
                standard_deviation, 0.0, atol=1e-12
            ):
                return pd.Series(0.0, index=values.index).where(numeric.notna())
            return (clipped - clipped.mean()) / standard_deviation

        result[processed_column] = result.groupby(date_column, group_keys=False)[factor].transform(
            transform
        )
    return result


def neutralize_cross_section(
    frame: pd.DataFrame,
    factor_column: str,
    industry_column: str = "industry",
    size_column: str | None = None,
    date_column: str = "signal_date",
) -> pd.Series:
    required = [date_column, factor_column, industry_column]
    if size_column:
        required.append(size_column)
    require_columns(frame, required, "factor_panel")
    residuals = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, snapshot in frame.groupby(date_column):
        columns = [factor_column, industry_column, *([size_column] if size_column else [])]
        valid = snapshot[columns].dropna()
        if len(valid) < 3:
            continue
        y = valid[factor_column].astype(float).to_numpy()
        industry = pd.get_dummies(valid[industry_column], drop_first=True, dtype=float)
        design_parts = [np.ones((len(valid), 1)), industry.to_numpy()]
        if size_column:
            size = np.log(valid[size_column].astype(float).clip(lower=1e-12)).to_numpy()
            design_parts.append(size.reshape(-1, 1))
        design = np.column_stack(design_parts)
        fitted = design @ np.linalg.lstsq(design, y, rcond=None)[0]
        residuals.loc[valid.index] = y - fitted
    return residuals

"""Ledoit-Wolf covariance estimation from trailing daily returns."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from pb_roe.data.schema import require_columns


def trailing_return_matrix(
    prices: pd.DataFrame,
    securities: Iterable[str],
    as_of: object,
    lookback_days: int = 252,
) -> pd.DataFrame:
    require_columns(prices, ("trade_date", "security_id", "close", "is_suspended"), "prices")
    security_list = list(securities)
    working = prices.loc[
        prices["security_id"].isin(security_list) & ~prices["is_suspended"].fillna(False)
    ].copy()
    working["trade_date"] = pd.to_datetime(working["trade_date"]).dt.normalize()
    working = working[working["trade_date"] <= pd.Timestamp(as_of).normalize()]
    close = working.pivot(index="trade_date", columns="security_id", values="close").sort_index()
    close = close.reindex(columns=security_list).tail(lookback_days + 1)
    return close.pct_change(fill_method=None).iloc[1:]


def ledoit_wolf_covariance(
    returns: pd.DataFrame,
    minimum_observations: int = 60,
    annualization: int = 252,
) -> pd.DataFrame:
    if returns.empty or returns.shape[1] == 0:
        raise ValueError("Return matrix is empty")
    valid_columns = returns.count()[returns.count() >= minimum_observations].index.tolist()
    if not valid_columns:
        raise ValueError("No security has enough return observations")
    working = returns[valid_columns].copy()
    working = working.fillna(working.mean()).fillna(0.0)
    estimate = LedoitWolf().fit(working.to_numpy(dtype=float)).covariance_ * annualization
    estimate = (estimate + estimate.T) / 2
    minimum_eigenvalue = float(np.linalg.eigvalsh(estimate).min())
    if minimum_eigenvalue < 1e-10:
        estimate += np.eye(len(estimate)) * (1e-10 - minimum_eigenvalue)
    return pd.DataFrame(estimate, index=valid_columns, columns=valid_columns)

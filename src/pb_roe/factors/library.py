"""Fundamental and price-derived factor definitions."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from pb_roe.data.schema import require_columns


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce")
    numerator = pd.to_numeric(numerator, errors="coerce")
    return numerator / denominator.where(denominator.abs() > 1e-12)


def compute_fundamental_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute available factors without inventing values for absent accounting fields."""

    result = frame.copy()
    if {"book_equity", "market_cap"} <= set(result):
        result["bp"] = _safe_ratio(result["book_equity"], result["market_cap"])
    if {"ttm_net_income", "market_cap"} <= set(result):
        result["ep"] = _safe_ratio(result["ttm_net_income"], result["market_cap"])
    if {"ttm_operating_cash_flow", "market_cap"} <= set(result):
        result["ocf_to_price"] = _safe_ratio(
            result["ttm_operating_cash_flow"], result["market_cap"]
        )
    if {"ttm_net_income", "average_book_equity"} <= set(result):
        result["roe"] = _safe_ratio(result["ttm_net_income"], result["average_book_equity"])
    if {"ttm_net_income", "average_assets"} <= set(result):
        result["roa"] = _safe_ratio(result["ttm_net_income"], result["average_assets"])
    if {"ttm_gross_profit", "average_assets"} <= set(result):
        result["gross_profitability"] = _safe_ratio(
            result["ttm_gross_profit"], result["average_assets"]
        )
    if {"ttm_operating_cash_flow", "ttm_net_income"} <= set(result):
        result["cash_flow_quality"] = _safe_ratio(
            result["ttm_operating_cash_flow"], result["ttm_net_income"]
        )
    if {"revenue", "revenue_lag_year"} <= set(result):
        result["revenue_growth"] = _safe_ratio(
            result["revenue"] - result["revenue_lag_year"], result["revenue_lag_year"].abs()
        )
    if {"net_income", "net_income_lag_year"} <= set(result):
        result["earnings_growth"] = _safe_ratio(
            result["net_income"] - result["net_income_lag_year"],
            result["net_income_lag_year"].abs(),
        )
    if "roe_history_std" in result:
        result["roe_stability"] = -pd.to_numeric(result["roe_history_std"], errors="coerce")
    return result


def _trailing_return(values: pd.Series, start_offset: int, end_offset: int = 0) -> float:
    clean = values.dropna()
    needed = start_offset + 1
    if len(clean) < needed:
        return np.nan
    start = clean.iloc[-needed]
    end = clean.iloc[-(end_offset + 1)] if end_offset else clean.iloc[-1]
    return float(end / start - 1) if start > 0 else np.nan


def compute_price_factors(
    prices: pd.DataFrame,
    signal_dates: Iterable[object],
    minimum_beta_observations: int = 60,
) -> pd.DataFrame:
    require_columns(
        prices,
        ("trade_date", "security_id", "close", "amount", "is_suspended"),
        "prices",
    )
    working = prices.loc[~prices["is_suspended"].fillna(False)].copy()
    working["trade_date"] = pd.to_datetime(working["trade_date"]).dt.normalize()
    working = working.sort_values(["security_id", "trade_date"])
    working["daily_return"] = working.groupby("security_id")["close"].pct_change(
        fill_method=None
    )
    market = working.groupby("trade_date")["daily_return"].mean().rename("market_return")
    signals = {pd.Timestamp(value).normalize() for value in signal_dates}
    frames: list[pd.DataFrame] = []
    for security_id, stock in working.groupby("security_id", sort=False):
        stock = stock.set_index("trade_date").sort_index()
        returns = stock["daily_return"]
        market_returns = market.reindex(stock.index)
        covariance = returns.rolling(252, min_periods=minimum_beta_observations).cov(
            market_returns
        )
        market_variance = market_returns.rolling(
            252, min_periods=minimum_beta_observations
        ).var()
        stock_variance = returns.rolling(
            252, min_periods=minimum_beta_observations
        ).var()
        beta = covariance / market_variance.where(market_variance > 0)
        residual_variance = (stock_variance - covariance.pow(2) / market_variance).clip(
            lower=0
        )
        factors = pd.DataFrame(
            {
                "signal_date": stock.index,
                "security_id": security_id,
                "price": stock["close"],
                "momentum_12_1": stock["close"].shift(21) / stock["close"].shift(252) - 1,
                "reversal_1m": -(stock["close"] / stock["close"].shift(21) - 1),
                "volatility_60d": returns.rolling(60, min_periods=20).std() * np.sqrt(252),
                "liquidity_20d": np.log1p(stock["amount"].rolling(20, min_periods=5).mean()),
                "beta_252d": beta,
                "idiosyncratic_volatility": np.sqrt(residual_variance * 252),
            }
        )
        frames.append(factors[factors["signal_date"].isin(signals)])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

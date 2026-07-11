"""Portfolio performance metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def performance_metrics(returns: pd.Series, periods_per_year: int = 12) -> dict[str, float]:
    values = pd.to_numeric(returns, errors="coerce").dropna().astype(float)
    if values.empty:
        return {
            name: np.nan
            for name in ("annual_return", "annual_volatility", "sharpe", "max_drawdown", "calmar")
        }
    wealth = (1 + values).cumprod()
    years = len(values) / periods_per_year
    annual_return = float(wealth.iloc[-1] ** (1 / years) - 1) if wealth.iloc[-1] > 0 else -1.0
    annual_volatility = (
        float(values.std(ddof=1) * np.sqrt(periods_per_year)) if len(values) > 1 else 0.0
    )
    sharpe = annual_return / annual_volatility if annual_volatility > 0 else np.nan
    drawdown = wealth / wealth.cummax() - 1
    max_drawdown = float(drawdown.min())
    calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else np.nan
    return {
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "calmar": calmar,
    }

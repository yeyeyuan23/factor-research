"""Long-only benchmark-aware mean-variance portfolio optimization."""

from __future__ import annotations

from dataclasses import dataclass

import cvxpy as cp
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioConstraints:
    risk_aversion: float = 10.0
    turnover_penalty: float = 0.001
    max_weight: float = 0.03
    max_industry_deviation: float = 0.05
    max_turnover: float = 0.30


@dataclass(frozen=True)
class OptimizationResult:
    weights: pd.Series
    status: str
    objective_value: float | None
    turnover: float
    used_fallback: bool = False


def ranking_fallback(
    expected_returns: pd.Series,
    max_weight: float,
    top_n: int | None = None,
) -> pd.Series:
    required_count = int(np.ceil(1 / max_weight))
    count = max(required_count, top_n or required_count)
    selected = expected_returns.sort_values(ascending=False).head(min(count, len(expected_returns)))
    if selected.empty:
        raise ValueError("Cannot construct a fallback portfolio without assets")
    weights = pd.Series(0.0, index=expected_returns.index)
    weights.loc[selected.index] = 1 / len(selected)
    if weights.max() > max_weight + 1e-10:
        weights[:] = 1 / len(weights)
    return weights


def optimize_portfolio(
    expected_returns: pd.Series,
    covariance: pd.DataFrame,
    industries: pd.Series,
    benchmark_weights: pd.Series | None = None,
    previous_weights: pd.Series | None = None,
    constraints: PortfolioConstraints | None = None,
) -> OptimizationResult:
    settings = constraints or PortfolioConstraints()
    securities = [security for security in expected_returns.index if security in covariance.index]
    if not securities:
        raise ValueError("Expected returns and covariance have no common securities")
    mu = expected_returns.reindex(securities).fillna(0.0).astype(float)
    sigma = covariance.reindex(index=securities, columns=securities).astype(float)
    industry = industries.reindex(securities).fillna("Unknown")
    benchmark = (
        benchmark_weights.reindex(securities).fillna(0.0).astype(float)
        if benchmark_weights is not None
        else pd.Series(1 / len(securities), index=securities)
    )
    benchmark = benchmark / benchmark.sum()
    previous = (
        previous_weights.reindex(securities).fillna(0.0).astype(float)
        if previous_weights is not None
        else benchmark.copy()
    )
    if previous.sum() > 0:
        previous = previous / previous.sum()

    weights = cp.Variable(len(securities))
    covariance_array = cp.psd_wrap(sigma.to_numpy())
    active_weights = weights - benchmark.to_numpy()
    turnover_expression = 0.5 * cp.norm1(weights - previous.to_numpy())
    objective = cp.Maximize(
        mu.to_numpy() @ weights
        - 0.5 * settings.risk_aversion * cp.quad_form(active_weights, covariance_array)
        - settings.turnover_penalty * turnover_expression
    )
    restrictions: list[cp.Constraint] = [
        cp.sum(weights) == 1,
        weights >= 0,
        weights <= settings.max_weight,
        turnover_expression <= settings.max_turnover,
    ]
    for industry_name in sorted(industry.unique()):
        mask = (industry == industry_name).astype(float).to_numpy()
        benchmark_share = float(benchmark[industry == industry_name].sum())
        restrictions.extend(
            [
                mask @ weights <= benchmark_share + settings.max_industry_deviation,
                mask @ weights >= max(0.0, benchmark_share - settings.max_industry_deviation),
            ]
        )
    problem = cp.Problem(objective, restrictions)
    status = "error"
    for solver in (cp.CLARABEL, cp.SCS):
        try:
            problem.solve(solver=solver, verbose=False)
        except cp.error.SolverError:
            continue
        status = str(problem.status)
        if problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and weights.value is not None:
            break
    if weights.value is None or problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        fallback = ranking_fallback(mu, settings.max_weight)
        turnover = float(0.5 * (fallback - previous).abs().sum())
        return OptimizationResult(fallback, status, None, turnover, used_fallback=True)

    optimized = pd.Series(np.maximum(weights.value, 0.0), index=securities)
    optimized = optimized / optimized.sum()
    turnover = float(0.5 * (optimized - previous).abs().sum())
    return OptimizationResult(
        optimized,
        status,
        float(problem.value) if problem.value is not None else None,
        turnover,
    )

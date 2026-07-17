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
    enforce_industry_constraints: bool = True


@dataclass(frozen=True)
class OptimizationResult:
    weights: pd.Series
    status: str
    objective_value: float | None
    turnover: float
    used_fallback: bool = False
    forced_exit_weight: float = 0.0
    unavoidable_turnover_floor: float = 0.0
    turnover_limit: float = 0.0


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


def turnover_constrained_fallback(
    expected_returns: pd.Series,
    previous_weights: pd.Series,
    forced_exit_weight: float,
    max_weight: float,
    max_turnover: float,
) -> pd.Series:
    """Find the closest feasible portfolio to a ranking fallback.

    The primary mean-variance problem can fail for numerical reasons.  A fallback
    must still obey the release constraints; jumping straight to a fresh top-N
    portfolio would silently discard the turnover limit.
    """
    target = ranking_fallback(expected_returns, max_weight)
    previous = previous_weights.reindex(expected_returns.index).fillna(0.0).astype(float)
    weights = cp.Variable(len(expected_returns))
    turnover = 0.5 * (cp.norm1(weights - previous.to_numpy()) + forced_exit_weight)
    problem = cp.Problem(
        cp.Minimize(cp.norm1(weights - target.to_numpy())),
        [
            cp.sum(weights) == 1,
            weights >= 0,
            weights <= max_weight,
            turnover <= max_turnover,
        ],
    )
    for solver in (cp.CLARABEL, cp.SCS):
        try:
            problem.solve(solver=solver, verbose=False)
        except cp.error.SolverError:
            continue
        if problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) and weights.value is not None:
            fallback = pd.Series(np.maximum(weights.value, 0.0), index=expected_returns.index)
            return fallback / fallback.sum()
    return target


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
    if previous_weights is not None:
        previous_all = previous_weights.fillna(0.0).astype(float).clip(lower=0.0)
        if previous_all.sum() > 0:
            previous_all = previous_all / previous_all.sum()
        previous = previous_all.reindex(securities).fillna(0.0)
        forced_exit_weight = float(
            previous_all.loc[~previous_all.index.isin(securities)].sum()
        )
    else:
        previous = benchmark.copy()
        forced_exit_weight = 0.0
    cap_repair_weight = float((previous - settings.max_weight).clip(lower=0.0).sum())
    unavoidable_turnover_floor = forced_exit_weight + cap_repair_weight
    effective_turnover_limit = max(settings.max_turnover, unavoidable_turnover_floor)

    weights = cp.Variable(len(securities))
    covariance_array = cp.psd_wrap(sigma.to_numpy())
    active_weights = weights - benchmark.to_numpy()
    turnover_expression = 0.5 * (
        cp.norm1(weights - previous.to_numpy()) + forced_exit_weight
    )
    objective = cp.Maximize(
        mu.to_numpy() @ weights
        - 0.5 * settings.risk_aversion * cp.quad_form(active_weights, covariance_array)
        - settings.turnover_penalty * turnover_expression
    )
    restrictions: list[cp.Constraint] = [
        cp.sum(weights) == 1,
        weights >= 0,
        weights <= settings.max_weight,
        turnover_expression <= effective_turnover_limit,
    ]
    if settings.enforce_industry_constraints:
        for industry_name in sorted(industry.unique()):
            mask = (industry == industry_name).astype(float).to_numpy()
            benchmark_share = float(benchmark[industry == industry_name].sum())
            restrictions.extend(
                [
                    mask @ weights <= benchmark_share + settings.max_industry_deviation,
                    mask @ weights
                    >= max(0.0, benchmark_share - settings.max_industry_deviation),
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
        fallback = turnover_constrained_fallback(
            mu,
            previous,
            forced_exit_weight,
            settings.max_weight,
            effective_turnover_limit,
        )
        turnover = float(0.5 * ((fallback - previous).abs().sum() + forced_exit_weight))
        return OptimizationResult(
            fallback,
            status,
            None,
            turnover,
            used_fallback=True,
            forced_exit_weight=forced_exit_weight,
            unavoidable_turnover_floor=unavoidable_turnover_floor,
            turnover_limit=effective_turnover_limit,
        )

    optimized = pd.Series(np.maximum(weights.value, 0.0), index=securities)
    optimized = optimized / optimized.sum()
    turnover = float(0.5 * ((optimized - previous).abs().sum() + forced_exit_weight))
    return OptimizationResult(
        optimized,
        status,
        float(problem.value) if problem.value is not None else None,
        turnover,
        forced_exit_weight=forced_exit_weight,
        unavoidable_turnover_floor=unavoidable_turnover_floor,
        turnover_limit=effective_turnover_limit,
    )

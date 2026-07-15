import numpy as np
import pandas as pd

from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.portfolio.optimizer import PortfolioConstraints, optimize_portfolio
from pb_roe.portfolio.risk import ledoit_wolf_covariance, trailing_return_matrix
from pb_roe.portfolio.runner import _annualize_monthly_predictions, _ex_ante_snapshot


def test_ledoit_wolf_covariance_is_positive_semidefinite() -> None:
    bundle = fixture_bundle()
    securities = bundle.security_master["security_id"].tolist()
    returns = trailing_return_matrix(bundle.prices, securities, "2023-12-29", 252)

    covariance = ledoit_wolf_covariance(returns, minimum_observations=20)

    assert covariance.shape == (5, 5)
    assert np.linalg.eigvalsh(covariance.to_numpy()).min() >= -1e-10


def test_optimizer_respects_weight_industry_and_turnover_constraints() -> None:
    securities = [f"S{i}" for i in range(5)]
    expected = pd.Series([0.05, 0.04, 0.03, 0.02, 0.01], index=securities)
    covariance = pd.DataFrame(np.eye(5) * 0.04, index=securities, columns=securities)
    industries = pd.Series(["A", "A", "B", "B", "C"], index=securities)
    benchmark = pd.Series(0.2, index=securities)
    previous = benchmark.copy()
    settings = PortfolioConstraints(
        risk_aversion=1.0,
        turnover_penalty=0.001,
        max_weight=0.30,
        max_industry_deviation=0.10,
        max_turnover=0.30,
    )

    result = optimize_portfolio(
        expected, covariance, industries, benchmark, previous, constraints=settings
    )

    assert not result.used_fallback
    assert np.isclose(result.weights.sum(), 1.0)
    assert result.weights.min() >= -1e-10
    assert result.weights.max() <= 0.30 + 1e-6
    assert result.turnover <= 0.30 + 1e-6
    industry_weights = result.weights.groupby(industries).sum()
    benchmark_industry = benchmark.groupby(industries).sum()
    assert (industry_weights - benchmark_industry).abs().max() <= 0.10 + 1e-6


def test_monthly_predictions_are_annualized_for_annual_covariance() -> None:
    monthly = pd.Series([0.01, -0.02])

    annualized = _annualize_monthly_predictions(monthly)

    assert annualized.tolist() == [0.12, -0.24]


def test_ex_ante_snapshot_does_not_filter_on_future_returns() -> None:
    snapshot = pd.DataFrame(
        {
            "prediction": [0.1, 0.2, np.nan],
            "industry": ["A", "B", "C"],
            "forward_return": [np.nan, 0.03, 0.04],
        }
    )

    selected = _ex_ante_snapshot(snapshot)

    assert selected.index.tolist() == [0, 1]
    assert pd.isna(selected.loc[0, "forward_return"])


def test_zero_alpha_minimizes_active_risk_at_benchmark() -> None:
    securities = ["A", "B", "C"]
    benchmark = pd.Series([0.2, 0.3, 0.5], index=securities)
    covariance = pd.DataFrame(np.diag([0.01, 0.04, 0.09]), index=securities, columns=securities)
    settings = PortfolioConstraints(
        risk_aversion=10.0,
        turnover_penalty=0.0,
        max_weight=0.60,
        max_industry_deviation=1.0,
        max_turnover=1.0,
    )

    result = optimize_portfolio(
        pd.Series(0.0, index=securities),
        covariance,
        pd.Series("All", index=securities),
        benchmark_weights=benchmark,
        previous_weights=pd.Series(1 / 3, index=securities),
        constraints=settings,
    )

    assert np.allclose(result.weights, benchmark, atol=1e-5)

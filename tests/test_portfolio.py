import numpy as np
import pandas as pd

from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.portfolio.optimizer import PortfolioConstraints, optimize_portfolio
from pb_roe.portfolio.risk import ledoit_wolf_covariance, trailing_return_matrix


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

import numpy as np
import pandas as pd

from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.evaluation.exposures import mean_factor_correlation
from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.evaluation.panel import month_end_dates, next_open_forward_returns
from pb_roe.evaluation.performance import performance_metrics
from pb_roe.evaluation.preprocessing import neutralize_cross_section, winsorize_zscore
from pb_roe.evaluation.quantiles import long_short_spread, quantile_backtest


def test_month_end_and_next_open_return_timing() -> None:
    bundle = fixture_bundle()
    dates = month_end_dates(bundle.trading_calendar["trade_date"], "2022-01-01", "2022-03-31")

    returns = next_open_forward_returns(dates, bundle.prices)

    assert dates == [
        pd.Timestamp("2022-01-31"),
        pd.Timestamp("2022-02-28"),
        pd.Timestamp("2022-03-31"),
    ]
    assert returns["signal_date"].nunique() == 2
    assert (returns["entry_date"] > returns["signal_date"]).all()
    assert (returns["exit_date"] > returns["entry_date"]).all()


def test_winsorized_zscores_are_cross_sectionally_standardized() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": ["2022-01-31"] * 5,
            "factor": [1.0, 2.0, 3.0, 4.0, 100.0],
        }
    )

    result = winsorize_zscore(panel, ["factor"], lower=0.0, upper=0.8)

    assert np.isclose(result["factor_z"].mean(), 0.0)
    assert np.isclose(result["factor_z"].std(ddof=0), 1.0)
    assert result["factor_z"].max() < 2


def test_near_constant_factor_is_not_amplified() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": ["2022-01-31"] * 3,
            "factor": [1.0, 1.0 + 1e-15, 1.0 - 1e-15],
        }
    )

    result = winsorize_zscore(panel, ["factor"])

    assert result["factor_z"].eq(0).all()


def test_factor_correlation_ignores_months_with_missing_values() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": ["2022-01-31"] * 3 + ["2022-02-28"] * 3,
            "a": [np.nan] * 3 + [1.0, 2.0, 3.0],
            "b": [np.nan] * 3 + [3.0, 2.0, 1.0],
        }
    )

    correlation = mean_factor_correlation(panel, ["a", "b"])

    assert np.isclose(correlation.loc["a", "b"], -1.0)


def test_industry_neutralization_removes_industry_means() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": ["2022-01-31"] * 6,
            "industry": ["A", "A", "A", "B", "B", "B"],
            "factor": [1.0, 2.0, 3.0, 11.0, 12.0, 13.0],
        }
    )

    residuals = neutralize_cross_section(panel, "factor")

    assert np.allclose(residuals.groupby(panel["industry"]).mean(), 0.0, atol=1e-12)


def test_ic_and_newey_west_summary_identify_positive_signal() -> None:
    rows = []
    for month in range(1, 7):
        for security in range(5):
            rows.append(
                {
                    "signal_date": pd.Timestamp(2022, month, 28),
                    "factor": security,
                    "forward_return": security * 0.01 + month * 0.0001,
                }
            )
    panel = pd.DataFrame(rows)

    ic = calculate_ic(panel, ["factor"])
    summary = summarize_ic(ic)

    assert np.allclose(ic["ic"], 1.0)
    assert np.isclose(summary.iloc[0]["ic_mean"], 1.0)
    assert np.isnan(summary.iloc[0]["newey_west_t"])


def test_quantile_returns_turnover_cost_and_spread() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": ["2022-01-31"] * 4 + ["2022-02-28"] * 4,
            "security_id": ["A", "B", "C", "D"] * 2,
            "factor": [1, 2, 3, 4] * 2,
            "forward_return": [0.01, 0.02, 0.03, 0.04, 0.02, 0.03, 0.04, 0.05],
        }
    )

    quantiles = quantile_backtest(panel, "factor", quantiles=2, cost_rate=0.001)
    spreads = long_short_spread(quantiles)

    assert quantiles.groupby("signal_date")["quantile"].nunique().eq(2).all()
    assert (
        quantiles.loc[quantiles["signal_date"] == pd.Timestamp("2022-01-31"), "turnover"]
        .eq(1)
        .all()
    )
    assert (
        quantiles.loc[quantiles["signal_date"] == pd.Timestamp("2022-02-28"), "turnover"]
        .eq(0)
        .all()
    )
    assert np.allclose(spreads["gross_spread"], 0.02)


def test_performance_metrics_capture_drawdown() -> None:
    metrics = performance_metrics(pd.Series([0.10, -0.20, 0.05]), periods_per_year=12)

    assert metrics["max_drawdown"] < 0
    assert np.isfinite(metrics["annual_volatility"])

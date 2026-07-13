import pandas as pd
import pytest

from pb_roe.factors.validation import _factor_metrics, _passes_minimum


def test_factor_metrics_reports_costs_and_monotonicity() -> None:
    rows = []
    for month in pd.date_range("2020-01-31", periods=6, freq="ME"):
        for rank in range(10):
            rows.append(
                {
                    "signal_date": month,
                    "security_id": f"S{rank:02d}",
                    "test_z": float(rank),
                    "target_return": rank / 100,
                    "industry": "A" if rank < 5 else "B",
                    "adv_20d": 1_000_000 + rank,
                }
            )
    panel = pd.DataFrame(rows)

    metrics, quantiles = _factor_metrics(panel, "test_z", "Value", 1, [0.001, 0.003, 0.005], 5)

    assert metrics["quantile_monotonicity_30bp"] == pytest.approx(1.0)
    assert {10, 30, 50} == set(quantiles["cost_bps"])
    assert "long_short_annual_return_30bp" in metrics


def test_spearman_boundary_is_numerically_stable() -> None:
    assert _passes_minimum(0.7999999999999999, 0.8)
    assert not _passes_minimum(0.79, 0.8)

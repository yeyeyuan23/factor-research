import pandas as pd
import pytest

from pb_roe.factors.eligibility import build_model_factor_eligibility
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


def test_model_eligibility_excludes_derived_and_redundant_features() -> None:
    rows = []
    for month in pd.date_range("2020-01-31", periods=12, freq="ME"):
        for rank in range(30):
            rows.append(
                {
                    "signal_date": month,
                    "security_id": f"S{rank:02d}",
                    "bp_z": float(rank),
                    "reversal_1m_z": float(rank),
                    "roe_z": float((rank * 7) % 30),
                    "paper_score_z": float(rank),
                    "target_return": rank / 100 + month.month / 10_000,
                }
            )
    panel = pd.DataFrame(rows)
    candidates = {
        "bp": {"category": "Value", "direction": 1},
        "paper_score": {"category": "Value", "direction": 1},
        "roe": {"category": "Quality", "direction": 1},
        "reversal_1m": {"category": "Momentum", "direction": 1},
    }
    settings = {
        "minimum_valid_months": 6,
        "minimum_monthly_coverage": 0.8,
        "minimum_coverage_pass_rate": 0.9,
        "minimum_median_stock_count": 20,
        "minimum_unique_values": 20,
        "significantly_opposite_t": -2.0,
        "maximum_absolute_correlation": 0.85,
        "exclude_derived_features": ["paper_score_z"],
        "representative_priority": ["bp_z", "roe_z", "reversal_1m_z"],
    }

    eligibility, correlations, eligible = build_model_factor_eligibility(
        panel,
        candidates,
        ["bp_z", "paper_score_z", "roe_z", "reversal_1m_z"],
        settings,
    )

    indexed = eligibility.set_index("feature")
    assert eligible == ["bp_z", "roe_z"]
    assert indexed.loc["paper_score_z", "failed_checks"] == "primitive"
    assert indexed.loc["reversal_1m_z", "failed_checks"] == "redundancy"
    assert correlations.loc["bp_z", "reversal_1m_z"] == pytest.approx(1.0)

import pandas as pd
import pytest

from pb_roe.factors.eligibility import build_model_factor_eligibility
from pb_roe.factors.incremental import build_pb_roe_incremental_analysis
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


def test_incremental_analysis_links_extensions_to_pb_roe_baseline() -> None:
    rows = []
    for month in pd.date_range("2018-01-31", periods=24, freq="ME"):
        for rank in range(30):
            bp = (rank - 15) / 10
            roe = ((rank * 7) % 30 - 15) / 10
            good = ((rank * 11 + month.month) % 30 - 15) / 10
            baseline = bp + roe
            rows.append(
                {
                    "signal_date": month,
                    "security_id": f"S{rank:02d}",
                    "bp_z": bp,
                    "roe_z": roe,
                    "paper_score_z": baseline,
                    "good_z": good,
                    "bad_z": -good,
                    "target_return": baseline / 100 + good / 30,
                }
            )
    panel = pd.DataFrame(rows)
    candidates = {
        "bp": {"category": "Value", "direction": 1},
        "paper_score": {"category": "Value", "direction": 1},
        "roe": {"category": "Quality", "direction": 1},
        "good": {"category": "Momentum", "direction": 1},
        "bad": {"category": "Momentum", "direction": 1},
    }
    settings = {
        "baseline_feature": "paper_score_z",
        "core_features": ["bp_z", "roe_z"],
        "candidate_weight": 1 / 3,
        "cost_rate": 0.003,
        "maximum_baseline_correlation": 0.85,
        "minimum_residual_ic": 0.0,
        "minimum_add_one_delta_ic": 0.0,
        "minimum_improvement_year_rate": 0.5,
    }

    summary, timeseries = build_pb_roe_incremental_analysis(
        panel,
        candidates,
        list(panel.columns),
        settings,
        quantiles=5,
    )

    indexed = summary.set_index("feature")
    assert bool(indexed.loc["good_z", "incremental_pass"])
    assert indexed.loc["good_z", "residual_ic_mean"] > 0
    assert indexed.loc["good_z", "add_one_delta_ic"] > 0
    assert not bool(indexed.loc["bad_z", "incremental_pass"])
    assert set(timeseries["feature"]) == {"good_z", "bad_z"}


def test_model_eligibility_requires_incremental_pass_for_extensions() -> None:
    rows = []
    for month in pd.date_range("2020-01-31", periods=12, freq="ME"):
        for rank in range(30):
            rows.append(
                {
                    "signal_date": month,
                    "security_id": f"S{rank:02d}",
                    "bp_z": float(rank),
                    "roe_z": float((rank * 7) % 30),
                    "extension_z": float((rank * 11) % 30),
                    "target_return": rank / 100,
                }
            )
    panel = pd.DataFrame(rows)
    candidates = {
        "bp": {"category": "Value", "direction": 1},
        "roe": {"category": "Quality", "direction": 1},
        "extension": {"category": "Momentum", "direction": 1},
    }
    settings = {
        "minimum_valid_months": 6,
        "minimum_monthly_coverage": 0.8,
        "minimum_coverage_pass_rate": 0.9,
        "minimum_median_stock_count": 20,
        "minimum_unique_values": 20,
        "significantly_opposite_t": -2.0,
        "maximum_absolute_correlation": 1.01,
        "core_features": ["bp_z", "roe_z"],
        "require_incremental_pass": True,
        "exclude_derived_features": [],
        "representative_priority": ["bp_z", "roe_z", "extension_z"],
    }
    incremental = pd.DataFrame(
        {
            "feature": ["extension_z"],
            "incremental_pass": [False],
            "failed_incremental_checks": ["add_one_ic"],
            "residual_ic_mean": [0.02],
            "add_one_delta_ic": [-0.01],
            "add_one_improvement_year_rate": [0.25],
        }
    )

    eligibility, _, eligible = build_model_factor_eligibility(
        panel,
        candidates,
        ["bp_z", "roe_z", "extension_z"],
        settings,
        incremental,
    )

    indexed = eligibility.set_index("feature")
    assert eligible == ["bp_z", "roe_z"]
    assert indexed.loc["extension_z", "failed_pre_redundancy_checks"] == "incremental"
    assert indexed.loc["extension_z", "failed_incremental_checks"] == "add_one_ic"

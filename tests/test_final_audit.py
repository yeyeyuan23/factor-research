import json

import pandas as pd

from pb_roe.config import load_config
from pb_roe.validation.final_audit import (
    REQUIRED_OUTPUTS,
    _model_feature_alignment_check,
    _model_feature_manifest_check,
    _paper_window_check,
    _prediction_time_check,
    audit_frozen_run,
)


def test_final_audit_detects_time_leakage_and_missing_outputs(tmp_path) -> None:
    config = load_config("configs/smoke.yaml")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    report = audit_frozen_run(run_dir, config)

    assert not report["passed"]
    failed = {check["check_id"] for check in report["checks"] if not check["passed"]}
    assert "outputs.required_files" in failed
    assert "models.lightgbm.no_leakage" in failed


def test_final_audit_accepts_complete_consistent_run(tmp_path) -> None:
    config = load_config("configs/smoke.yaml")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    for name in REQUIRED_OUTPUTS:
        path = run_dir / name
        if name.endswith(".json"):
            payload = (
                {
                    "passed": True,
                    "checks": [],
                    "config_fingerprint": config.fingerprint,
                }
                if name == "data_audit.json"
                else {}
            )
            path.write_text(json.dumps(payload), encoding="utf-8")
        elif name.endswith(".csv"):
            pd.DataFrame({"value": [1]}).to_csv(path, index=False)
        elif name.endswith(".html"):
            path.write_text("<h1>PB-ROE Alpha Research</h1>", encoding="utf-8")
    prediction = pd.DataFrame(
        {
            "signal_date": ["2023-03-31"],
            "training_end": ["2023-01-31"],
            "training_label_exit_end": ["2023-03-01"],
            "validation_start": ["2023-02-01"],
            "validation_end": ["2023-02-28"],
            "validation_label_exit_end": ["2023-03-01"],
        }
    )
    prediction[["signal_date", "training_end", "training_label_exit_end"]].to_parquet(
        run_dir / "elastic-net_predictions.parquet", index=False
    )
    prediction.to_parquet(run_dir / "lightgbm_predictions.parquet", index=False)
    pd.DataFrame(
        {
            "signal_date": ["2023-03-31"] * 5,
            "target_weight": [0.2] * 5,
        }
    ).to_parquet(run_dir / "optimized_holdings.parquet", index=False)
    pd.DataFrame({"turnover": [0.1]}).to_csv(run_dir / "optimized_returns.csv", index=False)
    pd.DataFrame({"value": [1]}).to_parquet(run_dir / "paper_returns.parquet", index=False)

    report = audit_frozen_run(run_dir, config)

    assert report["passed"]
    assert len(report["manifest"]) == len(REQUIRED_OUTPUTS)


def test_prediction_audit_rejects_unmatured_forward_return_label(tmp_path) -> None:
    pd.DataFrame(
        {
            "signal_date": ["2023-01-31"],
            "training_end": ["2022-12-30"],
            "training_label_exit_end": ["2023-02-01"],
        }
    ).to_parquet(tmp_path / "elastic-net_predictions.parquet", index=False)

    check = _prediction_time_check(tmp_path, "elastic-net")

    assert not check.passed
    assert "0/1" in check.details


def test_formal_audit_requires_full_18_period_paper_window(tmp_path) -> None:
    config = load_config("configs/modern.yaml")
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    dates = pd.date_range("2005-05-09", periods=18, freq="120D")
    pd.DataFrame(
        {
            "rebalance_date": dates,
            "period_end": [*dates[1:17], pd.Timestamp("2011-03-25"), pd.Timestamp("2011-03-25")],
        }
    ).to_parquet(paper_dir / "paper_returns.parquet", index=False)

    check = _paper_window_check(paper_dir, config)

    assert check.passed


def test_formal_audit_rejects_truncated_paper_window(tmp_path) -> None:
    config = load_config("configs/modern.yaml")
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    dates = pd.date_range("2007-04-30", periods=12, freq="120D")
    pd.DataFrame(
        {
            "rebalance_date": dates,
            "period_end": [*dates[1:], pd.Timestamp("2011-03-25")],
        }
    ).to_parquet(paper_dir / "paper_returns.parquet", index=False)

    check = _paper_window_check(paper_dir, config)

    assert not check.passed
    assert "periods=12" in check.details


def test_formal_model_manifest_rejects_derived_duplicate(tmp_path) -> None:
    config = load_config("configs/modern.yaml")
    (tmp_path / "data_audit.json").write_text(
        json.dumps({"input_manifest_sha256": "a" * 64}), encoding="utf-8"
    )
    (tmp_path / "model_feature_manifest.json").write_text(
        json.dumps(
            {
                "config_fingerprint": config.fingerprint,
                "canonical_input_manifest_sha256": "a" * 64,
                "eligible_features": ["bp_z", "roe_z", "paper_score_z"],
                "strict_standalone_features": ["bp_z"],
                "evaluation_status": "exploratory_after_prior_oos_review",
            }
        ),
        encoding="utf-8",
    )

    check = _model_feature_manifest_check(tmp_path, config)

    assert not check.passed
    assert "derived_duplicate=True" in check.details


def test_formal_models_must_use_identical_manifest_features(tmp_path) -> None:
    config = load_config("configs/modern.yaml")
    manifest = {"eligible_features": ["bp_z", "roe_z"]}
    (tmp_path / "model_feature_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "elastic-net_run.json").write_text(
        json.dumps({"features": ["bp_z", "roe_z"]}), encoding="utf-8"
    )
    (tmp_path / "lightgbm_run.json").write_text(
        json.dumps({"features": ["bp_z"]}), encoding="utf-8"
    )

    check = _model_feature_alignment_check(tmp_path, config)

    assert not check.passed
    assert "lightgbm=['bp_z']" in check.details

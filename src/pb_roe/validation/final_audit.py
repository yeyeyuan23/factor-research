"""Machine-readable final audit for frozen research outputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pb_roe.config import ResearchConfig, load_config

REQUIRED_OUTPUTS = (
    "data_audit.json",
    "paper_run.json",
    "paper_returns.parquet",
    "evaluation_run.json",
    "ic_summary.csv",
    "elastic-net_predictions.parquet",
    "lightgbm_predictions.parquet",
    "optimized_holdings.parquet",
    "optimized_returns.csv",
    "optimization_diagnostics.csv",
    "dashboard.html",
)


@dataclass(frozen=True)
class FinalCheck:
    check_id: str
    passed: bool
    severity: str
    details: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_files(run_dir: Path, paper_dir: Path) -> FinalCheck:
    if (run_dir / "elastic-net_optimized_holdings.parquet").is_file():
        required = [
            "data_audit.json",
            "evaluation_run.json",
            "ic_summary.csv",
            "frozen_factor_selection.json",
            "model_factor_eligibility.csv",
            "model_feature_manifest.json",
            "strict_factor_equal_weight_predictions.parquet",
            "model_input_equal_weight_predictions.parquet",
            "dashboard.html",
            "elastic-net_predictions.parquet",
            "lightgbm_predictions.parquet",
            "elastic-net_optimized_holdings.parquet",
            "elastic-net_optimized_returns.csv",
            "elastic-net_optimization_diagnostics.csv",
            "lightgbm_optimized_holdings.parquet",
            "lightgbm_optimized_returns.csv",
            "lightgbm_optimization_diagnostics.csv",
            "strict_factor_equal_weight_optimized_holdings.parquet",
            "strict_factor_equal_weight_optimized_returns.csv",
            "model_input_equal_weight_optimized_holdings.parquet",
            "model_input_equal_weight_optimized_returns.csv",
        ]
    else:
        required = [name for name in REQUIRED_OUTPUTS if not name.startswith("paper_")]
    missing = [name for name in required if not (run_dir / name).is_file()]
    missing.extend(
        f"paper:{name}"
        for name in ("paper_run.json", "paper_returns.parquet")
        if not (paper_dir / name).is_file()
    )
    return FinalCheck(
        "outputs.required_files",
        not missing,
        "error",
        "complete" if not missing else f"missing: {', '.join(missing)}",
    )


def _data_audit(run_dir: Path, config: ResearchConfig) -> FinalCheck:
    path = run_dir / "data_audit.json"
    if not path.is_file():
        return FinalCheck("data.audit_passed", False, "error", "data_audit.json missing")
    report = json.loads(path.read_text(encoding="utf-8"))
    providers = config.section("data").get("providers", {})
    fixture = all(value == "fixture" for value in providers.values())
    checks = {item.get("check_id"): item for item in report.get("checks", [])}
    expected_lag = config.section("quality").get("maximum_roe_announcement_lag_days")
    valid = bool(report.get("passed")) and report.get("config_fingerprint") == config.fingerprint
    details = [f"{len(checks)} checks", "config fingerprint matched"]
    if expected_lag is not None:
        lag_check = checks.get("fundamentals.roe_announcement_lag")
        valid &= bool(lag_check and lag_check.get("passed"))
        details.append("ROE announcement-lag gate present")
    if not fixture:
        manifest_hash = str(report.get("input_manifest_sha256", ""))
        valid &= len(manifest_hash) == 64 and bool(report.get("input_manifest"))
        details.append("canonical input manifest frozen")
    return FinalCheck(
        "data.audit_passed",
        bool(valid),
        "error",
        "; ".join(details),
    )


def _causal_industry_check(config: ResearchConfig) -> FinalCheck:
    providers = config.section("data").get("providers", {})
    fixture = all(value == "fixture" for value in providers.values())
    if config.mode != "modern" or fixture:
        return FinalCheck("research.static_industry_not_causal", True, "info", "not applicable")
    evaluation = config.section("evaluation")
    portfolio = config.section("portfolio")
    target = str(evaluation.get("target_neutralization", "industry"))
    constraints = bool(portfolio.get("enforce_industry_constraints", True))
    valid = target == "none" and not constraints
    return FinalCheck(
        "research.static_industry_not_causal",
        valid,
        "error",
        f"target_neutralization={target}, industry_constraints={constraints}",
    )


def _paper_exit_mark_check(paper_dir: Path, config: ResearchConfig) -> FinalCheck:
    if config.mode != "modern":
        return FinalCheck("paper.observable_exit_marks", True, "info", "not applicable")
    path = paper_dir / "paper_returns.parquet"
    if not path.is_file():
        return FinalCheck("paper.observable_exit_marks", False, "error", "returns missing")
    frame = pd.read_parquet(path)
    required = {"stale_exit_count", "maximum_exit_staleness_days"}
    missing = sorted(required - set(frame.columns))
    return FinalCheck(
        "paper.observable_exit_marks",
        not missing,
        "error",
        "last observable close retained" if not missing else f"missing columns: {missing}",
    )


def _paper_window_check(paper_dir: Path, config: ResearchConfig) -> FinalCheck:
    """Require the formal modern audit to reference the full 18-period paper run."""
    if config.mode != "modern":
        return FinalCheck("paper.full_reproduction_window", True, "info", "not applicable")
    path = paper_dir / "paper_returns.parquet"
    if not path.is_file():
        return FinalCheck(
            "paper.full_reproduction_window", False, "error", "paper_returns.parquet missing"
        )
    frame = pd.read_parquet(path)
    required = {"rebalance_date", "period_end"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        return FinalCheck(
            "paper.full_reproduction_window",
            False,
            "error",
            f"missing columns: {', '.join(missing)}",
        )
    rebalance = pd.to_datetime(frame["rebalance_date"], errors="coerce")
    period_end = pd.to_datetime(frame["period_end"], errors="coerce")
    periods = int(rebalance.nunique())
    start = rebalance.min()
    end = period_end.max()
    valid = (
        periods == 18
        and pd.notna(start)
        and pd.notna(end)
        and start.year == 2005
        and end.normalize() == pd.Timestamp("2011-03-25")
    )
    details = (
        f"periods={periods}, first_rebalance={start.date() if pd.notna(start) else 'missing'}, "
        f"last_period_end={end.date() if pd.notna(end) else 'missing'}"
    )
    return FinalCheck("paper.full_reproduction_window", bool(valid), "error", details)


def _prediction_time_check(run_dir: Path, model: str) -> FinalCheck:
    path = run_dir / f"{model}_predictions.parquet"
    if not path.is_file():
        return FinalCheck(f"models.{model}.no_leakage", False, "error", "predictions missing")
    frame = pd.read_parquet(path)
    required_label_columns = {"training_label_exit_end"}
    if "validation_end" in frame:
        required_label_columns.add("validation_label_exit_end")
    missing = sorted(required_label_columns - set(frame))
    if missing:
        return FinalCheck(
            f"models.{model}.no_leakage",
            False,
            "error",
            f"strict label-availability columns missing: {missing}",
        )
    valid = pd.to_datetime(frame["training_end"]) < pd.to_datetime(frame["signal_date"])
    valid &= pd.to_datetime(frame["training_label_exit_end"]) <= pd.to_datetime(
        frame["signal_date"]
    )
    if "validation_end" in frame:
        valid &= pd.to_datetime(frame["validation_end"]) < pd.to_datetime(frame["signal_date"])
        valid &= pd.to_datetime(frame["training_end"]) < pd.to_datetime(frame["validation_start"])
        valid &= pd.to_datetime(frame["validation_label_exit_end"]) <= pd.to_datetime(
            frame["signal_date"]
        )
    return FinalCheck(
        f"models.{model}.no_leakage",
        bool(valid.all()),
        "error",
        f"{int(valid.sum())}/{len(valid)} predictions respect signal and label availability",
    )


def _model_feature_manifest_check(run_dir: Path, config: ResearchConfig) -> FinalCheck:
    providers = config.section("data").get("providers", {})
    fixture = all(value == "fixture" for value in providers.values())
    if config.mode != "modern" or fixture:
        return FinalCheck("models.feature_manifest", True, "info", "not applicable")
    path = run_dir / "model_feature_manifest.json"
    if not path.is_file():
        return FinalCheck("models.feature_manifest", False, "error", "manifest missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = list(payload.get("eligible_features", []))
    strict = list(payload.get("strict_standalone_features", []))
    audit_path = run_dir / "data_audit.json"
    data_audit = (
        json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    )
    derived_duplicate = "paper_score_z" in features and {"bp_z", "roe_z"} <= set(features)
    valid = (
        payload.get("config_fingerprint") == config.fingerprint
        and bool(features)
        and set(strict) <= set(features)
        and not derived_duplicate
        and payload.get("canonical_input_manifest_sha256")
        == data_audit.get("input_manifest_sha256")
        and payload.get("evaluation_status") == "exploratory_after_prior_oos_review"
    )
    return FinalCheck(
        "models.feature_manifest",
        bool(valid),
        "error",
        f"features={features}; strict={strict}; derived_duplicate={derived_duplicate}; "
        f"status={payload.get('evaluation_status')}",
    )


def _model_feature_alignment_check(run_dir: Path, config: ResearchConfig) -> FinalCheck:
    providers = config.section("data").get("providers", {})
    fixture = all(value == "fixture" for value in providers.values())
    if config.mode != "modern" or fixture:
        return FinalCheck("models.same_feature_inputs", True, "info", "not applicable")
    manifest_path = run_dir / "model_feature_manifest.json"
    run_paths = [run_dir / "elastic-net_run.json", run_dir / "lightgbm_run.json"]
    if not manifest_path.is_file() or not all(path.is_file() for path in run_paths):
        return FinalCheck(
            "models.same_feature_inputs", False, "error", "manifest or model run metadata missing"
        )
    expected = list(json.loads(manifest_path.read_text(encoding="utf-8"))["eligible_features"])
    observed = [
        list(json.loads(path.read_text(encoding="utf-8")).get("features", []))
        for path in run_paths
    ]
    valid = all(features == expected for features in observed)
    return FinalCheck(
        "models.same_feature_inputs",
        bool(valid),
        "error",
        f"manifest={expected}; elastic_net={observed[0]}; lightgbm={observed[1]}",
    )


def _portfolio_check(run_dir: Path, config: ResearchConfig, model: str = "") -> list[FinalCheck]:
    prefix = f"{model}_" if model else ""
    check_prefix = f"portfolio.{model or 'legacy'}"
    path = run_dir / f"{prefix}optimized_holdings.parquet"
    if not path.is_file():
        return [FinalCheck(f"{check_prefix}.weights", False, "error", "holdings missing")]
    holdings = pd.read_parquet(path)
    weight_sums = holdings.groupby("signal_date")["target_weight"].sum()
    max_weight = float(config.section("portfolio")["max_weight"])
    checks = [
        FinalCheck(
            f"{check_prefix}.fully_invested",
            bool(np.allclose(weight_sums, 1.0, atol=1e-6)),
            "error",
            f"max weight-sum deviation={float((weight_sums - 1).abs().max()):.3g}",
        ),
        FinalCheck(
            f"{check_prefix}.long_only",
            bool(holdings["target_weight"].min() >= -1e-8),
            "error",
            f"minimum weight={holdings['target_weight'].min():.6g}",
        ),
        FinalCheck(
            f"{check_prefix}.single_name_limit",
            bool(holdings["target_weight"].max() <= max_weight + 1e-6),
            "error",
            f"maximum weight={holdings['target_weight'].max():.6g}, limit={max_weight}",
        ),
    ]
    returns_path = run_dir / f"{prefix}optimized_returns.csv"
    if returns_path.is_file():
        returns = pd.read_csv(returns_path)
        max_turnover = float(config.section("portfolio")["max_turnover"])
        checks.append(
            FinalCheck(
                f"{check_prefix}.turnover_limit",
                bool(returns["turnover"].max() <= max_turnover + 1e-6),
                "error",
                f"maximum turnover={returns['turnover'].max():.6g}, limit={max_turnover}",
            )
        )
    return checks


def _dashboard_check(run_dir: Path) -> FinalCheck:
    path = run_dir / "dashboard.html"
    if not path.is_file():
        return FinalCheck("report.offline", False, "error", "dashboard missing")
    content = path.read_text(encoding="utf-8")
    external = 'src="https://cdn.plot.ly' in content or "src='https://cdn.plot.ly" in content
    return FinalCheck(
        "report.offline",
        not external and "PB-ROE Alpha Research" in content,
        "error",
        f"size={path.stat().st_size} bytes, external_plotly={external}",
    )


def _sample_split_check(config: ResearchConfig) -> FinalCheck:
    research = config.section("research")
    if not {"development_end", "oos_start", "end_date"} <= set(research):
        return FinalCheck("research.time_windows", True, "info", "not applicable to smoke/paper")
    development_end = pd.Timestamp(research["development_end"])
    oos_start = pd.Timestamp(research["oos_start"])
    end = pd.Timestamp(research["end_date"])
    valid = development_end < oos_start <= end
    model_status = str(config.section("models").get("evidence_status", ""))
    if config.mode == "modern":
        valid &= model_status == "exploratory_after_prior_oos_review"
    return FinalCheck(
        "research.time_windows",
        bool(valid),
        "error",
        f"development_end={development_end.date()}, historical_evaluation="
        f"{oos_start.date()}..{end.date()}, model_status={model_status}",
    )


def audit_frozen_run(
    run_dir: str | Path,
    config: ResearchConfig,
    paper_run_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(run_dir).expanduser().resolve()
    paper_root = Path(paper_run_dir).expanduser().resolve() if paper_run_dir else root
    portfolio_models = (
        [
            "strict_factor_equal_weight",
            "model_input_equal_weight",
            "elastic-net",
            "lightgbm",
        ]
        if (root / "elastic-net_optimized_holdings.parquet").is_file()
        else [""]
    )
    checks = [
        _required_files(root, paper_root),
        _data_audit(root, config),
        _paper_window_check(paper_root, config),
        _paper_exit_mark_check(paper_root, config),
        _causal_industry_check(config),
        _model_feature_manifest_check(root, config),
        _model_feature_alignment_check(root, config),
        _prediction_time_check(root, "elastic-net"),
        _prediction_time_check(root, "lightgbm"),
        *[check for model in portfolio_models for check in _portfolio_check(root, config, model)],
        _dashboard_check(root),
        _sample_split_check(config),
    ]
    passed = all(check.passed for check in checks if check.severity == "error")
    manifest = {
        path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in sorted(root.iterdir())
        if path.is_file() and path.name not in {"final_audit.json", "result_manifest.json"}
    }
    if paper_root != root:
        manifest.update(
            {
                f"paper/{path.name}": {"sha256": _sha256(path), "bytes": path.stat().st_size}
                for path in sorted(paper_root.iterdir())
                if path.is_file()
            }
        )
    return {
        "run_id": config.run_id,
        "config_fingerprint": config.fingerprint,
        "passed": passed,
        "checks": [asdict(check) for check in checks],
        "manifest": manifest,
    }


def final_audit_from_cli(
    config_path: str, run_dir: str | None, paper_run_dir: str | None = None
) -> int:
    config = load_config(config_path)
    root = Path(run_dir).resolve() if run_dir else config.output_dir()
    report = audit_frozen_run(root, config, paper_run_dir)
    (root / "final_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "result_manifest.json").write_text(
        json.dumps(report["manifest"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = {
        "run_id": config.run_id,
        "passed": report["passed"],
        "checks": len(report["checks"]),
        "manifest_files": len(report["manifest"]),
        "output": str(root / "final_audit.json"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1

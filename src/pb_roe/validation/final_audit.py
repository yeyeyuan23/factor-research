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


def _required_files(run_dir: Path) -> FinalCheck:
    missing = [name for name in REQUIRED_OUTPUTS if not (run_dir / name).is_file()]
    return FinalCheck(
        "outputs.required_files",
        not missing,
        "error",
        "complete" if not missing else f"missing: {', '.join(missing)}",
    )


def _data_audit(run_dir: Path) -> FinalCheck:
    path = run_dir / "data_audit.json"
    if not path.is_file():
        return FinalCheck("data.audit_passed", False, "error", "data_audit.json missing")
    report = json.loads(path.read_text(encoding="utf-8"))
    return FinalCheck(
        "data.audit_passed",
        bool(report.get("passed")),
        "error",
        f"{len(report.get('checks', []))} checks",
    )


def _prediction_time_check(run_dir: Path, model: str) -> FinalCheck:
    path = run_dir / f"{model}_predictions.parquet"
    if not path.is_file():
        return FinalCheck(f"models.{model}.no_leakage", False, "error", "predictions missing")
    frame = pd.read_parquet(path)
    valid = pd.to_datetime(frame["training_end"]) < pd.to_datetime(frame["signal_date"])
    if "validation_end" in frame:
        valid &= pd.to_datetime(frame["validation_end"]) < pd.to_datetime(frame["signal_date"])
        valid &= pd.to_datetime(frame["training_end"]) < pd.to_datetime(frame["validation_start"])
    return FinalCheck(
        f"models.{model}.no_leakage",
        bool(valid.all()),
        "error",
        f"{int(valid.sum())}/{len(valid)} predictions respect time order",
    )


def _portfolio_check(run_dir: Path, config: ResearchConfig) -> list[FinalCheck]:
    path = run_dir / "optimized_holdings.parquet"
    if not path.is_file():
        return [FinalCheck("portfolio.weights", False, "error", "holdings missing")]
    holdings = pd.read_parquet(path)
    weight_sums = holdings.groupby("signal_date")["target_weight"].sum()
    max_weight = float(config.section("portfolio")["max_weight"])
    checks = [
        FinalCheck(
            "portfolio.fully_invested",
            bool(np.allclose(weight_sums, 1.0, atol=1e-6)),
            "error",
            f"max weight-sum deviation={float((weight_sums - 1).abs().max()):.3g}",
        ),
        FinalCheck(
            "portfolio.long_only",
            bool(holdings["target_weight"].min() >= -1e-8),
            "error",
            f"minimum weight={holdings['target_weight'].min():.6g}",
        ),
        FinalCheck(
            "portfolio.single_name_limit",
            bool(holdings["target_weight"].max() <= max_weight + 1e-6),
            "error",
            f"maximum weight={holdings['target_weight'].max():.6g}, limit={max_weight}",
        ),
    ]
    returns_path = run_dir / "optimized_returns.csv"
    if returns_path.is_file():
        returns = pd.read_csv(returns_path)
        max_turnover = float(config.section("portfolio")["max_turnover"])
        checks.append(
            FinalCheck(
                "portfolio.turnover_limit",
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
        return FinalCheck("research.frozen_oos", True, "info", "not applicable to smoke/paper")
    development_end = pd.Timestamp(research["development_end"])
    oos_start = pd.Timestamp(research["oos_start"])
    end = pd.Timestamp(research["end_date"])
    valid = development_end < oos_start <= end
    return FinalCheck(
        "research.frozen_oos",
        bool(valid),
        "error",
        f"development_end={development_end.date()}, oos={oos_start.date()}..{end.date()}",
    )


def audit_frozen_run(run_dir: str | Path, config: ResearchConfig) -> dict[str, Any]:
    root = Path(run_dir).expanduser().resolve()
    checks = [
        _required_files(root),
        _data_audit(root),
        _prediction_time_check(root, "elastic-net"),
        _prediction_time_check(root, "lightgbm"),
        *_portfolio_check(root, config),
        _dashboard_check(root),
        _sample_split_check(config),
    ]
    passed = all(check.passed for check in checks if check.severity == "error")
    manifest = {
        path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in sorted(root.iterdir())
        if path.is_file() and path.name not in {"final_audit.json", "result_manifest.json"}
    }
    return {
        "run_id": config.run_id,
        "config_fingerprint": config.fingerprint,
        "passed": passed,
        "checks": [asdict(check) for check in checks],
        "manifest": manifest,
    }


def final_audit_from_cli(config_path: str, run_dir: str | None) -> int:
    config = load_config(config_path)
    root = Path(run_dir).resolve() if run_dir else config.output_dir()
    report = audit_frozen_run(root, config)
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

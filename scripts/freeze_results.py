#!/usr/bin/env python3
"""Freeze formal machine outputs into the tracked documentation summaries."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

PAPER_NAMES = {
    "R0_UNIVERSE_EW": "CSI300_equal_weight",
    "R1_ROE_TOP20": "ROE20",
    "R2_PB_RANK50_100": "PB50_100",
    "R3_PB_ROE_TOP50": "PB_ROE50",
    "R4_PB_ROE_INDUSTRY_EW": "PB_ROE_industry_equal_weight",
    "R4_PB_ROE_INDUSTRY_BENCHMARK_WEIGHT": "PB_ROE_industry_benchmark_weight",
}
ORIGINAL_PAPER = {
    "ROE20": (6.0511, 4.6109, 0.3393, 14, 14 / 18),
    "PB50_100": (6.0345, 4.5977, 0.3387, 11, 11 / 18),
    "PB_ROE50": (6.3917, 4.8820, 0.3500, 13, 13 / 18),
    "PB_ROE_industry_equal_weight": (6.8785, 5.2693, 0.3647, 13, 13 / 18),
    "PB_ROE_industry_benchmark_weight": (6.0870, 4.6395, 0.3404, 13, 13 / 18),
}
FACTOR_NAMES = {
    "bp_z": ("BP", "raw"),
    "bp_z_industry_neutral": ("BP", "industry_adjusted"),
    "roe_z": ("ROE_TTM", "raw"),
    "roe_z_industry_neutral": ("ROE_TTM", "industry_adjusted"),
    "paper_score_z": ("PB_ROE", "raw"),
    "paper_score_z_industry_neutral": ("PB_ROE", "industry_adjusted"),
}


def freeze_paper(paper_dir: Path, output: Path) -> None:
    summary = pd.read_csv(paper_dir / "paper_summary.csv")
    reproduced = summary[summary["strategy_id"].isin(PAPER_NAMES)].copy()
    reproduced["strategy"] = reproduced["strategy_id"].map(PAPER_NAMES)
    reproduced["source"] = "reproduction"
    columns = [
        "strategy",
        "source",
        "periods",
        "cumulative_gross_return",
        "cumulative_net_return",
        "annualized_net_return",
        "benchmark_win_count",
        "benchmark_win_rate",
    ]
    rows = [reproduced[columns]]
    original_rows = []
    for strategy, values in ORIGINAL_PAPER.items():
        gross, net, annual, wins, win_rate = values
        original_rows.append(
            {
                "strategy": strategy,
                "source": "original_paper",
                "periods": 18,
                "cumulative_gross_return": gross,
                "cumulative_net_return": net,
                "annualized_net_return": annual,
                "benchmark_win_count": wins,
                "benchmark_win_rate": win_rate,
            }
        )
    rows.append(pd.DataFrame(original_rows))
    pd.concat(rows, ignore_index=True)[columns].to_csv(
        output / "paper_reproduction_full.csv", index=False
    )


def freeze_factor_validation(run_dir: Path, output: Path) -> None:
    validation = pd.read_csv(run_dir / "factor_validation.csv")
    columns = {
        "ic_mean": "development_ic_mean",
        "icir": "development_icir",
        "ic_positive_rate": "development_ic_positive_rate",
        "newey_west_t": "development_newey_west_t",
    }
    validation = validation.rename(columns=columns)
    retained = [
        "factor",
        "category",
        "direction",
        "minimum_monthly_coverage",
        "development_ic_mean",
        "development_icir",
        "development_ic_positive_rate",
        "development_newey_west_t",
        "year_positive_rate",
        "quantile_monotonicity_30bp",
        "long_short_annual_return_10bp",
        "long_short_annual_return_30bp",
        "long_short_annual_return_50bp",
        "mean_absolute_industry_active_weight",
        "median_capacity_cny",
        "frozen_oos_ic_mean",
        "frozen_oos_newey_west_t",
        "selected",
        "failed_checks",
    ]
    validation[retained].to_csv(output / "factor_validation_summary.csv", index=False)
    shutil.copy2(run_dir / "frozen_factor_selection.json", output / "frozen_factor_selection.json")
    shutil.copy2(
        run_dir / "selected_factor_correlations.csv",
        output / "selected_factor_correlations.csv",
    )
    for name in (
        "factor_incremental_analysis.csv",
        "factor_incremental_ic_timeseries.csv",
        "model_factor_eligibility.csv",
        "model_factor_correlations.csv",
        "model_feature_manifest.json",
    ):
        shutil.copy2(run_dir / name, output / name)

    ic = pd.read_csv(run_dir / "equal_weight_factor_ic.csv")
    performance = pd.read_csv(run_dir / "equal_weight_factor_performance.csv")
    ic = ic[["segment", "ic_mean", "newey_west_t"]]
    performance.merge(ic, on="segment", validate="many_to_one")[
        [
            "segment",
            "cost_bps",
            "ic_mean",
            "newey_west_t",
            "cumulative_return",
            "annual_return",
            "sharpe",
            "max_drawdown",
        ]
    ].to_csv(output / "equal_weight_factor_baseline.csv", index=False)

    model_ic = pd.read_csv(run_dir / "model_input_equal_weight_ic.csv")
    model_performance = pd.read_csv(run_dir / "model_input_equal_weight_performance.csv")
    model_ic = model_ic[["segment", "ic_mean", "newey_west_t"]]
    model_performance.merge(model_ic, on="segment", validate="many_to_one")[
        [
            "segment",
            "cost_bps",
            "ic_mean",
            "newey_west_t",
            "cumulative_return",
            "annual_return",
            "sharpe",
            "max_drawdown",
        ]
    ].to_csv(output / "model_input_equal_weight_baseline.csv", index=False)

    pb_roe_ic = pd.read_csv(run_dir / "pb_roe_baseline_ic.csv")
    pb_roe_performance = pd.read_csv(run_dir / "pb_roe_baseline_performance.csv")
    pb_roe_ic = pb_roe_ic[["segment", "ic_mean", "newey_west_t"]]
    pb_roe_performance.merge(pb_roe_ic, on="segment", validate="many_to_one")[
        [
            "segment",
            "cost_bps",
            "ic_mean",
            "newey_west_t",
            "cumulative_return",
            "annual_return",
            "sharpe",
            "max_drawdown",
        ]
    ].to_csv(output / "pb_roe_baseline.csv", index=False)


def freeze_walk_forward_example(run_dir: Path, output: Path) -> None:
    """Freeze three audited prediction months for the presentation timeline."""
    panel = pd.read_parquet(
        run_dir / "model_factor_panel.parquet",
        columns=["signal_date", "entry_date", "exit_date"],
    ).drop_duplicates()
    for column in ["signal_date", "entry_date", "exit_date"]:
        panel[column] = pd.to_datetime(panel[column])

    rows = []
    for model, stem in (("Elastic Net", "elastic-net"), ("LightGBM", "lightgbm")):
        predictions = pd.read_parquet(run_dir / f"{stem}_predictions.parquet")
        predictions["signal_date"] = pd.to_datetime(predictions["signal_date"])
        prediction_dates = sorted(
            predictions.loc[
                predictions["signal_date"].ge(pd.Timestamp("2023-01-01")),
                "signal_date",
            ].unique()
        )[:3]
        for prediction_date in prediction_dates:
            current = panel.loc[panel["signal_date"].eq(prediction_date)].iloc[0]
            excluded = (
                panel.loc[
                    panel["signal_date"].lt(prediction_date)
                    & panel["exit_date"].gt(prediction_date)
                ]
                .sort_values("signal_date")
                .iloc[-1]
            )
            row = predictions.loc[predictions["signal_date"].eq(prediction_date)].iloc[0]
            rows.append(
                {
                    "model": model,
                    "prediction_date": prediction_date,
                    "training_start": row["training_start"],
                    "training_end": row["training_end"],
                    "validation_start": row.get("validation_start", pd.NaT),
                    "validation_end": row.get("validation_end", pd.NaT),
                    "training_label_exit_end": row["training_label_exit_end"],
                    "validation_label_exit_end": row.get("validation_label_exit_end", pd.NaT),
                    "excluded_signal_date": excluded["signal_date"],
                    "excluded_label_exit_date": excluded["exit_date"],
                    "trade_date": current["entry_date"],
                    "prediction_label_exit_date": current["exit_date"],
                }
            )
    pd.DataFrame(rows).to_csv(output / "walk_forward_example.csv", index=False)


def freeze_modern_baseline(run_dir: Path, output: Path) -> None:
    shutil.copy2(run_dir / "core_factor_validation.csv", output / "core_factor_validation.csv")
    ic = pd.read_csv(run_dir / "ic_summary.csv")
    performance = pd.read_csv(run_dir / "long_short_performance.csv")
    performance = performance[performance["cost_bps"].eq(30)].set_index("factor")
    rows = []
    for row in ic.itertuples(index=False):
        factor, variant = FACTOR_NAMES[row.factor]
        perf = performance.loc[row.factor]
        rows.append(
            {
                "factor": factor,
                "variant": variant,
                "periods": row.periods,
                "ic_mean": row.ic_mean,
                "icir": row.icir,
                "ic_positive_rate": row.ic_positive_rate,
                "newey_west_t": row.newey_west_t,
                "net_annual_return_30bp": perf.annual_return,
                "annual_volatility_30bp": perf.annual_volatility,
                "sharpe_30bp": perf.sharpe,
                "max_drawdown_30bp": perf.max_drawdown,
            }
        )
    pd.DataFrame(rows).to_csv(output / "modern_factor_baseline.csv", index=False)

    segments = pd.read_csv(run_dir / "ic_segments.csv")
    mapped = segments["factor"].map(FACTOR_NAMES)
    segments["factor"] = mapped.map(lambda value: value[0])
    segments["variant"] = mapped.map(lambda value: value[1])
    segments[["segment", "factor", "variant", "periods", "ic_mean", "newey_west_t"]].to_csv(
        output / "modern_factor_segments.csv", index=False
    )


def freeze_model_summary(run_dir: Path, output: Path, stem: str, model: str) -> pd.DataFrame:
    all_row = pd.read_csv(run_dir / f"{stem}_ic_summary.csv").iloc[0]
    segments = pd.read_csv(run_dir / f"{stem}_ic_segments.csv")
    rows = [
        {
            "model": model,
            "segment": "all",
            "prediction_months": int(all_row["periods"]),
            "rank_ic_mean": all_row["ic_mean"],
            "icir": all_row["icir"],
            "ic_positive_rate": all_row["ic_positive_rate"],
            "newey_west_t": all_row["newey_west_t"],
        }
    ]
    names = {
        "development": "development_2015_2022",
        "exploratory_2023_2025": "exploratory_2023_2025",
    }
    for row in segments.itertuples(index=False):
        rows.append(
            {
                "model": model,
                "segment": names[row.segment],
                "prediction_months": row.periods,
                "rank_ic_mean": row.ic_mean,
                "icir": row.icir,
                "ic_positive_rate": row.ic_positive_rate,
                "newey_west_t": row.newey_west_t,
            }
        )
    frame = pd.DataFrame(rows)
    target = "elastic_net_summary.csv" if stem == "elastic-net" else "lightgbm_summary.csv"
    frame.to_csv(output / target, index=False)
    explanation = (
        "elastic-net_coefficient_summary.csv"
        if stem == "elastic-net"
        else "lightgbm_feature_importance_summary.csv"
    )
    shutil.copy2(run_dir / explanation, output / explanation)
    return frame


def freeze_portfolios(run_dir: Path, output: Path) -> None:
    rows = []
    for model, stem in (
        ("PBROE", "pb_roe_baseline"),
        ("StrictReversal", "strict_factor_equal_weight"),
        ("EligibleEqualWeight", "model_input_equal_weight"),
        ("ElasticNet", "elastic-net"),
        ("LightGBM", "lightgbm"),
    ):
        frame = pd.read_csv(run_dir / f"{stem}_portfolio_summary.csv")
        frame.insert(0, "model", model)
        keep = frame[frame["cost_bps"].eq(30) | frame["segment"].eq("exploratory_2023_2025")]
        rows.append(keep)
    pd.concat(rows, ignore_index=True).to_csv(
        output / "portfolio_model_comparison.csv", index=False
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="results/runs/modern-pb-roe")
    parser.add_argument("--paper-dir", default="results/runs/paper-reproduction")
    parser.add_argument("--output-dir", default="docs/results")
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    paper_dir = Path(args.paper_dir)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    freeze_paper(paper_dir, output)
    freeze_modern_baseline(run_dir, output)
    freeze_factor_validation(run_dir, output)
    freeze_model_summary(run_dir, output, "elastic-net", "ElasticNet")
    freeze_model_summary(run_dir, output, "lightgbm", "LightGBM")
    freeze_walk_forward_example(run_dir, output)
    freeze_portfolios(run_dir, output)
    shutil.copy2(run_dir / "final_audit.json", output / "final_audit_summary.json")
    metadata = {
        "modern_run": str(run_dir),
        "paper_run": str(paper_dir),
        "config_fingerprint": json.loads(
            (run_dir / "final_audit.json").read_text(encoding="utf-8")
        )["config_fingerprint"],
        "canonical_input_manifest_sha256": json.loads(
            (run_dir / "data_audit.json").read_text(encoding="utf-8")
        )["input_manifest_sha256"],
        "files": sorted(path.name for path in output.glob("*.csv")),
    }
    (output / "freeze_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

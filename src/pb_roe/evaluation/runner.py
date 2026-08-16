"""End-to-end modern factor evaluation runner."""

from __future__ import annotations

import json

import pandas as pd

from pb_roe.config import load_config
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.data.store import ParquetStore
from pb_roe.evaluation.exposures import (
    mean_factor_correlation,
    top_quantile_capacity,
    top_quantile_industry_exposure,
)
from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.evaluation.panel import build_modern_panel
from pb_roe.evaluation.performance import performance_metrics
from pb_roe.evaluation.preprocessing import neutralize_cross_section, winsorize_zscore
from pb_roe.evaluation.quantiles import long_short_spread, quantile_backtest


def evaluate_from_cli(
    config_path: str, factor_file: str | None, input_dir: str | None = None
) -> int:
    config = load_config(config_path)
    research = config.section("research")
    evaluation = config.section("evaluation")
    raw_factors = list(evaluation["factor_columns"])
    if factor_file:
        panel = pd.read_parquet(factor_file)
    elif input_dir:
        panel = build_modern_panel(
            ParquetStore(input_dir, immutable=False).read_bundle(),
            research.get("factor_start_date", research["start_date"]),
            research["end_date"],
            minimum_listing_days=int(research.get("minimum_listing_days", 0)),
        )
    else:
        providers = config.section("data").get("providers", {})
        if not all(value == "fixture" for value in providers.values()):
            raise FileNotFoundError("--factor-file is required unless all providers are fixture")
        panel = build_modern_panel(fixture_bundle(), research["start_date"], research["end_date"])

    panel["signal_date"] = pd.to_datetime(panel["signal_date"]).dt.normalize()
    factor_start = pd.Timestamp(
        research.get("factor_start_date", research["start_date"])
    ).normalize()
    panel = panel[panel["signal_date"] >= factor_start].copy()

    processed = winsorize_zscore(
        panel,
        raw_factors,
        lower=float(research.get("winsor_lower", 0.01)),
        upper=float(research.get("winsor_upper", 0.99)),
    )
    coverage = (
        panel.groupby("signal_date")[raw_factors]
        .count()
        .div(panel.groupby("signal_date").size(), axis=0)
        .rename_axis(columns="factor")
        .stack(future_stack=True)
        .rename("coverage")
        .reset_index()
    )
    coverage_threshold = float(config.section("quality")["factor_coverage"])
    eligible_dates = coverage.groupby("signal_date")["coverage"].min()
    eligible_dates = eligible_dates[eligible_dates >= coverage_threshold].index
    dropped_dates = sorted(set(processed["signal_date"]) - set(eligible_dates))
    processed = processed[processed["signal_date"].isin(eligible_dates)].copy()
    if processed.empty:
        raise ValueError("No signal date passed the configured factor coverage gate")
    factor_columns = [f"{factor}_z" for factor in raw_factors]
    industry_column = str(evaluation.get("industry_column", "industry"))
    industry_neutral_columns: list[str] = []
    if industry_column in processed:
        for factor in factor_columns:
            column = f"{factor}_industry_neutral"
            processed[column] = neutralize_cross_section(
                processed,
                factor,
                industry_column=industry_column,
            )
            industry_neutral_columns.append(column)
    factor_columns.extend(industry_neutral_columns)
    return_column = str(evaluation.get("return_column", "forward_return"))
    ic_series = calculate_ic(processed, factor_columns, return_column=return_column)
    ic_summary = summarize_ic(ic_series)
    quantiles = int(research.get("quantiles", 5))
    cost_rates = [
        float(value)
        for value in config.section("costs").get(
            "sensitivity_rates", [config.section("costs").get("base_rate", 0.0)]
        )
    ]
    quantile_frames: list[pd.DataFrame] = []
    for cost_rate in cost_rates:
        for factor in factor_columns:
            frame = quantile_backtest(
                processed,
                factor,
                return_column=return_column,
                quantiles=quantiles,
                cost_rate=cost_rate,
            )
            frame["cost_rate"] = cost_rate
            frame["cost_bps"] = int(round(cost_rate * 10_000))
            quantile_frames.append(frame)
    quantile_returns = pd.concat(quantile_frames, ignore_index=True)
    spreads = long_short_spread(quantile_returns)
    performance_rows = [
        {
            "factor": factor,
            "cost_rate": cost_rate,
            "cost_bps": int(round(float(cost_rate) * 10_000)),
            "average_monthly_turnover": float(group["turnover"].mean()),
            **performance_metrics(group["net_spread"]),
        }
        for (factor, cost_rate), group in spreads.groupby(["factor", "cost_rate"])
    ]
    performance = pd.DataFrame(performance_rows)
    exposures = pd.concat(
        [
            top_quantile_industry_exposure(
                processed, factor, industry_column=industry_column, quantiles=quantiles
            )
            for factor in factor_columns
        ],
        ignore_index=True,
    )
    correlations = mean_factor_correlation(processed, factor_columns)
    capacity = pd.concat(
        [
            top_quantile_capacity(processed, factor, quantiles=quantiles)
            for factor in factor_columns
        ],
        ignore_index=True,
    )
    execution_coverage = (
        processed.groupby("signal_date")[return_column]
        .agg(observations="size", executable="count")
        .reset_index()
    )
    execution_coverage["coverage"] = (
        execution_coverage["executable"] / execution_coverage["observations"]
    )
    if "entry_locked_limit" in processed:
        locked = processed.groupby("signal_date")["entry_locked_limit"].sum().astype(int)
        execution_coverage["locked_limit"] = execution_coverage["signal_date"].map(locked)
    for column in ("entry_delay_days", "exit_delay_days"):
        if column in processed:
            delayed = processed[column].gt(0).groupby(processed["signal_date"]).sum().astype(int)
            execution_coverage[f"{column}_delayed"] = execution_coverage["signal_date"].map(delayed)
    annual_ic = (
        ic_series.assign(year=pd.to_datetime(ic_series["signal_date"]).dt.year)
        .groupby(["factor", "year"])["ic"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    segment_boundaries = {
        "warmup": (pd.Timestamp(factor_start), pd.Timestamp("2014-12-31")),
        "development": (pd.Timestamp("2015-01-01"), pd.Timestamp(research["development_end"])),
        "frozen_oos": (pd.Timestamp(research["oos_start"]), pd.Timestamp(research["end_date"])),
    }
    segment_frames: list[pd.DataFrame] = []
    for segment, (start, end) in segment_boundaries.items():
        selected = ic_series[pd.to_datetime(ic_series["signal_date"]).between(start, end)]
        summary = summarize_ic(selected)
        summary.insert(0, "segment", segment)
        segment_frames.append(summary)
    segment_ic = pd.concat(segment_frames, ignore_index=True)

    validation_rows: list[dict[str, object]] = []
    for factor in factor_columns:
        full = ic_summary[ic_summary["factor"] == factor].iloc[0]
        development = segment_ic[
            (segment_ic["segment"] == "development") & (segment_ic["factor"] == factor)
        ].iloc[0]
        frozen_oos = segment_ic[
            (segment_ic["segment"] == "frozen_oos") & (segment_ic["factor"] == factor)
        ].iloc[0]
        quantile_means = (
            quantile_returns[
                (quantile_returns["factor"] == factor) & (quantile_returns["cost_bps"] == 30)
            ]
            .groupby("quantile")["net_return"]
            .mean()
            .reindex(range(1, quantiles + 1))
        )
        costs = performance[performance["factor"] == factor].set_index("cost_bps")
        validation_rows.append(
            {
                "factor": factor,
                "full_ic_mean": full["ic_mean"],
                "full_newey_west_t": full["newey_west_t"],
                "development_ic_mean": development["ic_mean"],
                "development_newey_west_t": development["newey_west_t"],
                "frozen_oos_ic_mean": frozen_oos["ic_mean"],
                "frozen_oos_newey_west_t": frozen_oos["newey_west_t"],
                "quantile_monotonicity_30bp": quantile_means.corr(
                    pd.Series(range(1, quantiles + 1), index=quantile_means.index),
                    method="spearman",
                ),
                **{
                    f"long_short_annual_return_{cost_bps}bp": costs.loc[cost_bps, "annual_return"]
                    for cost_bps in (10, 30, 50)
                },
                **{
                    f"quantile_{quantile}_mean_monthly_return_30bp": quantile_means.loc[quantile]
                    for quantile in range(1, quantiles + 1)
                },
            }
        )
    validation = pd.DataFrame(validation_rows).round(6)

    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    processed.to_parquet(output / "modern_factor_panel.parquet", index=False)
    coverage.to_csv(output / "factor_coverage.csv", index=False)
    ic_series.to_csv(output / "ic_timeseries.csv", index=False)
    ic_summary.to_csv(output / "ic_summary.csv", index=False)
    annual_ic.to_csv(output / "ic_annual.csv", index=False)
    segment_ic.to_csv(output / "ic_segments.csv", index=False)
    validation.to_csv(output / "core_factor_validation.csv", index=False, float_format="%.6f")
    quantile_returns.to_csv(output / "quantile_returns.csv", index=False)
    spreads.to_csv(output / "long_short_spreads.csv", index=False)
    performance.to_csv(output / "long_short_performance.csv", index=False)
    exposures.to_csv(output / "industry_exposures.csv", index=False)
    correlations.to_csv(output / "factor_correlations.csv")
    capacity.to_csv(output / "capacity_estimates.csv", index=False)
    execution_coverage.to_csv(output / "execution_coverage.csv", index=False)
    metadata = {
        "run_id": config.run_id,
        "config_fingerprint": config.fingerprint,
        "observations": len(processed),
        "signal_dates": int(processed["signal_date"].nunique()),
        "dropped_signal_dates": [pd.Timestamp(value).date().isoformat() for value in dropped_dates],
        "factor_columns": factor_columns,
        "output": str(output),
    }
    (output / "evaluation_run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0

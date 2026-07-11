"""End-to-end modern factor evaluation runner."""

from __future__ import annotations

import json

import pandas as pd

from pb_roe.config import load_config
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.evaluation.exposures import mean_factor_correlation, top_quantile_industry_exposure
from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.evaluation.panel import build_modern_panel
from pb_roe.evaluation.performance import performance_metrics
from pb_roe.evaluation.preprocessing import winsorize_zscore
from pb_roe.evaluation.quantiles import long_short_spread, quantile_backtest


def evaluate_from_cli(config_path: str, factor_file: str | None) -> int:
    config = load_config(config_path)
    research = config.section("research")
    evaluation = config.section("evaluation")
    raw_factors = list(evaluation["factor_columns"])
    if factor_file:
        panel = pd.read_parquet(factor_file)
    else:
        providers = config.section("data").get("providers", {})
        if not all(value == "fixture" for value in providers.values()):
            raise FileNotFoundError("--factor-file is required unless all providers are fixture")
        panel = build_modern_panel(fixture_bundle(), research["start_date"], research["end_date"])

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
    return_column = str(evaluation.get("return_column", "forward_return"))
    ic_series = calculate_ic(processed, factor_columns, return_column=return_column)
    ic_summary = summarize_ic(ic_series)
    quantiles = int(research.get("quantiles", 5))
    cost_rate = float(config.section("costs").get("base_rate", 0.0))
    quantile_frames = [
        quantile_backtest(
            processed,
            factor,
            return_column=return_column,
            quantiles=quantiles,
            cost_rate=cost_rate,
        )
        for factor in factor_columns
    ]
    quantile_returns = pd.concat(quantile_frames, ignore_index=True)
    spreads = long_short_spread(quantile_returns)
    performance_rows = [
        {"factor": factor, **performance_metrics(group["net_spread"])}
        for factor, group in spreads.groupby("factor")
    ]
    performance = pd.DataFrame(performance_rows)
    industry_column = str(evaluation.get("industry_column", "industry"))
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

    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    processed.to_parquet(output / "modern_factor_panel.parquet", index=False)
    coverage.to_csv(output / "factor_coverage.csv", index=False)
    ic_series.to_csv(output / "ic_timeseries.csv", index=False)
    ic_summary.to_csv(output / "ic_summary.csv", index=False)
    quantile_returns.to_csv(output / "quantile_returns.csv", index=False)
    spreads.to_csv(output / "long_short_spreads.csv", index=False)
    performance.to_csv(output / "long_short_performance.csv", index=False)
    exposures.to_csv(output / "industry_exposures.csv", index=False)
    correlations.to_csv(output / "factor_correlations.csv")
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

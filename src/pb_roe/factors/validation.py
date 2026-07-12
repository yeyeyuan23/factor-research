"""Development-only factor validation and frozen feature selection."""

from __future__ import annotations

import json

import pandas as pd

from pb_roe.config import load_config
from pb_roe.evaluation.exposures import (
    mean_factor_correlation,
    top_quantile_capacity,
    top_quantile_industry_exposure,
)
from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.evaluation.performance import performance_metrics
from pb_roe.evaluation.quantiles import long_short_spread, quantile_backtest
from pb_roe.models.dataset import load_model_panel


def _segment_summary(panel: pd.DataFrame, feature: str) -> pd.Series:
    return summarize_ic(calculate_ic(panel, [feature], return_column="target_return")).iloc[0]


def _factor_metrics(
    panel: pd.DataFrame,
    feature: str,
    category: str,
    direction: int,
    costs: list[float],
    quantiles: int,
) -> tuple[dict[str, object], pd.DataFrame]:
    oriented = f"{feature}_oriented"
    working = panel.copy()
    working[oriented] = working[feature] * direction
    ic = calculate_ic(working, [oriented], return_column="target_return")
    summary = summarize_ic(ic).iloc[0]
    annual = ic.assign(year=pd.to_datetime(ic["signal_date"]).dt.year).groupby("year")["ic"].mean()
    quantile_frames = []
    for cost in costs:
        frame = quantile_backtest(
            working, oriented, return_column="target_return", quantiles=quantiles, cost_rate=cost
        )
        frame["cost_rate"] = cost
        frame["cost_bps"] = int(round(cost * 10_000))
        quantile_frames.append(frame)
    quantile_returns = pd.concat(quantile_frames, ignore_index=True)
    spreads = long_short_spread(quantile_returns)
    performance = {
        int(round(float(cost_rate) * 10_000)): performance_metrics(group["net_spread"])[
            "annual_return"
        ]
        for cost_rate, group in spreads.groupby("cost_rate")
    }
    q30 = (
        quantile_returns[quantile_returns["cost_bps"] == 30]
        .groupby("quantile")["net_return"]
        .mean()
        .reindex(range(1, quantiles + 1))
    )
    monotonicity = q30.corr(pd.Series(range(1, quantiles + 1), index=q30.index), method="spearman")
    exposure = top_quantile_industry_exposure(working, oriented, quantiles=quantiles)
    capacity = top_quantile_capacity(working, oriented, quantiles=quantiles)
    row: dict[str, object] = {
        "factor": feature.removesuffix("_z"),
        "feature": feature,
        "category": category,
        "direction": direction,
        "minimum_monthly_coverage": panel.groupby("signal_date")[feature]
        .apply(lambda x: x.notna().mean())
        .min(),
        "periods": summary["periods"],
        "ic_mean": summary["ic_mean"],
        "icir": summary["icir"],
        "ic_positive_rate": summary["ic_positive_rate"],
        "newey_west_t": summary["newey_west_t"],
        "year_positive_rate": annual.gt(0).mean(),
        "quantile_monotonicity_30bp": monotonicity,
        "mean_absolute_industry_active_weight": exposure["active_weight"].abs().mean(),
        "maximum_absolute_industry_active_weight": exposure["active_weight"].abs().max(),
        "median_capacity_cny": capacity["full_rebalance_capacity_cny"].median(),
        **{f"long_short_annual_return_{bps}bp": value for bps, value in performance.items()},
        **{f"q{q}_mean_monthly_return_30bp": q30.loc[q] for q in range(1, quantiles + 1)},
    }
    return row, quantile_returns


def validate_factors_from_cli(
    config_path: str, factor_file: str | None, input_dir: str | None = None
) -> int:
    config = load_config(config_path)
    panel, available = load_model_panel(config, factor_file, input_dir)
    settings = config.section("evaluation")["factor_validation"]
    candidates = settings["candidates"]
    research = config.section("research")
    development = panel[
        pd.to_datetime(panel["signal_date"]).between(
            pd.Timestamp(settings["development_start"]), pd.Timestamp(research["development_end"])
        )
    ].copy()
    frozen = panel[
        pd.to_datetime(panel["signal_date"]).between(
            pd.Timestamp(research["oos_start"]), pd.Timestamp(research["end_date"])
        )
    ].copy()
    costs = [float(value) for value in config.section("costs")["sensitivity_rates"]]
    quantiles = int(research["quantiles"])
    rows, quantile_outputs = [], []
    for factor, specification in candidates.items():
        feature = f"{factor}_z"
        if feature not in available:
            continue
        row, quantile_returns = _factor_metrics(
            development,
            feature,
            str(specification["category"]),
            int(specification["direction"]),
            costs,
            quantiles,
        )
        oos = frozen.copy()
        oos[f"{feature}_oriented"] = oos[feature] * int(specification["direction"])
        oos_summary = _segment_summary(oos, f"{feature}_oriented")
        row.update(
            {
                "frozen_oos_ic_mean": oos_summary["ic_mean"],
                "frozen_oos_newey_west_t": oos_summary["newey_west_t"],
            }
        )
        checks = {
            "coverage": row["minimum_monthly_coverage"]
            >= config.section("quality")["factor_coverage"],
            "ic": row["ic_mean"] >= settings["minimum_ic"],
            "t_stat": row["newey_west_t"] >= settings["minimum_newey_west_t"],
            "year_stability": row["year_positive_rate"] >= settings["minimum_year_positive_rate"],
            "monotonicity": row["quantile_monotonicity_30bp"]
            >= settings["minimum_quantile_monotonicity"],
            "cost_30bp": (
                not settings["require_positive_30bp_spread"]
                or row["long_short_annual_return_30bp"] > 0
            ),
        }
        row["selected"] = all(checks.values())
        row["failed_checks"] = "|".join(key for key, passed in checks.items() if not passed)
        rows.append(row)
        quantile_returns["factor"] = factor
        quantile_outputs.append(quantile_returns)
    validation = pd.DataFrame(rows).sort_values(["category", "factor"])
    selected_rows = validation[validation["selected"]]
    selected = selected_rows["feature"].tolist()
    if not selected:
        raise ValueError("No factor passed the frozen development-sample selection rules")
    selected_directions = dict(
        zip(selected_rows["feature"], selected_rows["direction"], strict=True)
    )
    equal_weight = panel.copy()
    equal_weight["equal_weight_score"] = pd.concat(
        [equal_weight[feature] * direction for feature, direction in selected_directions.items()],
        axis=1,
    ).mean(axis=1)
    equal_weight_ic = calculate_ic(
        equal_weight, ["equal_weight_score"], return_column="target_return"
    )
    segment_rows = []
    equal_weight_performance_rows = []
    for segment, sample in (("development", development), ("frozen_oos", frozen)):
        sample = sample.copy()
        sample["equal_weight_score"] = pd.concat(
            [sample[feature] * direction for feature, direction in selected_directions.items()],
            axis=1,
        ).mean(axis=1)
        summary = _segment_summary(sample, "equal_weight_score").to_dict()
        summary["segment"] = segment
        segment_rows.append(summary)
        for cost in costs:
            quantile_returns = quantile_backtest(
                sample,
                "equal_weight_score",
                return_column="target_return",
                quantiles=quantiles,
                cost_rate=cost,
            )
            spreads = long_short_spread(quantile_returns)
            equal_weight_performance_rows.append(
                {
                    "segment": segment,
                    "cost_bps": int(round(cost * 10_000)),
                    **performance_metrics(spreads["net_spread"]),
                }
            )
    correlations = mean_factor_correlation(development, selected)
    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    validation.round(6).to_csv(output / "factor_validation.csv", index=False, float_format="%.6f")
    pd.concat(quantile_outputs, ignore_index=True).to_csv(
        output / "factor_validation_quantiles.csv", index=False
    )
    correlations.to_csv(output / "selected_factor_correlations.csv")
    pd.DataFrame(segment_rows).round(6).to_csv(
        output / "equal_weight_factor_ic.csv", index=False, float_format="%.6f"
    )
    pd.DataFrame(equal_weight_performance_rows).round(6).to_csv(
        output / "equal_weight_factor_performance.csv",
        index=False,
        float_format="%.6f",
    )
    equal_weight_ic.to_csv(output / "equal_weight_factor_ic_timeseries.csv", index=False)
    frozen_payload = {
        "config_fingerprint": config.fingerprint,
        "selection_sample": f"{settings['development_start']}/{research['development_end']}",
        "selected_features": selected,
        "selected_directions": selected_directions,
        "candidate_count": len(validation),
        "selected_count": len(selected),
        "rules": {key: value for key, value in settings.items() if key != "candidates"},
    }
    (output / "frozen_factor_selection.json").write_text(
        json.dumps(frozen_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(frozen_payload, ensure_ascii=False, indent=2, default=str))
    return 0

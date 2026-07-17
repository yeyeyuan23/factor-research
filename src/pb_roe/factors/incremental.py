"""Development-only incremental tests relative to the modern PB-ROE baseline."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.evaluation.performance import performance_metrics
from pb_roe.evaluation.quantiles import long_short_spread, quantile_backtest

SUMMARY_COLUMNS = (
    "factor",
    "feature",
    "category",
    "expected_direction",
    "baseline_feature",
    "mean_absolute_baseline_correlation",
    "residual_ic_mean",
    "residual_newey_west_t",
    "baseline_ic_mean",
    "add_one_ic_mean",
    "add_one_newey_west_t",
    "add_one_delta_ic",
    "add_one_improvement_year_rate",
    "baseline_monotonicity_30bp",
    "add_one_monotonicity_30bp",
    "add_one_delta_monotonicity_30bp",
    "baseline_long_short_annual_return_30bp",
    "add_one_long_short_annual_return_30bp",
    "add_one_delta_long_short_annual_return_30bp",
    "incremental_pass",
    "failed_incremental_checks",
)


def _residualize_by_month(
    panel: pd.DataFrame, target: str, controls: Sequence[str]
) -> pd.Series:
    residuals = pd.Series(np.nan, index=panel.index, dtype=float)
    columns = [target, *controls]
    for _, snapshot in panel.groupby("signal_date", sort=True):
        valid = snapshot[columns].dropna()
        if len(valid) <= len(controls) + 1 or valid[target].nunique() < 2:
            continue
        matrix = np.column_stack(
            [np.ones(len(valid)), valid[list(controls)].to_numpy(dtype=float)]
        )
        values = valid[target].to_numpy(dtype=float)
        coefficients = np.linalg.lstsq(matrix, values, rcond=None)[0]
        residuals.loc[valid.index] = values - matrix @ coefficients
    return residuals


def _score_economics(
    panel: pd.DataFrame, score: str, quantiles: int, cost_rate: float
) -> tuple[float, float]:
    quantile_returns = quantile_backtest(
        panel,
        score,
        return_column="target_return",
        quantiles=quantiles,
        cost_rate=cost_rate,
    )
    means = (
        quantile_returns.groupby("quantile")["net_return"]
        .mean()
        .reindex(range(1, quantiles + 1))
    )
    monotonicity = means.corr(
        pd.Series(range(1, quantiles + 1), index=means.index), method="spearman"
    )
    annual_return = performance_metrics(
        long_short_spread(quantile_returns)["net_spread"]
    )["annual_return"]
    return float(monotonicity), float(annual_return)


def build_pb_roe_incremental_analysis(
    development: pd.DataFrame,
    candidates: Mapping[str, Mapping[str, object]],
    available_features: Sequence[str],
    settings: Mapping[str, object],
    quantiles: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Test primitive extension factors for information beyond PB and ROE."""

    baseline_feature = str(settings["baseline_feature"])
    core_features = list(settings["core_features"])
    candidate_weight = float(settings["candidate_weight"])
    cost_rate = float(settings["cost_rate"])
    if not 0 < candidate_weight < 1:
        raise ValueError("candidate_weight must be between zero and one")
    required = {baseline_feature, *core_features}
    missing = sorted(required.difference(available_features))
    if missing:
        raise ValueError(f"Incremental analysis is missing required features: {missing}")

    baseline_ic = calculate_ic(
        development, [baseline_feature], return_column="target_return"
    ).rename(columns={"ic": "baseline_ic"})
    baseline_ic = baseline_ic[["signal_date", "baseline_ic"]]
    baseline_summary = summarize_ic(
        calculate_ic(development, [baseline_feature], return_column="target_return")
    ).iloc[0]
    baseline_monotonicity, baseline_return = _score_economics(
        development, baseline_feature, quantiles, cost_rate
    )

    maximum_baseline_correlation = float(settings["maximum_baseline_correlation"])
    minimum_residual_ic = float(settings["minimum_residual_ic"])
    minimum_add_one_delta_ic = float(settings["minimum_add_one_delta_ic"])
    minimum_improvement_year_rate = float(settings["minimum_improvement_year_rate"])
    rows: list[dict[str, object]] = []
    timeseries: list[pd.DataFrame] = []
    available = set(available_features)
    core = set(core_features)

    for factor, specification in candidates.items():
        feature = f"{factor}_z"
        if feature not in available or feature in core or feature == baseline_feature:
            continue
        direction = int(specification["direction"])
        oriented = f"{feature}_incremental_oriented"
        residual = f"{feature}_residual_to_pb_roe"
        add_one = f"{feature}_add_one_pb_roe"
        working = development.copy()
        working[oriented] = working[feature] * direction
        working[residual] = _residualize_by_month(working, oriented, core_features)
        working[add_one] = (
            (1 - candidate_weight) * working[baseline_feature]
            + candidate_weight * working[oriented]
        )

        monthly_correlations = working.groupby("signal_date").apply(
            lambda snapshot, oriented=oriented: snapshot[
                [baseline_feature, oriented]
            ].corr(
                method="spearman"
            ).iloc[0, 1],
            include_groups=False,
        )
        residual_ic = calculate_ic(
            working, [residual], return_column="target_return"
        ).rename(columns={"ic": "residual_ic"})
        add_one_ic = calculate_ic(
            working, [add_one], return_column="target_return"
        ).rename(columns={"ic": "add_one_ic"})
        residual_summary = summarize_ic(
            residual_ic.rename(columns={"residual_ic": "ic"})
        ).iloc[0]
        add_one_summary = summarize_ic(
            add_one_ic.rename(columns={"add_one_ic": "ic"})
        ).iloc[0]
        comparison = baseline_ic.merge(
            add_one_ic[["signal_date", "add_one_ic"]],
            on="signal_date",
            validate="one_to_one",
        )
        annual = (
            comparison.assign(year=comparison["signal_date"].dt.year)
            .groupby("year")[["baseline_ic", "add_one_ic"]]
            .mean()
        )
        improvement_rate = float(annual["add_one_ic"].gt(annual["baseline_ic"]).mean())
        add_one_monotonicity, add_one_return = _score_economics(
            working, add_one, quantiles, cost_rate
        )
        checks = {
            "baseline_correlation": float(monthly_correlations.abs().mean())
            < maximum_baseline_correlation,
            "residual_ic": float(residual_summary["ic_mean"]) > minimum_residual_ic,
            "add_one_ic": (
                float(add_one_summary["ic_mean"]) - float(baseline_summary["ic_mean"])
            )
            > minimum_add_one_delta_ic,
            "year_stability": improvement_rate >= minimum_improvement_year_rate,
        }
        rows.append(
            {
                "factor": factor,
                "feature": feature,
                "category": str(specification["category"]),
                "expected_direction": direction,
                "baseline_feature": baseline_feature,
                "mean_absolute_baseline_correlation": float(
                    monthly_correlations.abs().mean()
                ),
                "residual_ic_mean": float(residual_summary["ic_mean"]),
                "residual_newey_west_t": float(residual_summary["newey_west_t"]),
                "baseline_ic_mean": float(baseline_summary["ic_mean"]),
                "add_one_ic_mean": float(add_one_summary["ic_mean"]),
                "add_one_newey_west_t": float(add_one_summary["newey_west_t"]),
                "add_one_delta_ic": float(add_one_summary["ic_mean"])
                - float(baseline_summary["ic_mean"]),
                "add_one_improvement_year_rate": improvement_rate,
                "baseline_monotonicity_30bp": baseline_monotonicity,
                "add_one_monotonicity_30bp": add_one_monotonicity,
                "add_one_delta_monotonicity_30bp": add_one_monotonicity
                - baseline_monotonicity,
                "baseline_long_short_annual_return_30bp": baseline_return,
                "add_one_long_short_annual_return_30bp": add_one_return,
                "add_one_delta_long_short_annual_return_30bp": add_one_return
                - baseline_return,
                "incremental_pass": all(checks.values()),
                "failed_incremental_checks": "|".join(
                    key for key, passed in checks.items() if not passed
                ),
            }
        )
        timeseries.append(
            comparison.merge(
                residual_ic[["signal_date", "residual_ic"]],
                on="signal_date",
                validate="one_to_one",
            ).assign(factor=factor, feature=feature)
        )

    summary = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    detail = (
        pd.concat(timeseries, ignore_index=True)
        if timeseries
        else pd.DataFrame(
            columns=[
                "signal_date",
                "baseline_ic",
                "add_one_ic",
                "residual_ic",
                "factor",
                "feature",
            ]
        )
    )
    return summary, detail

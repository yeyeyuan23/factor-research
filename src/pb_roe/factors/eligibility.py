"""Model-input eligibility based on quality, direction and redundancy.

This module deliberately does not select features by positive standalone return.
Standalone alpha validation remains a separate research result; this layer only
decides whether a primitive feature is safe and distinct enough to enter a model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from pb_roe.evaluation.exposures import mean_factor_correlation
from pb_roe.evaluation.ic import calculate_ic, summarize_ic


def _connected_components(
    features: Sequence[str], correlations: pd.DataFrame, threshold: float
) -> list[list[str]]:
    remaining = set(features)
    components: list[list[str]] = []
    while remaining:
        root = min(remaining)
        remaining.remove(root)
        component = {root}
        frontier = [root]
        while frontier:
            current = frontier.pop()
            neighbours = {
                other
                for other in list(remaining)
                if pd.notna(correlations.loc[current, other])
                and abs(float(correlations.loc[current, other])) >= threshold
            }
            remaining.difference_update(neighbours)
            component.update(neighbours)
            frontier.extend(neighbours)
        components.append(sorted(component))
    return sorted(components, key=lambda values: values[0])


def build_model_factor_eligibility(
    development: pd.DataFrame,
    candidates: Mapping[str, Mapping[str, object]],
    available_features: Sequence[str],
    settings: Mapping[str, object],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Return eligibility rows, the development correlation matrix and final features."""

    minimum_monthly_coverage = float(settings["minimum_monthly_coverage"])
    minimum_coverage_pass_rate = float(settings["minimum_coverage_pass_rate"])
    minimum_valid_months = int(settings["minimum_valid_months"])
    minimum_median_stock_count = int(settings["minimum_median_stock_count"])
    minimum_unique_values = int(settings["minimum_unique_values"])
    opposite_t_threshold = float(settings["significantly_opposite_t"])
    correlation_threshold = float(settings["maximum_absolute_correlation"])
    excluded_derived = set(settings.get("exclude_derived_features", []))
    priority = list(settings.get("representative_priority", available_features))
    priority_rank = {feature: rank for rank, feature in enumerate(priority)}

    available = set(available_features)
    rows: list[dict[str, object]] = []
    for factor, specification in candidates.items():
        feature = f"{factor}_z"
        if feature not in available:
            continue
        monthly = development.groupby("signal_date")[feature]
        coverage = monthly.apply(lambda values: values.notna().mean())
        valid_count = monthly.count()
        unique_count = monthly.nunique(dropna=True)
        coverage_pass = coverage.ge(minimum_monthly_coverage)
        usable_unique = unique_count[coverage_pass]
        direction = int(specification["direction"])
        oriented = f"{feature}_eligibility_oriented"
        working = development.assign(**{oriented: development[feature] * direction})
        ic_summary = summarize_ic(
            calculate_ic(working, [oriented], return_column="target_return")
        ).iloc[0]
        row = {
            "factor": factor,
            "feature": feature,
            "category": str(specification["category"]),
            "expected_direction": direction,
            "total_development_months": int(len(coverage)),
            "valid_months": int(coverage_pass.sum()),
            "coverage_pass_rate": float(coverage_pass.mean()),
            "minimum_monthly_coverage": float(coverage.min()),
            "median_valid_stock_count": float(valid_count.median()),
            "minimum_unique_values": (
                int(usable_unique.min()) if not usable_unique.empty else 0
            ),
            "oriented_development_ic_mean": float(ic_summary["ic_mean"]),
            "oriented_development_newey_west_t": float(ic_summary["newey_west_t"]),
            "direction_conflict": bool(
                float(ic_summary["newey_west_t"]) <= opposite_t_threshold
            ),
            "derived_feature_exclusion": feature in excluded_derived,
        }
        checks = {
            "valid_months": row["valid_months"] >= minimum_valid_months,
            "coverage": row["coverage_pass_rate"] >= minimum_coverage_pass_rate,
            "stock_count": row["median_valid_stock_count"] >= minimum_median_stock_count,
            "unique_values": row["minimum_unique_values"] >= minimum_unique_values,
            "direction": not row["direction_conflict"],
            "primitive": not row["derived_feature_exclusion"],
        }
        row["pre_redundancy_eligible"] = all(checks.values())
        row["failed_pre_redundancy_checks"] = "|".join(
            key for key, passed in checks.items() if not passed
        )
        rows.append(row)

    eligibility = pd.DataFrame(rows)
    if eligibility.empty:
        raise ValueError("No configured candidate is available for model eligibility")
    pre_redundancy = eligibility.loc[eligibility["pre_redundancy_eligible"], "feature"].tolist()
    if not pre_redundancy:
        raise ValueError("No feature passed model input data, direction and primitive checks")
    correlations = mean_factor_correlation(development, pre_redundancy)
    components = _connected_components(pre_redundancy, correlations, correlation_threshold)

    cluster_by_feature: dict[str, str] = {}
    representative_by_feature: dict[str, str] = {}
    for number, component in enumerate(components, start=1):
        representative = min(
            component,
            key=lambda feature: (priority_rank.get(feature, len(priority)), feature),
        )
        cluster = f"cluster_{number:02d}"
        for feature in component:
            cluster_by_feature[feature] = cluster
            representative_by_feature[feature] = representative

    eligibility["redundancy_cluster"] = eligibility["feature"].map(cluster_by_feature)
    eligibility["cluster_representative"] = eligibility["feature"].map(
        representative_by_feature
    )
    eligibility["maximum_absolute_correlation"] = eligibility["feature"].map(
        lambda feature: (
            float(
                correlations.loc[feature]
                .drop(labels=[feature], errors="ignore")
                .abs()
                .max()
            )
            if feature in correlations.index and len(correlations.index) > 1
            else 0.0
        )
    )
    eligibility["redundant_feature"] = eligibility.apply(
        lambda row: bool(
            row["pre_redundancy_eligible"]
            and row["feature"] != row["cluster_representative"]
        ),
        axis=1,
    )
    eligibility["eligible"] = eligibility.apply(
        lambda row: bool(row["pre_redundancy_eligible"] and not row["redundant_feature"]),
        axis=1,
    )
    eligibility["failed_checks"] = eligibility.apply(
        lambda row: "|".join(
            value
            for value in (
                str(row["failed_pre_redundancy_checks"]),
                "redundancy" if row["redundant_feature"] else "",
            )
            if value
        ),
        axis=1,
    )
    eligible = sorted(
        eligibility.loc[eligibility["eligible"], "feature"].tolist(),
        key=lambda feature: (priority_rank.get(feature, len(priority)), feature),
    )
    if not eligible:
        raise ValueError("No feature passed final model input eligibility")
    return eligibility, correlations, eligible

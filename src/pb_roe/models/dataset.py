"""Shared model dataset construction."""

from __future__ import annotations

import pandas as pd

from pb_roe.config import ResearchConfig
from pb_roe.data.pit import fundamentals_asof
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.data.store import ParquetStore
from pb_roe.evaluation.panel import build_modern_panel
from pb_roe.evaluation.preprocessing import neutralize_cross_section, winsorize_zscore
from pb_roe.factors.library import compute_price_factors


def load_model_panel(
    config: ResearchConfig, factor_file: str | None, input_dir: str | None = None
) -> tuple[pd.DataFrame, list[str]]:
    research = config.section("research")
    evaluation = config.section("evaluation")
    raw_factors = list(evaluation["factor_columns"])
    expanded_factors = list(evaluation.get("expanded_factor_columns", []))
    if factor_file:
        panel = pd.read_parquet(factor_file)
        raw_factors.extend(expanded_factors)
    elif input_dir:
        bundle = ParquetStore(input_dir, immutable=False).read_bundle()
        panel = build_modern_panel(
            bundle,
            research.get("factor_start_date", research["start_date"]),
            research["end_date"],
            minimum_listing_days=int(research.get("minimum_listing_days", 0)),
        )
        signals = panel[["signal_date", "security_id"]].drop_duplicates()
        fundamental_names = [
            factor
            for factor in expanded_factors
            if factor in {"gross_margin", "revenue_growth", "earnings_growth"}
        ]
        if fundamental_names:
            selected = fundamentals_asof(
                signals,
                bundle.fundamentals[
                    bundle.fundamentals["metric"].isin(fundamental_names)
                ],
            )
            fundamental_panel = selected.pivot_table(
                index=["signal_date", "security_id"],
                columns="metric",
                values="value",
                aggfunc="last",
            ).reset_index()
            panel = panel.merge(
                fundamental_panel,
                on=["signal_date", "security_id"],
                how="left",
                validate="one_to_one",
            )
        price_factors = compute_price_factors(
            bundle.prices,
            panel["signal_date"].drop_duplicates(),
        )
        panel = panel.merge(
            price_factors,
            on=["signal_date", "security_id"],
            how="left",
            validate="one_to_one",
        )
        raw_factors.extend(expanded_factors)
    else:
        providers = config.section("data").get("providers", {})
        if not all(value == "fixture" for value in providers.values()):
            raise FileNotFoundError("--factor-file is required unless all providers are fixture")
        bundle = fixture_bundle()
        panel = build_modern_panel(
            bundle,
            research.get("factor_start_date", research["start_date"]),
            research["end_date"],
        )
        price_factors = compute_price_factors(
            bundle.prices,
            panel["signal_date"].drop_duplicates(),
            minimum_beta_observations=20,
        )
        panel = panel.merge(
            price_factors,
            on=["signal_date", "security_id"],
            how="left",
            validate="one_to_one",
        )
        raw_factors.extend(expanded_factors)
    available = [factor for factor in raw_factors if factor in panel]
    processed = winsorize_zscore(
        panel,
        available,
        lower=float(research.get("winsor_lower", 0.01)),
        upper=float(research.get("winsor_upper", 0.99)),
    )
    return_column = str(evaluation.get("return_column", "forward_return"))
    target_neutralization = str(evaluation.get("target_neutralization", "industry"))
    if target_neutralization == "industry":
        processed["target_return"] = neutralize_cross_section(
            processed,
            return_column,
            industry_column=str(evaluation.get("industry_column", "industry")),
        )
    elif target_neutralization == "none":
        processed["target_return"] = pd.to_numeric(processed[return_column], errors="coerce")
    else:
        raise ValueError(
            "evaluation.target_neutralization must be either 'none' or 'industry'"
        )
    feature_columns = [f"{factor}_z" for factor in available]
    coverage_threshold = float(config.section("quality")["factor_coverage"])
    coverage = (
        processed.groupby("signal_date")[feature_columns]
        .count()
        .div(processed.groupby("signal_date").size(), axis=0)
    )
    retained_features = [
        feature
        for feature in feature_columns
        if float(coverage[feature].min()) >= coverage_threshold
    ]
    return processed, retained_features

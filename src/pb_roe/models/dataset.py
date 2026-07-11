"""Shared model dataset construction."""

from __future__ import annotations

import pandas as pd

from pb_roe.config import ResearchConfig
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.evaluation.panel import build_modern_panel
from pb_roe.evaluation.preprocessing import neutralize_cross_section, winsorize_zscore
from pb_roe.factors.library import compute_price_factors


def load_model_panel(
    config: ResearchConfig, factor_file: str | None
) -> tuple[pd.DataFrame, list[str]]:
    research = config.section("research")
    evaluation = config.section("evaluation")
    raw_factors = list(evaluation["factor_columns"])
    if factor_file:
        panel = pd.read_parquet(factor_file)
    else:
        providers = config.section("data").get("providers", {})
        if not all(value == "fixture" for value in providers.values()):
            raise FileNotFoundError("--factor-file is required unless all providers are fixture")
        bundle = fixture_bundle()
        panel = build_modern_panel(bundle, research["start_date"], research["end_date"])
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
        raw_factors.extend(
            [
                "momentum_12_1",
                "reversal_1m",
                "volatility_60d",
                "liquidity_20d",
                "beta_252d",
                "idiosyncratic_volatility",
            ]
        )
    available = [factor for factor in raw_factors if factor in panel]
    processed = winsorize_zscore(
        panel,
        available,
        lower=float(research.get("winsor_lower", 0.01)),
        upper=float(research.get("winsor_upper", 0.99)),
    )
    processed["target_return"] = neutralize_cross_section(
        processed,
        str(evaluation.get("return_column", "forward_return")),
        industry_column=str(evaluation.get("industry_column", "industry")),
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
        if float(coverage[feature].median()) >= coverage_threshold
    ]
    return processed, retained_features

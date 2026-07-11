"""CLI model training runner."""

from __future__ import annotations

import json

from pb_roe.config import load_config
from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.models.dataset import load_model_panel
from pb_roe.models.linear import walk_forward_elastic_net


def train_from_cli(config_path: str, factor_file: str | None, model_name: str) -> int:
    config = load_config(config_path)
    panel, features = load_model_panel(config, factor_file)
    if not features:
        raise ValueError("No feature passed the configured coverage gate")
    model_config = config.section("models")
    if model_name == "elastic-net":
        parameters = model_config["elastic_net"]
        predictions, diagnostics = walk_forward_elastic_net(
            panel,
            features,
            train_months=int(model_config["train_months"]),
            minimum_train_months=int(model_config["minimum_train_months"]),
            alpha=float(parameters["alpha"]),
            l1_ratio=float(parameters["l1_ratio"]),
            max_iter=int(parameters["max_iter"]),
            random_seed=int(config.section("project")["random_seed"]),
        )
    elif model_name == "lightgbm":
        from pb_roe.models.lightgbm import walk_forward_lightgbm

        predictions, diagnostics = walk_forward_lightgbm(panel, features, config)
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    if predictions.empty:
        raise ValueError("Walk-forward model produced no predictions")

    ic = calculate_ic(
        predictions.rename(columns={"prediction": "model_prediction"}),
        ["model_prediction"],
        return_column="target_return",
    )
    summary = summarize_ic(ic)
    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(output / f"{model_name}_predictions.parquet", index=False)
    diagnostics.to_csv(output / f"{model_name}_diagnostics.csv", index=False)
    summary.to_csv(output / f"{model_name}_ic_summary.csv", index=False)
    metadata = {
        "run_id": config.run_id,
        "model": model_name,
        "features": features,
        "predictions": len(predictions),
        "prediction_months": int(predictions["signal_date"].nunique()),
        "output": str(output),
    }
    (output / f"{model_name}_run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0

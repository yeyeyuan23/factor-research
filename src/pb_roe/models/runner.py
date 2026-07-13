"""CLI model training runner."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pb_roe.config import load_config
from pb_roe.evaluation.ic import calculate_ic, summarize_ic
from pb_roe.models.dataset import load_model_panel
from pb_roe.models.linear import walk_forward_elastic_net


def _load_frozen_features(
    selection_path: Path,
    available_features: list[str],
    config_fingerprint: str,
) -> tuple[list[str], dict[str, object]]:
    if not selection_path.exists():
        raise FileNotFoundError(
            "Frozen factor selection is missing; run validate-factors before train"
        )
    payload = json.loads(selection_path.read_text(encoding="utf-8"))
    if payload.get("config_fingerprint") != config_fingerprint:
        raise ValueError("Frozen factor selection does not match the active config")
    selected = list(payload.get("selected_features", []))
    if not selected:
        raise ValueError("Frozen factor selection contains no features")
    missing = [feature for feature in selected if feature not in available_features]
    if missing:
        raise ValueError(f"Frozen features missing from model panel: {missing}")
    return selected, payload


def train_from_cli(
    config_path: str,
    factor_file: str | None,
    model_name: str,
    input_dir: str | None = None,
) -> int:
    config = load_config(config_path)
    panel, available_features = load_model_panel(config, factor_file, input_dir)
    if not available_features:
        raise ValueError("No feature passed the configured coverage gate")
    selection_path = config.output_dir() / "frozen_factor_selection.json"
    features, selection = _load_frozen_features(
        selection_path,
        available_features,
        config.fingerprint,
    )
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
    factor_ic = summarize_ic(calculate_ic(panel, features, return_column="target_return"))
    research = config.section("research")
    segment_frames: list[pd.DataFrame] = []
    segments = {
        "development": (pd.Timestamp("2015-01-01"), pd.Timestamp(research["development_end"])),
        "frozen_oos": (pd.Timestamp(research["oos_start"]), pd.Timestamp(research["end_date"])),
    }
    for segment, (start, end) in segments.items():
        selected = ic[pd.to_datetime(ic["signal_date"]).between(start, end)]
        segment_summary = summarize_ic(selected)
        segment_summary.insert(0, "segment", segment)
        segment_frames.append(segment_summary)
    segment_ic = pd.concat(segment_frames, ignore_index=True)
    coefficient_summary = pd.DataFrame()
    if {"feature", "coefficient"} <= set(diagnostics):
        coefficient_summary = (
            diagnostics.groupby("feature")["coefficient"]
            .agg(mean="mean", std="std", nonzero_rate=lambda values: values.ne(0).mean())
            .reset_index()
        )
    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output / "model_factor_panel.parquet", index=False)
    predictions.to_parquet(output / f"{model_name}_predictions.parquet", index=False)
    diagnostics.to_csv(output / f"{model_name}_diagnostics.csv", index=False)
    if not coefficient_summary.empty:
        coefficient_summary.to_csv(output / f"{model_name}_coefficient_summary.csv", index=False)
    summary.to_csv(output / f"{model_name}_ic_summary.csv", index=False)
    segment_ic.to_csv(output / f"{model_name}_ic_segments.csv", index=False)
    factor_ic.to_csv(output / "expanded_factor_ic_summary.csv", index=False)
    metadata = {
        "run_id": config.run_id,
        "model": model_name,
        "config_fingerprint": config.fingerprint,
        "features": features,
        "factor_selection": str(selection_path),
        "selection_sample": selection.get("selection_sample"),
        "predictions": len(predictions),
        "prediction_months": int(predictions["signal_date"].nunique()),
        "output": str(output),
    }
    (output / f"{model_name}_run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0

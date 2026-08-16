"""Deterministic LightGBM walk-forward model with time-ordered validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import lightgbm as lgb
import numpy as np
import pandas as pd

from pb_roe.config import ResearchConfig
from pb_roe.data.schema import require_columns


def _fit_month(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
    target_column: str,
    parameters: Mapping[str, object],
    random_seed: int,
) -> tuple[np.ndarray, lgb.LGBMRegressor]:
    model = lgb.LGBMRegressor(
        objective="regression",
        verbosity=-1,
        random_state=random_seed,
        deterministic=True,
        force_col_wise=True,
        n_jobs=1,
        **{key: value for key, value in parameters.items() if key != "early_stopping_rounds"},
    )
    callbacks = [lgb.log_evaluation(period=0)]
    fit_kwargs: dict[str, object] = {"callbacks": callbacks}
    if not validation.empty:
        callbacks.append(
            lgb.early_stopping(int(parameters.get("early_stopping_rounds", 50)), verbose=False)
        )
        fit_kwargs.update(
            {
                "eval_set": [(validation[features], validation[target_column])],
                "eval_metric": "l2",
            }
        )
    model.fit(train[features], train[target_column], **fit_kwargs)
    best_iteration = model.best_iteration_ if model.best_iteration_ else model.n_estimators
    return model.predict(test[features], num_iteration=best_iteration), model


def walk_forward_lightgbm_raw(
    panel: pd.DataFrame,
    feature_columns: Iterable[str],
    parameters: Mapping[str, object],
    target_column: str = "target_return",
    train_months: int = 60,
    validation_months: int = 12,
    minimum_train_months: int = 24,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = list(feature_columns)
    require_columns(
        panel,
        ("signal_date", "exit_date", "security_id", target_column, *features),
        "model_panel",
    )
    working = panel.copy()
    working["signal_date"] = pd.to_datetime(working["signal_date"]).dt.normalize()
    working["exit_date"] = pd.to_datetime(working["exit_date"]).dt.normalize()
    dates = sorted(working["signal_date"].unique())
    predictions: list[pd.DataFrame] = []
    diagnostic_rows: list[dict[str, object]] = []
    for date in dates:
        prediction_date = pd.Timestamp(date)
        mature = working[
            (working["signal_date"] < prediction_date) & (working["exit_date"] <= prediction_date)
        ].dropna(subset=[target_column])
        history_dates = sorted(mature["signal_date"].unique())[-train_months:]
        if len(history_dates) < minimum_train_months:
            continue
        validation_count = min(validation_months, max(1, len(history_dates) // 3))
        fit_dates = history_dates[:-validation_count]
        validation_dates = history_dates[-validation_count:]
        if not fit_dates:
            continue
        train = mature[mature["signal_date"].isin(fit_dates)]
        validation = mature[mature["signal_date"].isin(validation_dates)]
        test = working[working["signal_date"] == prediction_date]
        if train.empty or test.empty:
            continue
        values, model = _fit_month(
            train,
            validation,
            test,
            features,
            target_column,
            parameters,
            random_seed,
        )
        prediction_columns = ["signal_date", "security_id", target_column]
        if target_column != "target_return" and "target_return" in test:
            prediction_columns.append("target_return")
        predicted = test[prediction_columns].copy()
        predicted["prediction"] = values
        predicted["model"] = "lightgbm"
        predicted["training_start"] = pd.Timestamp(fit_dates[0])
        predicted["training_end"] = pd.Timestamp(fit_dates[-1])
        predicted["validation_start"] = pd.Timestamp(validation_dates[0])
        predicted["validation_end"] = pd.Timestamp(validation_dates[-1])
        predicted["training_label_exit_end"] = pd.Timestamp(train["exit_date"].max())
        predicted["validation_label_exit_end"] = pd.Timestamp(validation["exit_date"].max())
        predictions.append(predicted)
        best_iteration = model.best_iteration_ if model.best_iteration_ else model.n_estimators
        diagnostic_rows.extend(
            {
                "prediction_date": prediction_date,
                "feature": feature,
                "importance_gain": float(importance),
                "best_iteration": int(best_iteration),
            }
            for feature, importance in zip(
                features,
                model.booster_.feature_importance(importance_type="gain"),
                strict=True,
            )
        )
    prediction_frame = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    return prediction_frame, pd.DataFrame(diagnostic_rows)


def walk_forward_lightgbm(
    panel: pd.DataFrame,
    feature_columns: Iterable[str],
    config: ResearchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model_config = config.section("models")
    return walk_forward_lightgbm_raw(
        panel,
        feature_columns,
        model_config["lightgbm"],
        target_column=str(model_config.get("target_column", "target_return")),
        train_months=int(model_config["train_months"]),
        validation_months=int(model_config["validation_months"]),
        minimum_train_months=int(model_config["minimum_train_months"]),
        random_seed=int(config.section("project")["random_seed"]),
    )

"""Elastic Net walk-forward baseline."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pb_roe.data.schema import require_columns


def walk_forward_elastic_net(
    panel: pd.DataFrame,
    feature_columns: Iterable[str],
    target_column: str = "target_return",
    train_months: int = 60,
    minimum_train_months: int = 24,
    alpha: float = 0.001,
    l1_ratio: float = 0.2,
    max_iter: int = 10000,
    random_seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = list(feature_columns)
    require_columns(
        panel,
        ("signal_date", "security_id", target_column, *features),
        "model_panel",
    )
    working = panel.copy()
    working["signal_date"] = pd.to_datetime(working["signal_date"]).dt.normalize()
    dates = sorted(working["signal_date"].unique())
    predictions: list[pd.DataFrame] = []
    coefficient_rows: list[dict[str, object]] = []
    for prediction_index in range(minimum_train_months, len(dates)):
        prediction_date = pd.Timestamp(dates[prediction_index])
        training_dates = dates[max(0, prediction_index - train_months) : prediction_index]
        train = working[working["signal_date"].isin(training_dates)].dropna(subset=[target_column])
        test = working[working["signal_date"] == prediction_date]
        if train.empty or test.empty:
            continue
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=max_iter,
                        random_state=random_seed,
                    ),
                ),
            ]
        )
        model.fit(train[features], train[target_column])
        predicted = test[["signal_date", "security_id", target_column]].copy()
        predicted["prediction"] = model.predict(test[features])
        predicted["model"] = "elastic_net"
        predicted["training_start"] = pd.Timestamp(training_dates[0])
        predicted["training_end"] = pd.Timestamp(training_dates[-1])
        predictions.append(predicted)
        coefficients = model.named_steps["model"].coef_
        coefficient_rows.extend(
            {
                "prediction_date": prediction_date,
                "feature": feature,
                "coefficient": float(value),
            }
            for feature, value in zip(features, coefficients, strict=True)
        )
    prediction_frame = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    return prediction_frame, pd.DataFrame(coefficient_rows)

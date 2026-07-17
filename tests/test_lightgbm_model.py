import numpy as np
import pandas as pd

from pb_roe.models.lightgbm import walk_forward_lightgbm_raw


def test_lightgbm_walk_forward_uses_past_training_and_validation_only() -> None:
    rows = []
    for date_index, month in enumerate(pd.date_range("2021-01-31", periods=12, freq="ME")):
        for security in range(12):
            x1 = security / 11
            x2 = (date_index + 1) / 12
            rows.append(
                {
                    "signal_date": month,
                    "exit_date": month + pd.offsets.MonthBegin(2),
                    "security_id": f"S{security:02d}",
                    "x1": x1,
                    "x2": x2,
                    "target_return": (x1 - 0.5) ** 2 + 0.2 * x2,
                }
            )
    panel = pd.DataFrame(rows)
    parameters = {
        "n_estimators": 50,
        "learning_rate": 0.05,
        "num_leaves": 7,
        "max_depth": 3,
        "min_child_samples": 3,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "reg_alpha": 0.0,
        "reg_lambda": 0.0,
        "early_stopping_rounds": 5,
    }

    predictions, diagnostics = walk_forward_lightgbm_raw(
        panel,
        ["x1", "x2"],
        parameters,
        train_months=8,
        validation_months=2,
        minimum_train_months=5,
    )

    assert predictions["signal_date"].nunique() == 6
    assert (predictions["training_end"] < predictions["validation_start"]).all()
    assert (predictions["validation_end"] < predictions["signal_date"]).all()
    assert (predictions["training_label_exit_end"] <= predictions["signal_date"]).all()
    assert (predictions["validation_label_exit_end"] <= predictions["signal_date"]).all()
    assert np.isfinite(predictions["prediction"]).all()
    assert diagnostics["best_iteration"].gt(0).all()
    assert set(diagnostics["feature"]) == {"x1", "x2"}


def test_lightgbm_rank_target_predictions_keep_realized_return() -> None:
    rows = []
    for month in pd.date_range("2021-01-31", periods=8, freq="ME"):
        for security in range(8):
            rows.append(
                {
                    "signal_date": month,
                    "exit_date": month + pd.offsets.MonthBegin(2),
                    "security_id": f"S{security}",
                    "x": float(security),
                    "model_target": security / 7 - 0.5,
                    "target_return": security / 100,
                }
            )
    predictions, _ = walk_forward_lightgbm_raw(
        pd.DataFrame(rows),
        ["x"],
        {
            "n_estimators": 20,
            "learning_rate": 0.05,
            "num_leaves": 7,
            "max_depth": 3,
            "min_child_samples": 3,
            "subsample": 1.0,
            "colsample_bytree": 1.0,
            "reg_alpha": 0.0,
            "reg_lambda": 0.0,
            "early_stopping_rounds": 3,
        },
        target_column="model_target",
        train_months=5,
        validation_months=1,
        minimum_train_months=3,
    )

    assert {"model_target", "target_return"} <= set(predictions)

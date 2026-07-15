import numpy as np
import pandas as pd

from pb_roe.models.linear import walk_forward_elastic_net


def test_elastic_net_walk_forward_never_trains_on_prediction_month() -> None:
    rows = []
    for month in pd.date_range("2021-01-31", periods=10, freq="ME"):
        for security in range(8):
            x1 = security / 10
            x2 = month.month / 12
            rows.append(
                {
                    "signal_date": month,
                    "exit_date": month + pd.offsets.MonthBegin(2),
                    "security_id": f"S{security}",
                    "x1": x1,
                    "x2": x2,
                    "target_return": 0.5 * x1 - 0.2 * x2 + security * 0.0001,
                }
            )
    panel = pd.DataFrame(rows)

    predictions, coefficients = walk_forward_elastic_net(
        panel,
        ["x1", "x2"],
        train_months=6,
        minimum_train_months=4,
        alpha=1e-5,
    )

    assert predictions["signal_date"].nunique() == 5
    assert (predictions["training_end"] < predictions["signal_date"]).all()
    assert (predictions["training_label_exit_end"] <= predictions["signal_date"]).all()
    assert np.isfinite(predictions["prediction"]).all()
    assert set(coefficients["feature"]) == {"x1", "x2"}

import numpy as np
import pandas as pd

from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.factors.library import compute_fundamental_factors, compute_price_factors


def test_fundamental_factor_formulas() -> None:
    frame = pd.DataFrame(
        {
            "book_equity": [50.0],
            "market_cap": [100.0],
            "ttm_net_income": [10.0],
            "ttm_operating_cash_flow": [12.0],
            "average_book_equity": [40.0],
            "average_assets": [200.0],
            "ttm_gross_profit": [30.0],
            "revenue": [120.0],
            "revenue_lag_year": [100.0],
            "net_income": [10.0],
            "net_income_lag_year": [8.0],
            "roe_history_std": [0.02],
        }
    )

    result = compute_fundamental_factors(frame).iloc[0]

    assert np.isclose(result["bp"], 0.5)
    assert np.isclose(result["ep"], 0.1)
    assert np.isclose(result["roe"], 0.25)
    assert np.isclose(result["revenue_growth"], 0.2)
    assert np.isclose(result["roe_stability"], -0.02)


def test_price_factor_library_returns_one_row_per_signal_and_security() -> None:
    bundle = fixture_bundle()
    signals = [pd.Timestamp("2022-12-30"), pd.Timestamp("2023-12-29")]

    result = compute_price_factors(bundle.prices, signals, minimum_beta_observations=20)

    assert len(result) == 10
    assert result["volatility_60d"].notna().all()
    assert result["liquidity_20d"].notna().all()
    assert result["beta_252d"].notna().all()

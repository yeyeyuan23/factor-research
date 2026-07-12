import numpy as np
import pandas as pd

from pb_roe.data.providers.akshare import (
    akshare_symbol,
    derive_ttm_roe,
    statement_metrics_to_long,
)


def _statement(dates: list[str], values: list[float], column: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "REPORT_DATE": pd.to_datetime(dates),
            "NOTICE_DATE": pd.to_datetime(dates) + pd.Timedelta(days=30),
            "UPDATE_DATE": pd.to_datetime(dates) + pd.Timedelta(days=30),
            column: values,
        }
    )


def test_akshare_symbol_uses_exchange_prefix() -> None:
    assert akshare_symbol("600519.SH") == "SH600519"
    assert akshare_symbol("000001.SZ") == "SZ000001"


def test_statement_metrics_use_update_date_as_effective_date() -> None:
    frame = _statement(["2023-12-31"], [100.0], "PARENT_NETPROFIT")
    frame.loc[0, "UPDATE_DATE"] = pd.Timestamp("2024-04-15")

    result = statement_metrics_to_long(
        frame,
        "600519.SH",
        {"net_income_cumulative": ("PARENT_NETPROFIT",)},
        "income_statement_cumulative",
    )

    assert result.loc[0, "effective_date"] == pd.Timestamp("2024-04-15")
    assert result.loc[0, "revision_date"] == pd.Timestamp("2024-04-15")


def test_ttm_roe_uses_only_components_available_by_effective_date() -> None:
    dates = ["2022-03-31", "2022-12-31", "2023-03-31"]
    profit = _statement(dates, [20.0, 100.0, 30.0], "PARENT_NETPROFIT")
    balance = _statement(dates, [200.0, 240.0, 260.0], "TOTAL_PARENT_EQUITY")
    profit.loc[2, "UPDATE_DATE"] = pd.Timestamp("2023-05-10")

    result = derive_ttm_roe(profit, balance, "600519.SH")
    row = result[result["report_period"] == pd.Timestamp("2023-03-31")].iloc[0]

    assert np.isclose(row["value"], (30.0 + 100.0 - 20.0) / 230.0)
    assert row["effective_date"] == pd.Timestamp("2023-05-10")

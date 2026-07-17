import numpy as np
import pandas as pd

from pb_roe.data.providers.akshare import (
    akshare_symbol,
    derive_ttm_per_share_metric,
    derive_ttm_roe,
    derive_ttm_roe_from_per_share,
    quarterly_report_to_long,
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


def test_quarterly_bulk_report_derives_ttm_roe() -> None:
    frames = []
    for report_period, eps, book_value in [
        ("2022-03-31", 0.2, 2.0),
        ("2022-12-31", 1.0, 2.4),
        ("2023-03-31", 0.3, 2.6),
    ]:
        report = pd.DataFrame(
            {
                "股票代码": ["600519"],
                "每股收益": [eps],
                "营业总收入-营业总收入": [100.0],
                "净利润-净利润": [10.0],
                "每股净资产": [book_value],
                "净资产收益率": [10.0],
                "每股经营现金流量": [0.5],
                "销售毛利率": [50.0],
                "营业总收入-同比增长": [5.0],
                "净利润-同比增长": [6.0],
                "最新公告日期": [pd.Timestamp(report_period) + pd.Timedelta(days=30)],
            }
        )
        frames.append(quarterly_report_to_long(report, report_period))

    result = derive_ttm_roe_from_per_share(pd.concat(frames, ignore_index=True))
    row = result[result["report_period"] == pd.Timestamp("2023-03-31")].iloc[0]

    assert np.isclose(row["value"], (0.3 + 1.0 - 0.2) / 2.3)


def test_cumulative_per_share_metric_is_converted_to_pit_ttm() -> None:
    rows = []
    for report_period, effective_date, value in (
        ("2022-03-31", "2022-04-30", 0.2),
        ("2022-12-31", "2023-04-20", 1.0),
        ("2023-03-31", "2023-05-10", 0.3),
    ):
        rows.append(
            {
                "security_id": "600519.SH",
                "report_period": report_period,
                "announce_date": effective_date,
                "revision_date": pd.NaT,
                "effective_date": effective_date,
                "metric": "eps_cumulative",
                "value": value,
                "unit": "CNY/share",
                "statement_type": "performance_report_cumulative",
                "source": "fixture",
            }
        )

    result = derive_ttm_per_share_metric(
        pd.DataFrame(rows), "eps_cumulative", "eps_ttm"
    )
    row = result[result["report_period"].eq(pd.Timestamp("2023-03-31"))].iloc[0]

    assert np.isclose(row["value"], 1.1)
    assert row["effective_date"] == pd.Timestamp("2023-05-10")


def test_raw_quarterly_report_uses_notice_date_not_later_update_date() -> None:
    report = pd.DataFrame(
        {
            "SECURITY_CODE": ["000001"],
            "NOTICE_DATE": ["2012-04-26"],
            "UPDATE_DATE": ["2013-04-24"],
            "BASIC_EPS": [0.67],
            "TOTAL_OPERATE_INCOME": [9_724_000_000.0],
            "PARENT_NETPROFIT": [3_429_000_000.0],
            "BPS": [14.99],
            "WEIGHTAVG_ROE": [4.57],
            "MGJYXJJE": [15.0],
            "XSMLL": [None],
            "YSTZ": [67.22],
            "SJLTZ": [42.74],
        }
    )

    result = quarterly_report_to_long(report, "2012-03-31")
    roe = result[result["metric"].eq("roe_reported")].iloc[0]

    assert roe["announce_date"] == pd.Timestamp("2012-04-26")
    assert roe["effective_date"] == pd.Timestamp("2012-04-26")
    assert roe["revision_date"] == pd.Timestamp("2013-04-24")
    assert np.isclose(roe["value"], 0.0457)

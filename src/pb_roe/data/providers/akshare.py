"""Cached AKShare financial statements converted to canonical PIT fundamentals."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from pb_roe.data.schema import SCHEMAS, canonical_security_id

LOGGER = logging.getLogger(__name__)


class AkShareQueryError(RuntimeError):
    """Raised when an AKShare statement request repeatedly fails."""


def akshare_symbol(security_id: str) -> str:
    symbol, exchange = canonical_security_id(security_id).split(".")
    return f"{exchange}{symbol}"


def _coalesce_numeric(frame: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for column in candidates:
        if column in frame:
            result = result.fillna(pd.to_numeric(frame[column], errors="coerce"))
    return result


def _statement_base(frame: pd.DataFrame, security_id: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "security_id",
                "report_period",
                "announce_date",
                "revision_date",
                "effective_date",
            ]
        )
    report_period = pd.to_datetime(frame["REPORT_DATE"], errors="coerce").dt.normalize()
    announce_date = pd.to_datetime(frame["NOTICE_DATE"], errors="coerce").dt.normalize()
    update_date = pd.to_datetime(frame.get("UPDATE_DATE"), errors="coerce").dt.normalize()
    effective_date = pd.concat([announce_date, update_date], axis=1).max(axis=1)
    revision_date = update_date.where(update_date > announce_date)
    return pd.DataFrame(
        {
            "security_id": canonical_security_id(security_id),
            "report_period": report_period,
            "announce_date": announce_date,
            "revision_date": revision_date,
            "effective_date": effective_date,
        }
    )


def statement_metrics_to_long(
    frame: pd.DataFrame,
    security_id: str,
    definitions: dict[str, tuple[str, ...]],
    statement_type: str,
) -> pd.DataFrame:
    """Convert selected statement columns into canonical long-form records."""

    base = _statement_base(frame, security_id)
    rows: list[pd.DataFrame] = []
    for metric, candidates in definitions.items():
        values = _coalesce_numeric(frame, candidates)
        selected = base.copy()
        selected["metric"] = metric
        selected["value"] = values
        selected["unit"] = "CNY"
        selected["statement_type"] = statement_type
        selected["source"] = "akshare_eastmoney"
        rows.append(selected.dropna(subset=["report_period", "effective_date", "value"]))
    if not rows:
        return pd.DataFrame(columns=SCHEMAS["fundamentals"])
    result = pd.concat(rows, ignore_index=True)
    return result.drop_duplicates(
        ["security_id", "report_period", "effective_date", "metric", "source"],
        keep="last",
    )


def derive_ttm_roe(profit: pd.DataFrame, balance: pd.DataFrame, security_id: str) -> pd.DataFrame:
    """Derive TTM ROE while carrying the latest component effective date."""

    profit_base = _statement_base(profit, security_id)
    profit_base["income"] = _coalesce_numeric(profit, ("PARENT_NETPROFIT", "NETPROFIT"))
    balance_base = _statement_base(balance, security_id)
    balance_base["equity"] = _coalesce_numeric(balance, ("TOTAL_PARENT_EQUITY", "TOTAL_EQUITY"))
    profit_base = (
        profit_base.dropna(subset=["report_period", "effective_date", "income"])
        .sort_values("effective_date")
        .drop_duplicates("report_period", keep="last")
        .set_index("report_period")
    )
    balance_base = (
        balance_base.dropna(subset=["report_period", "effective_date", "equity"])
        .sort_values("effective_date")
        .drop_duplicates("report_period", keep="last")
        .set_index("report_period")
    )
    rows: list[dict[str, object]] = []
    for report_period, current in profit_base.iterrows():
        prior_same = report_period - pd.DateOffset(years=1)
        if report_period.month == 12:
            ttm_income = float(current["income"])
            component_dates = [current["effective_date"]]
        else:
            prior_annual = pd.Timestamp(report_period.year - 1, 12, 31)
            if prior_same not in profit_base.index or prior_annual not in profit_base.index:
                continue
            ttm_income = float(
                current["income"]
                + profit_base.loc[prior_annual, "income"]
                - profit_base.loc[prior_same, "income"]
            )
            component_dates = [
                current["effective_date"],
                profit_base.loc[prior_annual, "effective_date"],
                profit_base.loc[prior_same, "effective_date"],
            ]
        if report_period not in balance_base.index or prior_same not in balance_base.index:
            continue
        average_equity = float(
            (balance_base.loc[report_period, "equity"] + balance_base.loc[prior_same, "equity"]) / 2
        )
        if not np.isfinite(average_equity) or abs(average_equity) <= 1e-12:
            continue
        component_dates.extend(
            [
                balance_base.loc[report_period, "effective_date"],
                balance_base.loc[prior_same, "effective_date"],
            ]
        )
        effective_date = max(pd.Timestamp(value) for value in component_dates)
        rows.append(
            {
                "security_id": canonical_security_id(security_id),
                "report_period": report_period,
                "announce_date": effective_date,
                "revision_date": pd.NaT,
                "effective_date": effective_date,
                "metric": "roe",
                "value": ttm_income / average_equity,
                "unit": "ratio",
                "statement_type": "derived_ttm",
                "source": "akshare_eastmoney_derived",
            }
        )
    return pd.DataFrame(rows, columns=SCHEMAS["fundamentals"])


class AkShareFinancialIngestor:
    """Download quarterly all-market reports and reuse local Parquet caches."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir).expanduser().resolve()

    def _quarterly_report(self, report_period: pd.Timestamp) -> pd.DataFrame:
        key = report_period.strftime("%Y%m%d")
        cache = self.cache_dir / "yjbb_raw" / f"{key}.parquet"
        if cache.is_file():
            return pd.read_parquet(cache)
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "sortColumns": "UPDATE_DATE,SECURITY_CODE",
            "sortTypes": "-1,-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_LICO_FN_CPD",
            "columns": "ALL",
            "filter": f"(REPORTDATE='{report_period:%Y-%m-%d}')",
        }

        def fetch_page(page_number: int) -> tuple[int, pd.DataFrame]:
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    response = requests.get(
                        url,
                        params={**params, "pageNumber": str(page_number)},
                        timeout=30,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if not payload.get("success") or payload.get("result") is None:
                        raise AkShareQueryError(str(payload.get("message", "empty result")))
                    result = payload["result"]
                    return int(result["pages"]), pd.DataFrame(result["data"])
                except Exception as exc:  # provider failures need bounded retries
                    last_error = exc
                    time.sleep(1 + attempt)
            raise AkShareQueryError(
                f"quarterly report page failed for {key} page {page_number}: {last_error}"
            )

        pages, first = fetch_page(1)
        frames = [first]
        for page_number in range(2, pages + 1):
            _, page = fetch_page(page_number)
            frames.append(page)
        frame = pd.concat(frames, ignore_index=True)
        cache.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(cache, index=False)
        return frame

    def fundamentals(
        self, securities: Iterable[str], start_date: object, end_date: object
    ) -> pd.DataFrame:
        start = max(
            pd.Timestamp(start_date).normalize() - pd.Timedelta(days=400),
            pd.Timestamp("2010-03-31"),
        )
        end = pd.Timestamp(end_date).normalize()
        periods = pd.period_range(start=start, end=end, freq="Q")
        report_dates = [period.end_time.normalize() for period in periods]
        security_set = {canonical_security_id(value) for value in securities}
        frames: list[pd.DataFrame] = []
        for index, report_period in enumerate(report_dates, start=1):
            report = self._quarterly_report(report_period)
            frame = quarterly_report_to_long(report, report_period)
            frames.append(frame[frame["security_id"].isin(security_set)])
            if index % 4 == 0 or index == len(report_dates):
                LOGGER.info("AKShare quarterly reports: %d/%d", index, len(report_dates))
        result = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True)
        roe = derive_ttm_roe_from_per_share(result)
        return pd.concat([result, roe], ignore_index=True).reset_index(drop=True)


def quarterly_report_to_long(report: pd.DataFrame, report_period: object) -> pd.DataFrame:
    """Convert one all-market performance report into canonical PIT metrics."""

    if report.empty:
        return pd.DataFrame(columns=SCHEMAS["fundamentals"])
    raw_eastmoney = "SECURITY_CODE" in report
    security_column = "SECURITY_CODE" if raw_eastmoney else "股票代码"
    notice_column = "NOTICE_DATE" if raw_eastmoney else "最新公告日期"
    update_column = "UPDATE_DATE" if raw_eastmoney else None
    base = pd.DataFrame(
        {
            "security_id": report[security_column].map(canonical_security_id),
            "report_period": pd.Timestamp(report_period).normalize(),
            "announce_date": pd.to_datetime(report[notice_column], errors="coerce"),
        }
    )
    update_date = (
        pd.to_datetime(report[update_column], errors="coerce")
        if update_column
        else pd.Series(pd.NaT, index=report.index)
    )
    base["revision_date"] = update_date.where(update_date > base["announce_date"])
    base["effective_date"] = base["announce_date"]
    definitions = (
        {
            "eps_cumulative": ("BASIC_EPS", "CNY/share", 1.0),
            "revenue_cumulative": ("TOTAL_OPERATE_INCOME", "CNY", 1.0),
            "net_income_cumulative": ("PARENT_NETPROFIT", "CNY", 1.0),
            "book_value_per_share": ("BPS", "CNY/share", 1.0),
            "roe_reported": ("WEIGHTAVG_ROE", "ratio", 0.01),
            "operating_cash_flow_per_share": ("MGJYXJJE", "CNY/share", 1.0),
            "gross_margin": ("XSMLL", "ratio", 0.01),
            "revenue_growth": ("YSTZ", "ratio", 0.01),
            "earnings_growth": ("SJLTZ", "ratio", 0.01),
        }
        if raw_eastmoney
        else {
            "eps_cumulative": ("每股收益", "CNY/share", 1.0),
            "revenue_cumulative": ("营业总收入-营业总收入", "CNY", 1.0),
            "net_income_cumulative": ("净利润-净利润", "CNY", 1.0),
            "book_value_per_share": ("每股净资产", "CNY/share", 1.0),
            "roe_reported": ("净资产收益率", "ratio", 0.01),
            "operating_cash_flow_per_share": ("每股经营现金流量", "CNY/share", 1.0),
            "gross_margin": ("销售毛利率", "ratio", 0.01),
            "revenue_growth": ("营业总收入-同比增长", "ratio", 0.01),
            "earnings_growth": ("净利润-同比增长", "ratio", 0.01),
        }
    )
    frames: list[pd.DataFrame] = []
    for metric, (column, unit, scale) in definitions.items():
        selected = base.copy()
        selected["metric"] = metric
        selected["value"] = pd.to_numeric(report[column], errors="coerce") * scale
        selected["unit"] = unit
        selected["statement_type"] = "performance_report_cumulative"
        selected["source"] = "akshare_eastmoney_yjbb_notice"
        frames.append(selected.dropna(subset=["effective_date", "value"]))
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        ["security_id", "report_period", "effective_date", "metric", "source"],
        keep="last",
    )


def derive_ttm_roe_from_per_share(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Derive TTM ROE from cumulative EPS and average book value per share."""

    selected = fundamentals[fundamentals["metric"].isin(["eps_cumulative", "book_value_per_share"])]
    values = selected.pivot_table(
        index=["security_id", "report_period"], columns="metric", values="value", aggfunc="last"
    )
    dates = selected.pivot_table(
        index=["security_id", "report_period"],
        columns="metric",
        values="effective_date",
        aggfunc="max",
    )
    rows: list[dict[str, object]] = []
    for security_id, stock in values.groupby(level="security_id"):
        stock = stock.droplevel("security_id").sort_index()
        stock_dates = dates.xs(security_id, level="security_id").sort_index()
        for report_period, current in stock.iterrows():
            prior_same = report_period - pd.DateOffset(years=1)
            if prior_same not in stock.index:
                continue
            if report_period.month == 12:
                ttm_eps = current.get("eps_cumulative")
                component_dates = [stock_dates.loc[report_period, "eps_cumulative"]]
            else:
                prior_annual = pd.Timestamp(report_period.year - 1, 12, 31)
                if prior_annual not in stock.index:
                    continue
                ttm_eps = (
                    current.get("eps_cumulative")
                    + stock.loc[prior_annual, "eps_cumulative"]
                    - stock.loc[prior_same, "eps_cumulative"]
                )
                component_dates = [
                    stock_dates.loc[report_period, "eps_cumulative"],
                    stock_dates.loc[prior_annual, "eps_cumulative"],
                    stock_dates.loc[prior_same, "eps_cumulative"],
                ]
            average_equity = (
                current.get("book_value_per_share") + stock.loc[prior_same, "book_value_per_share"]
            ) / 2
            component_dates.extend(
                [
                    stock_dates.loc[report_period, "book_value_per_share"],
                    stock_dates.loc[prior_same, "book_value_per_share"],
                ]
            )
            if (
                not np.isfinite(ttm_eps)
                or not np.isfinite(average_equity)
                or abs(average_equity) <= 1e-12
            ):
                continue
            effective_date = max(
                pd.Timestamp(value) for value in component_dates if pd.notna(value)
            )
            rows.append(
                {
                    "security_id": security_id,
                    "report_period": report_period,
                    "announce_date": effective_date,
                    "revision_date": pd.NaT,
                    "effective_date": effective_date,
                    "metric": "roe",
                    "value": float(ttm_eps / average_equity),
                    "unit": "ratio",
                    "statement_type": "derived_ttm_per_share",
                    "source": "akshare_eastmoney_yjbb_derived",
                }
            )
    return pd.DataFrame(rows, columns=SCHEMAS["fundamentals"])


def derive_ttm_per_share_metric(
    fundamentals: pd.DataFrame,
    source_metric: str,
    output_metric: str,
) -> pd.DataFrame:
    """Convert a cumulative per-share metric to PIT TTM observations.

    Interim reports in the Eastmoney bulk feed are year-to-date values.  A
    trailing-twelve-month value therefore combines the current cumulative
    observation with the previous annual report and subtracts the previous
    year's same-period cumulative observation.  The derived record only
    becomes usable after every component has become effective.
    """

    selected = fundamentals[fundamentals["metric"].eq(source_metric)].copy()
    if selected.empty:
        return pd.DataFrame(columns=SCHEMAS["fundamentals"])
    selected["report_period"] = pd.to_datetime(selected["report_period"]).dt.normalize()
    selected["effective_date"] = pd.to_datetime(selected["effective_date"]).dt.normalize()
    selected = selected.sort_values(
        ["security_id", "report_period", "effective_date"]
    ).drop_duplicates(["security_id", "report_period"], keep="last")
    rows: list[dict[str, object]] = []
    for security_id, stock in selected.groupby("security_id", sort=False):
        stock = stock.set_index("report_period").sort_index()
        for report_period, current in stock.iterrows():
            current_value = pd.to_numeric(current["value"], errors="coerce")
            component_dates = [current["effective_date"]]
            if report_period.month == 12:
                ttm_value = current_value
            else:
                prior_annual = pd.Timestamp(report_period.year - 1, 12, 31)
                prior_same = report_period - pd.DateOffset(years=1)
                if prior_annual not in stock.index or prior_same not in stock.index:
                    continue
                annual_value = pd.to_numeric(stock.loc[prior_annual, "value"], errors="coerce")
                prior_value = pd.to_numeric(stock.loc[prior_same, "value"], errors="coerce")
                ttm_value = current_value + annual_value - prior_value
                component_dates.extend(
                    [
                        stock.loc[prior_annual, "effective_date"],
                        stock.loc[prior_same, "effective_date"],
                    ]
                )
            if not np.isfinite(ttm_value) or any(pd.isna(value) for value in component_dates):
                continue
            effective_date = max(pd.Timestamp(value) for value in component_dates)
            rows.append(
                {
                    "security_id": security_id,
                    "report_period": report_period,
                    "announce_date": effective_date,
                    "revision_date": pd.NaT,
                    "effective_date": effective_date,
                    "metric": output_metric,
                    "value": float(ttm_value),
                    "unit": str(current["unit"]),
                    "statement_type": "derived_ttm_per_share",
                    "source": "akshare_eastmoney_yjbb_derived",
                }
            )
    return pd.DataFrame(rows, columns=SCHEMAS["fundamentals"])

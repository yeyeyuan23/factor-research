"""Cached AKShare financial statements converted to canonical PIT fundamentals."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from pathlib import Path

import akshare as ak
import numpy as np
import pandas as pd

from pb_roe.data.schema import SCHEMAS, canonical_security_id


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


def derive_ttm_roe(
    profit: pd.DataFrame, balance: pd.DataFrame, security_id: str
) -> pd.DataFrame:
    """Derive TTM ROE while carrying the latest component effective date."""

    profit_base = _statement_base(profit, security_id)
    profit_base["income"] = _coalesce_numeric(profit, ("PARENT_NETPROFIT", "NETPROFIT"))
    balance_base = _statement_base(balance, security_id)
    balance_base["equity"] = _coalesce_numeric(
        balance, ("TOTAL_PARENT_EQUITY", "TOTAL_EQUITY")
    )
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
            (balance_base.loc[report_period, "equity"] + balance_base.loc[prior_same, "equity"])
            / 2
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
    """Download each statement once per security and reuse local Parquet caches."""

    ENDPOINTS: dict[str, Callable[[str], pd.DataFrame]] = {
        "profit": ak.stock_profit_sheet_by_report_em,
        "balance": ak.stock_balance_sheet_by_report_em,
        "cashflow": ak.stock_cash_flow_sheet_by_report_em,
    }

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir).expanduser().resolve()

    def _statement(self, security_id: str, name: str) -> pd.DataFrame:
        cache = self.cache_dir / name / f"{canonical_security_id(security_id)}.parquet"
        if cache.is_file():
            return pd.read_parquet(cache)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                frame = self.ENDPOINTS[name](akshare_symbol(security_id))
                cache.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(cache, index=False)
                return frame
            except Exception as exc:  # provider failures need bounded retries
                last_error = exc
                time.sleep(1 + attempt)
        raise AkShareQueryError(f"{name} download failed for {security_id}: {last_error}")

    def fundamentals(
        self, securities: Iterable[str], start_date: object, end_date: object
    ) -> pd.DataFrame:
        start = pd.Timestamp(start_date).normalize() - pd.Timedelta(days=400)
        end = pd.Timestamp(end_date).normalize()
        frames: list[pd.DataFrame] = []
        for security_id in securities:
            profit = self._statement(security_id, "profit")
            balance = self._statement(security_id, "balance")
            cashflow = self._statement(security_id, "cashflow")
            frames.extend(
                [
                    statement_metrics_to_long(
                        profit,
                        security_id,
                        {
                            "net_income_cumulative": ("PARENT_NETPROFIT", "NETPROFIT"),
                            "revenue_cumulative": ("TOTAL_OPERATE_INCOME", "OPERATE_INCOME"),
                            "operating_cost_cumulative": ("OPERATE_COST",),
                        },
                        "income_statement_cumulative",
                    ),
                    statement_metrics_to_long(
                        balance,
                        security_id,
                        {
                            "book_equity": ("TOTAL_PARENT_EQUITY", "TOTAL_EQUITY"),
                            "total_assets": ("TOTAL_ASSETS",),
                            "share_capital": ("SHARE_CAPITAL",),
                        },
                        "balance_sheet",
                    ),
                    statement_metrics_to_long(
                        cashflow,
                        security_id,
                        {"operating_cash_flow_cumulative": ("NETCASH_OPERATE",)},
                        "cash_flow_statement_cumulative",
                    ),
                    derive_ttm_roe(profit, balance, security_id),
                ]
            )
        result = pd.concat([frame for frame in frames if not frame.empty], ignore_index=True)
        result["report_period"] = pd.to_datetime(result["report_period"])
        return result[result["report_period"].between(start, end)].reset_index(drop=True)

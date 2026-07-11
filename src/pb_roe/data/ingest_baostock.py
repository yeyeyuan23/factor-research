"""Resumable BaoStock ingestion into the canonical Parquet schema."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import baostock as bs
import numpy as np
import pandas as pd

from pb_roe.config import ResearchConfig, load_config
from pb_roe.data.bundle import DataBundle
from pb_roe.data.schema import canonical_security_id
from pb_roe.data.store import ParquetStore
from pb_roe.evaluation.panel import month_end_dates
from pb_roe.reproduction.schedule import DEFAULT_MONTH_DAYS, paper_rebalance_dates

LOGGER = logging.getLogger(__name__)


class BaoStockQueryError(RuntimeError):
    """Raised when a BaoStock query returns an error code."""


def _result_frame(result: object) -> pd.DataFrame:
    if result.error_code != "0":
        raise BaoStockQueryError(f"{result.error_code}: {result.error_msg}")
    rows: list[list[str]] = []
    while result.next():
        rows.append(result.get_row_data())
    return pd.DataFrame(rows, columns=result.fields)


def _vendor_code(security_id: str) -> str:
    symbol, exchange = canonical_security_id(security_id).split(".")
    return f"{exchange.lower()}.{symbol}"


def _quarter_for_signal(signal_date: pd.Timestamp) -> tuple[int, int]:
    if signal_date.month <= 4:
        return signal_date.year, 1
    if signal_date.month <= 8:
        return signal_date.year, 2
    if signal_date.month <= 10:
        return signal_date.year, 3
    return signal_date.year, 4


def reconstruct_membership_intervals(snapshots: dict[pd.Timestamp, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    signal_dates = sorted(snapshots)
    for index, signal_date in enumerate(signal_dates):
        snapshot = snapshots[signal_date]
        member_to = signal_dates[index + 1] if index + 1 < len(signal_dates) else pd.NaT
        count = len(snapshot)
        for row in snapshot.itertuples(index=False):
            rows.append(
                {
                    "universe_id": "CSI300",
                    "security_id": canonical_security_id(row.code),
                    "member_from": signal_date,
                    "member_to": member_to,
                    "weight": 1 / count if count else np.nan,
                    "industry": getattr(row, "industry", None),
                    "source": "baostock_snapshot",
                }
            )
    return pd.DataFrame(rows)


class BaoStockCanonicalIngestor:
    def __init__(self, config: ResearchConfig, output_dir: str | Path) -> None:
        self.config = config
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.cache_dir = self.output_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cached_query(self, cache_path: Path, query) -> pd.DataFrame:
        if cache_path.is_file():
            return pd.read_parquet(cache_path)
        frame = _result_frame(query())
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(cache_path, index=False)
        return frame

    def trading_calendar(self) -> pd.DataFrame:
        research = self.config.section("research")
        start = pd.Timestamp(research["start_date"]) - pd.Timedelta(days=14)
        end = pd.Timestamp(research["end_date"])
        raw = self._cached_query(
            self.cache_dir / "trading_calendar.parquet",
            lambda: bs.query_trade_dates(
                start_date=start.date().isoformat(), end_date=end.date().isoformat()
            ),
        )
        dates = pd.to_datetime(raw["calendar_date"])
        is_open = raw["is_trading_day"].astype(str).eq("1")
        open_dates = pd.Series(dates[is_open].to_numpy())
        previous_map = dict(zip(open_dates, open_dates.shift(1), strict=True))
        next_map = dict(zip(open_dates, open_dates.shift(-1), strict=True))
        return pd.DataFrame(
            {
                "trade_date": dates,
                "is_open": is_open.to_numpy(),
                "previous_open_date": dates.map(previous_map),
                "next_open_date": dates.map(next_map),
            }
        )

    def signal_dates(self, calendar: pd.DataFrame) -> list[pd.Timestamp]:
        research = self.config.section("research")
        open_dates = calendar.loc[calendar["is_open"], "trade_date"]
        if self.config.mode == "paper":
            return paper_rebalance_dates(
                research["start_date"],
                research["end_date"],
                open_dates,
                research.get("rebalance_month_days", DEFAULT_MONTH_DAYS),
            )
        return month_end_dates(open_dates, research["start_date"], research["end_date"])

    def membership(self, signal_dates: list[pd.Timestamp]) -> pd.DataFrame:
        snapshots: dict[pd.Timestamp, pd.DataFrame] = {}
        for signal_date in signal_dates:
            cache = self.cache_dir / "membership" / f"{signal_date.date()}.parquet"
            snapshots[signal_date] = self._cached_query(
                cache,
                lambda date=signal_date: bs.query_hs300_stocks(date=date.date().isoformat()),
            )
            LOGGER.info("membership %s: %d", signal_date.date(), len(snapshots[signal_date]))
        membership = reconstruct_membership_intervals(snapshots)
        industry = self._cached_query(
            self.cache_dir / "stock_industry.parquet", lambda: bs.query_stock_industry()
        )
        industry_map = industry.assign(
            security_id=industry["code"].map(canonical_security_id)
        ).set_index("security_id")["industry"]
        membership["industry"] = membership["security_id"].map(industry_map).fillna("Unknown")
        return membership

    def security_master(self, securities: list[str]) -> pd.DataFrame:
        raw = self._cached_query(
            self.cache_dir / "stock_basic.parquet", lambda: bs.query_stock_basic()
        )
        raw["security_id"] = raw["code"].map(canonical_security_id)
        selected = raw[raw["security_id"].isin(securities)].copy()
        exchange = selected["security_id"].str[-2:]
        return pd.DataFrame(
            {
                "security_id": selected["security_id"],
                "exchange": exchange,
                "symbol": selected["security_id"].str[:6],
                "name": selected["code_name"],
                "list_date": pd.to_datetime(selected["ipoDate"], errors="coerce"),
                "delist_date": pd.to_datetime(selected["outDate"], errors="coerce"),
                "source": "baostock",
            }
        )

    def prices(self, securities: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
        research = self.config.section("research")
        start = (pd.Timestamp(research["start_date"]) - pd.Timedelta(days=400)).date().isoformat()
        end = pd.Timestamp(research["end_date"]).date().isoformat()
        price_frames: list[pd.DataFrame] = []
        valuation_frames: list[pd.DataFrame] = []
        fields = "date,code,open,high,low,close,volume,amount,tradestatus,isST,pbMRQ"
        for index, security_id in enumerate(securities, start=1):
            cache = self.cache_dir / "prices" / f"{security_id}.parquet"
            vendor_code = _vendor_code(security_id)
            raw = self._cached_query(
                cache,
                lambda code=vendor_code: bs.query_history_k_data_plus(
                    code,
                    fields,
                    start_date=start,
                    end_date=end,
                    frequency="d",
                    adjustflag="1",
                ),
            )
            if raw.empty:
                continue
            numeric = ["open", "high", "low", "close", "volume", "amount", "pbMRQ"]
            raw[numeric] = raw[numeric].apply(pd.to_numeric, errors="coerce")
            dates = pd.to_datetime(raw["date"])
            canonical = raw["code"].map(canonical_security_id)
            price_frames.append(
                pd.DataFrame(
                    {
                        "trade_date": dates,
                        "security_id": canonical,
                        "open": raw["open"],
                        "high": raw["high"],
                        "low": raw["low"],
                        "close": raw["close"],
                        "volume": raw["volume"],
                        "amount": raw["amount"],
                        "adjustment_factor": 1.0,
                        "is_suspended": raw["tradestatus"].ne("1"),
                        "is_st": raw["isST"].eq("1"),
                        "limit_status": "unknown",
                        "source": "baostock_adj1",
                    }
                )
            )
            valuation_frames.append(
                pd.DataFrame(
                    {
                        "security_id": canonical,
                        "report_period": dates,
                        "announce_date": dates,
                        "revision_date": pd.NaT,
                        "effective_date": dates,
                        "metric": "pb",
                        "value": raw["pbMRQ"],
                        "unit": "ratio",
                        "statement_type": "market_snapshot",
                        "source": "baostock_pbMRQ",
                    }
                ).dropna(subset=["value"])
            )
            if index % 25 == 0 or index == len(securities):
                LOGGER.info("prices: %d/%d", index, len(securities))
        if not price_frames:
            raise BaoStockQueryError("No price data was returned")
        return pd.concat(price_frames, ignore_index=True), pd.concat(
            valuation_frames, ignore_index=True
        )

    def roe_fundamentals(
        self, securities: list[str], signal_dates: list[pd.Timestamp]
    ) -> pd.DataFrame:
        required_periods = sorted({_quarter_for_signal(date) for date in signal_dates})
        frames: list[pd.DataFrame] = []
        for index, security_id in enumerate(securities, start=1):
            stock_frames: list[pd.DataFrame] = []
            vendor_code = _vendor_code(security_id)
            for year, quarter in required_periods:
                cache = self.cache_dir / "profit" / security_id / f"{year}Q{quarter}.parquet"
                raw = self._cached_query(
                    cache,
                    lambda code=vendor_code, y=year, q=quarter: bs.query_profit_data(
                        code=code, year=y, quarter=q
                    ),
                )
                if not raw.empty:
                    stock_frames.append(raw)
            if stock_frames:
                raw = pd.concat(stock_frames, ignore_index=True).drop_duplicates()
                frames.append(
                    pd.DataFrame(
                        {
                            "security_id": raw["code"].map(canonical_security_id),
                            "report_period": pd.to_datetime(raw["statDate"]),
                            "announce_date": pd.to_datetime(raw["pubDate"]),
                            "revision_date": pd.NaT,
                            "effective_date": pd.to_datetime(raw["pubDate"]),
                            "metric": "roe",
                            "value": pd.to_numeric(raw["roeAvg"], errors="coerce"),
                            "unit": "ratio",
                            "statement_type": "consolidated_cumulative",
                            "source": "baostock_profit",
                        }
                    ).dropna(subset=["effective_date", "value"])
                )
            if index % 25 == 0 or index == len(securities):
                LOGGER.info("profit: %d/%d", index, len(securities))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def ingest(self, max_securities: int | None = None) -> DataBundle:
        calendar = self.trading_calendar()
        signals = self.signal_dates(calendar)
        membership = self.membership(signals)
        securities = sorted(membership["security_id"].unique())
        if max_securities:
            final_members = sorted(
                membership.loc[membership["member_to"].isna(), "security_id"].unique()
            )
            securities = final_members[:max_securities]
            membership = membership[membership["security_id"].isin(securities)].copy()
        master = self.security_master(securities)
        prices, pb = self.prices(securities)
        roe = self.roe_fundamentals(securities, signals)
        if roe.empty:
            raise BaoStockQueryError("No ROE fundamentals were returned")
        fundamentals = pd.concat([pb, roe], ignore_index=True)
        bundle = DataBundle(master, calendar, membership, prices, fundamentals)
        canonical = self.output_dir / "canonical"
        ParquetStore(canonical, immutable=False).write_bundle(bundle, overwrite=True)
        metadata = {
            "config_fingerprint": self.config.fingerprint,
            "signal_dates": [date.date().isoformat() for date in signals],
            "securities": len(securities),
            "canonical": str(canonical),
            "limitations": [
                "industry uses the BaoStock industry snapshot available at ingestion time",
                "CSI300 historical weights are unavailable; "
                "membership weights are equal-weight proxies",
                "prices use BaoStock adjustflag=1 and adjustment_factor is stored as 1.0",
            ],
        }
        (self.output_dir / "ingestion_run.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return bundle


def ingest_from_cli(config_path: str, output_dir: str, max_securities: int | None) -> int:
    config = load_config(config_path)
    login = bs.login()
    if login.error_code != "0":
        raise BaoStockQueryError(f"BaoStock login failed: {login.error_msg}")
    try:
        bundle = BaoStockCanonicalIngestor(config, output_dir).ingest(max_securities)
    finally:
        bs.logout()
    summary = {name: len(frame) for name, frame in bundle.tables().items()}
    print(json.dumps({"output_dir": str(Path(output_dir).resolve()), "rows": summary}, indent=2))
    return 0

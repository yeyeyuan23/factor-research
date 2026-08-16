"""Resumable BaoStock ingestion into the canonical Parquet schema."""

from __future__ import annotations

import json
import logging
import time
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
PRICE_FIELDS = "date,code,open,high,low,close,volume,amount,tradestatus,isST,pbMRQ"


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
    if signal_date.month <= 5:
        return signal_date.year, 1
    if signal_date.month <= 9:
        return signal_date.year, 2
    if signal_date.month <= 11:
        return signal_date.year, 3
    return signal_date.year, 4


def _download_price_jobs(jobs: list[tuple[str, str, str, str]]) -> None:
    """Download sequentially in one BaoStock session and preserve per-stock caches."""

    def login_session() -> None:
        login = bs.login()
        if login.error_code != "0":
            raise BaoStockQueryError(login.error_msg)

    login_session()
    try:
        for index, (security_id, start, end, cache_text) in enumerate(jobs, start=1):
            cache = Path(cache_text)
            if not cache.is_file():
                last_error: Exception | None = None
                for attempt in range(3):
                    try:
                        raw = _result_frame(
                            bs.query_history_k_data_plus(
                                _vendor_code(security_id),
                                PRICE_FIELDS,
                                start_date=start,
                                end_date=end,
                                frequency="d",
                                adjustflag="1",
                            )
                        )
                        cache.parent.mkdir(parents=True, exist_ok=True)
                        raw.to_parquet(cache, index=False)
                        break
                    except Exception as exc:  # provider errors need bounded retries
                        last_error = exc
                        bs.logout()
                        time.sleep(1 + attempt)
                        login_session()
                else:
                    raise BaoStockQueryError(
                        f"price download failed for {security_id}: {last_error}"
                    )
            if index % 25 == 0 or index == len(jobs):
                LOGGER.info("price downloads: %d/%d", index, len(jobs))
    finally:
        bs.logout()


def _download_profit_job(job: tuple[str, tuple[tuple[int, int], ...], str]) -> tuple[str, int]:
    security_id, periods, cache_root_text = job
    cache_root = Path(cache_root_text)
    missing = [
        (year, quarter)
        for year, quarter in periods
        if not (cache_root / security_id / f"{year}Q{quarter}.parquet").is_file()
    ]
    if not missing:
        return security_id, 0
    login = bs.login()
    if login.error_code != "0":
        raise BaoStockQueryError(login.error_msg)
    completed = 0
    try:
        for year, quarter in missing:
            cache = cache_root / security_id / f"{year}Q{quarter}.parquet"
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    raw = _result_frame(
                        bs.query_profit_data(
                            code=_vendor_code(security_id), year=year, quarter=quarter
                        )
                    )
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    raw.to_parquet(cache, index=False)
                    completed += 1
                    break
                except Exception as exc:  # network provider errors need bounded retries
                    last_error = exc
                    time.sleep(1 + attempt)
            else:
                raise BaoStockQueryError(
                    f"profit download failed for {security_id} {year}Q{quarter}: {last_error}"
                )
    finally:
        bs.logout()
    return security_id, completed


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
        self.workers = int(config.section("data").get("download_workers", 1))
        if self.workers != 1:
            raise ValueError(
                "BaoStock sessions are not concurrency-safe; download_workers must be 1"
            )

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
                str(research.get("non_trading_day", "previous")),
            )
        return month_end_dates(open_dates, research["start_date"], research["end_date"])

    def membership(self, signal_dates: list[pd.Timestamp]) -> pd.DataFrame:
        snapshots: dict[pd.Timestamp, pd.DataFrame] = {}
        early_dates = [date for date in signal_dates if date.year == 2005]
        early_snapshots: dict[pd.Timestamp, pd.DataFrame] = {}
        if early_dates:
            from pb_roe.data.providers.early_paper import EarlyPaperSource

            early_snapshots = EarlyPaperSource(self.cache_dir / "early_fill").membership_snapshots(
                early_dates
            )
        for signal_date in signal_dates:
            if signal_date in early_snapshots:
                snapshots[signal_date] = early_snapshots[signal_date]
                LOGGER.info("membership %s: %d", signal_date.date(), len(snapshots[signal_date]))
                continue
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
        buffer_days = 14 if self.config.mode == "paper" else 400
        start = (
            (pd.Timestamp(research["start_date"]) - pd.Timedelta(days=buffer_days))
            .date()
            .isoformat()
        )
        end = pd.Timestamp(research["end_date"]).date().isoformat()
        price_cache = self.cache_dir / "prices"
        early_fill = (
            self.config.section("data").get("providers", {}).get("fundamentals")
            == "baostock_early_fill"
        )
        early_price_cache = self.cache_dir / "early_fill" / "prices"
        if early_fill:
            early_jobs: list[tuple[str, str, str, str]] = []
            for security_id in securities:
                base = price_cache / f"{security_id}.parquet"
                if base.is_file():
                    raw = pd.read_parquet(base, columns=["date"])
                    first_date = pd.to_datetime(raw["date"], errors="coerce").min()
                    early_end = first_date - pd.Timedelta(days=1)
                else:
                    early_end = pd.Timestamp("2006-12-31")
                if pd.notna(early_end) and early_end >= pd.Timestamp(start):
                    early_jobs.append(
                        (
                            security_id,
                            start,
                            early_end.date().isoformat(),
                            str(early_price_cache / f"{security_id}.parquet"),
                        )
                    )
            _download_price_jobs(early_jobs)
        else:
            jobs = [
                (security_id, start, end, str(price_cache / f"{security_id}.parquet"))
                for security_id in securities
            ]
            _download_price_jobs(jobs)

        price_frames: list[pd.DataFrame] = []
        valuation_frames: list[pd.DataFrame] = []
        for index, security_id in enumerate(securities, start=1):
            paths = [
                path
                for path in (
                    early_price_cache / f"{security_id}.parquet",
                    price_cache / f"{security_id}.parquet",
                )
                if path.is_file()
            ]
            raw = pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True)
            raw = raw.drop_duplicates(["date", "code"], keep="last")
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
            if index % 100 == 0 or index == len(securities):
                LOGGER.info("price transforms: %d/%d", index, len(securities))
        if not price_frames:
            raise BaoStockQueryError("No price data was returned")
        return pd.concat(price_frames, ignore_index=True), pd.concat(
            valuation_frames, ignore_index=True
        )

    def roe_fundamentals(
        self, securities: list[str], signal_dates: list[pd.Timestamp]
    ) -> pd.DataFrame:
        required_periods = tuple(sorted({_quarter_for_signal(date) for date in signal_dates}))
        if (
            self.config.section("data").get("providers", {}).get("fundamentals")
            == "baostock_early_fill"
        ):
            required_periods = tuple(period for period in required_periods if period[0] >= 2007)
        profit_cache = self.cache_dir / "profit"
        jobs = [(security_id, required_periods, str(profit_cache)) for security_id in securities]
        completed = 0
        for job in jobs:
            _download_profit_job(job)
            completed += 1
            if completed % 25 == 0 or completed == len(jobs):
                LOGGER.info("profit downloads: %d/%d", completed, len(jobs))

        frames: list[pd.DataFrame] = []
        for index, security_id in enumerate(securities, start=1):
            stock_frames: list[pd.DataFrame] = []
            for year, quarter in required_periods:
                cache = profit_cache / security_id / f"{year}Q{quarter}.parquet"
                raw = pd.read_parquet(cache)
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
            if index % 100 == 0 or index == len(securities):
                LOGGER.info("profit transforms: %d/%d", index, len(securities))
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
        fundamental_provider = str(
            self.config.section("data").get("providers", {}).get("fundamentals", "")
        )
        if fundamental_provider == "baostock":
            financials = self.roe_fundamentals(securities, signals)
        elif fundamental_provider == "baostock_early_fill":
            from pb_roe.data.providers.early_paper import EarlyPaperSource

            cached_securities = [
                security_id
                for security_id in securities
                if (self.cache_dir / "profit" / security_id).is_dir()
            ]
            financials = self.roe_fundamentals(cached_securities, signals)
            early_periods = sorted(
                {
                    pd.Timestamp(year, quarter * 3, 1) + pd.offsets.MonthEnd(0)
                    for year, quarter in (_quarter_for_signal(date) for date in signals)
                    if year <= 2006
                }
            )
            early_securities = sorted(
                membership.loc[
                    pd.to_datetime(membership["member_from"]).dt.year.le(2006),
                    "security_id",
                ].unique()
            )
            early = EarlyPaperSource(self.cache_dir / "early_fill").roe_fundamentals(
                early_securities, early_periods
            )
            existing_keys = (
                set(zip(financials["security_id"], financials["report_period"], strict=True))
                if not financials.empty
                else set()
            )
            early_keys = list(zip(early["security_id"], early["report_period"], strict=True))
            early = early[[key not in existing_keys for key in early_keys]]
            financials = pd.concat([financials, early], ignore_index=True)
        elif fundamental_provider == "akshare":
            from pb_roe.data.providers.akshare import AkShareFinancialIngestor

            research = self.config.section("research")
            financials = AkShareFinancialIngestor(self.cache_dir / "akshare").fundamentals(
                securities, research["start_date"], research["end_date"]
            )
        else:
            raise ValueError(f"Unsupported fundamentals provider: {fundamental_provider}")
        if financials.empty:
            raise BaoStockQueryError("No financial fundamentals were returned")
        fundamentals = pd.concat([pb, financials], ignore_index=True)
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
                f"fundamentals provider: {fundamental_provider}",
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
    bundle = BaoStockCanonicalIngestor(config, output_dir).ingest(max_securities)
    summary = {name: len(frame) for name, frame in bundle.tables().items()}
    print(json.dumps({"output_dir": str(Path(output_dir).resolve()), "rows": summary}, indent=2))
    return 0

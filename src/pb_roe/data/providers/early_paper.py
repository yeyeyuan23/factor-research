"""Incremental 2005-2006 sources for the original-paper reproduction gap."""

from __future__ import annotations

import logging
import re
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from pb_roe.data.schema import SCHEMAS, canonical_security_id

LOGGER = logging.getLogger(__name__)

INITIAL_MEMBERS_URL = "https://finance.sina.com.cn/stock/y/20050405/01171486656.shtml"
JULY_ADJUSTMENT_URL = "https://finance.sina.com.cn/roll/20050622/0544143260.shtml"
CODE_PATTERN = re.compile(r"(?<!\d)(?:000|001|002|600)\d{3}(?!\d)")


def _article_text(html: bytes) -> str:
    soup = BeautifulSoup(html.decode("gb18030", errors="replace"), "html.parser")
    article = soup.find(id="article") or soup.find(id="zoom")
    if article is None:
        raise ValueError("Sina archive page has no article body")
    return article.get_text(" ", strip=True)


def parse_initial_csi300_members(html: bytes) -> list[str]:
    codes = list(dict.fromkeys(CODE_PATTERN.findall(_article_text(html))))
    codes = [code for code in codes if code != "000300"]
    if len(codes) != 300:
        raise ValueError(f"Expected 300 initial CSI300 members, found {len(codes)}")
    return [canonical_security_id(code) for code in codes]


def parse_july_2005_adjustment(html: bytes) -> tuple[list[str], list[str]]:
    codes = CODE_PATTERN.findall(_article_text(html))
    if len(codes) != 28:
        raise ValueError(f"Expected 14 adjustment pairs, found {len(codes)} codes")
    removed = [canonical_security_id(code) for code in codes[::2]]
    added = [canonical_security_id(code) for code in codes[1::2]]
    return removed, added


def apply_membership_adjustment(
    initial: list[str], removed: list[str], added: list[str]
) -> list[str]:
    members = set(initial)
    missing = sorted(set(removed) - members)
    if missing:
        raise ValueError(f"Adjustment removes non-members: {missing}")
    members.difference_update(removed)
    members.update(added)
    if len(members) != 300:
        raise ValueError(f"Adjusted CSI300 membership has {len(members)} securities")
    return sorted(members)


class EarlyPaperSource:
    """Cache and transform only the missing 2005-2006 paper data."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir).expanduser().resolve()

    def _cached_html(self, name: str, url: str) -> bytes:
        path = self.cache_dir / "membership" / name
        if not path.is_file():
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        return path.read_bytes()

    def membership_snapshots(
        self, signal_dates: list[pd.Timestamp]
    ) -> dict[pd.Timestamp, pd.DataFrame]:
        initial = parse_initial_csi300_members(
            self._cached_html("csi300_initial_20050405.html", INITIAL_MEMBERS_URL)
        )
        removed, added = parse_july_2005_adjustment(
            self._cached_html("csi300_adjustment_20050701.html", JULY_ADJUSTMENT_URL)
        )
        adjusted = apply_membership_adjustment(initial, removed, added)
        snapshots: dict[pd.Timestamp, pd.DataFrame] = {}
        for signal_date in signal_dates:
            members = initial if signal_date < pd.Timestamp("2005-07-01") else adjusted
            snapshots[signal_date] = pd.DataFrame(
                {
                    "code": [
                        f"{security_id[-2:].lower()}.{security_id[:6]}"
                        for security_id in members
                    ],
                    "code_name": "",
                }
            )
        return snapshots

    def _sina_year(self, security_id: str, year: int) -> pd.DataFrame:
        cache = self.cache_dir / "fundamentals_sina" / security_id / f"{year}.parquet"
        if cache.is_file():
            return pd.read_parquet(cache)
        symbol = canonical_security_id(security_id)[:6]
        url = (
            "https://money.finance.sina.com.cn/corp/go.php/"
            f"vFD_FinancialGuideLine/stockid/{symbol}/ctrl/{year}/displaytype/4.phtml"
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                break
            except Exception as exc:
                last_error = exc
                time.sleep(1 + attempt)
        else:
            raise RuntimeError(
                f"Sina financial download failed for {security_id} {year}: {last_error}"
            )
        tables = pd.read_html(StringIO(response.text))
        empty = pd.DataFrame(columns=["report_period", "净资产收益率(%)"])
        if len(tables) <= 12 or tables[12].empty:
            cache.parent.mkdir(parents=True, exist_ok=True)
            empty.to_parquet(cache, index=False)
            return empty
        table = tables[12].iloc[:, :-1]
        table.columns = table.iloc[0, :]
        table = table.iloc[1:, :]
        labels = table.iloc[:, 0].astype(str)
        sections = [
            "每股指标",
            "盈利能力",
            "成长能力",
            "营运能力",
            "偿债及资本结构",
            "现金流量",
            "其他指标",
        ]
        combined = pd.DataFrame()
        for index, section in enumerate(sections):
            starts = table.index[labels.str.find(section) == 0]
            if starts.empty:
                cache.parent.mkdir(parents=True, exist_ok=True)
                empty.to_parquet(cache, index=False)
                return empty
            start = starts[0]
            if index == len(sections) - 1:
                selected = table.loc[start:].T
            else:
                ends = table.index[labels.str.find(sections[index + 1]) == 0]
                if ends.empty:
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    empty.to_parquet(cache, index=False)
                    return empty
                end = ends[0]
                selected = table.loc[start : end - 1].T
            selected = selected.reset_index(drop=True)
            combined = pd.concat([combined, selected], axis=1)
        combined.columns = combined.iloc[0, :].tolist()
        combined = combined.iloc[1:, :]
        combined.index = table.columns.tolist()[1:]
        combined = combined.dropna(how="all").reset_index(names="report_period")
        combined["report_period"] = pd.to_datetime(
            combined["report_period"], errors="coerce"
        )
        cache.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(cache, index=False)
        return combined

    def roe_fundamentals(
        self, securities: list[str], report_periods: list[pd.Timestamp]
    ) -> pd.DataFrame:
        periods = pd.DatetimeIndex(report_periods).normalize()
        rows: list[pd.DataFrame] = []
        for index, security_id in enumerate(securities, start=1):
            sina = pd.concat(
                [self._sina_year(security_id, year) for year in sorted(periods.year.unique())],
                ignore_index=True,
            )
            if "report_period" not in sina or "净资产收益率(%)" not in sina:
                continue
            sina["report_period"] = pd.to_datetime(
                sina["report_period"], errors="coerce"
            ).dt.normalize()
            sina = sina[sina["report_period"].isin(periods)].copy()
            if sina.empty:
                continue
            roe = pd.to_numeric(sina["净资产收益率(%)"], errors="coerce")
            deadline = sina["report_period"].map(
                lambda date: pd.Timestamp(
                    date.year,
                    {3: 4, 6: 8, 9: 10}[date.month],
                    {3: 30, 6: 31, 9: 31}[date.month],
                )
            )
            rows.append(
                pd.DataFrame(
                    {
                        "security_id": canonical_security_id(security_id),
                        "report_period": sina["report_period"],
                        "announce_date": deadline,
                        "revision_date": pd.NaT,
                        "effective_date": deadline,
                        "metric": "roe",
                        "value": roe / 100,
                        "unit": "ratio",
                        "statement_type": "consolidated_cumulative",
                        "source": "sina_roe_paper_deadline",
                    }
                ).dropna(subset=["effective_date", "value"])
            )
            if index % 25 == 0 or index == len(securities):
                LOGGER.info("early Sina ROE transforms: %d/%d", index, len(securities))
        return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
            columns=SCHEMAS["fundamentals"]
        )

"""Lazy BaoStock adapter for prices and CSI 300 snapshots."""

from __future__ import annotations

from datetime import date

import pandas as pd

from pb_roe.data.providers.base import ProviderError
from pb_roe.data.schema import canonical_security_id


class BaoStockProvider:
    name = "baostock"

    @staticmethod
    def _module():
        try:
            import baostock as bs
        except ImportError as exc:
            raise ProviderError("Install the 'data' extra to use BaoStock") from exc
        return bs

    def fetch_prices(self, security_id: str, start_date: date, end_date: date) -> pd.DataFrame:
        bs = self._module()
        canonical = canonical_security_id(security_id)
        symbol, exchange = canonical.split(".")
        login = bs.login()
        if login.error_code != "0":
            raise ProviderError(f"BaoStock login failed: {login.error_msg}")
        try:
            query = bs.query_history_k_data_plus(
                f"{exchange.lower()}.{symbol}",
                "date,code,open,high,low,close,volume,amount,adjustflag,tradestatus,isST",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                frequency="d",
                adjustflag="3",
            )
            if query.error_code != "0":
                raise ProviderError(f"BaoStock price query failed: {query.error_msg}")
            rows: list[list[str]] = []
            while query.next():
                rows.append(query.get_row_data())
        finally:
            bs.logout()
        raw = pd.DataFrame(rows, columns=query.fields)
        if raw.empty:
            return raw
        numeric = ["open", "high", "low", "close", "volume", "amount"]
        raw[numeric] = raw[numeric].apply(pd.to_numeric, errors="coerce")
        return pd.DataFrame(
            {
                "trade_date": pd.to_datetime(raw["date"]),
                "security_id": canonical,
                "open": raw["open"],
                "high": raw["high"],
                "low": raw["low"],
                "close": raw["close"],
                "volume": raw["volume"],
                "amount": raw["amount"],
                "adjustment_factor": pd.NA,
                "is_suspended": raw["tradestatus"] != "1",
                "is_st": raw["isST"] == "1",
                "limit_status": "unknown",
                "source": self.name,
            }
        )

    def fetch_membership(self, universe_id: str, as_of: date) -> pd.DataFrame:
        if universe_id != "CSI300":
            raise ProviderError(f"BaoStock adapter only supports CSI300, got {universe_id}")
        bs = self._module()
        login = bs.login()
        if login.error_code != "0":
            raise ProviderError(f"BaoStock login failed: {login.error_msg}")
        try:
            query = bs.query_hs300_stocks(date=as_of.isoformat())
            if query.error_code != "0":
                raise ProviderError(f"BaoStock membership query failed: {query.error_msg}")
            rows: list[list[str]] = []
            while query.next():
                rows.append(query.get_row_data())
        finally:
            bs.logout()
        raw = pd.DataFrame(rows, columns=query.fields)
        if raw.empty:
            return raw
        code_column = "code" if "code" in raw else raw.columns[-2]
        return pd.DataFrame(
            {
                "universe_id": universe_id,
                "security_id": raw[code_column].map(canonical_security_id),
                "snapshot_date": pd.Timestamp(as_of),
                "source": self.name,
            }
        )

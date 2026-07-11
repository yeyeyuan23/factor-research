"""Modern monthly factor panel and next-open return labels."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from pb_roe.data.bundle import DataBundle
from pb_roe.data.schema import require_columns
from pb_roe.reproduction.factors import build_paper_factor_panel


def month_end_dates(
    open_dates: Iterable[object], start_date: object, end_date: object
) -> list[pd.Timestamp]:
    dates = pd.Series(pd.to_datetime(list(open_dates))).dropna().sort_values()
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    dates = dates[(dates >= start) & (dates <= end)]
    if dates.empty:
        return []
    return dates.groupby(dates.dt.to_period("M")).max().tolist()


def next_open_forward_returns(
    signal_dates: list[object],
    prices: pd.DataFrame,
    execution_price: str = "open",
) -> pd.DataFrame:
    require_columns(
        prices,
        ("trade_date", "security_id", execution_price, "is_suspended"),
        "prices",
    )
    price_frame = prices.copy()
    price_frame["trade_date"] = pd.to_datetime(price_frame["trade_date"]).dt.normalize()
    all_dates = pd.DatetimeIndex(price_frame["trade_date"].unique()).sort_values()
    signals = sorted(pd.Timestamp(value).normalize() for value in signal_dates)
    execution_dates: dict[pd.Timestamp, pd.Timestamp] = {}
    for signal_date in signals:
        candidates = all_dates[all_dates > signal_date]
        if not candidates.empty:
            execution_dates[signal_date] = pd.Timestamp(candidates[0])

    tradable = price_frame.loc[~price_frame["is_suspended"].fillna(False)]
    lookup = tradable.set_index(["trade_date", "security_id"])[execution_price].sort_index()
    securities = sorted(price_frame["security_id"].unique())
    rows: list[dict[str, object]] = []
    for index, signal_date in enumerate(signals[:-1]):
        next_signal = signals[index + 1]
        if signal_date not in execution_dates or next_signal not in execution_dates:
            continue
        entry_date = execution_dates[signal_date]
        exit_date = execution_dates[next_signal]
        entry_index = pd.MultiIndex.from_product([[entry_date], securities])
        exit_index = pd.MultiIndex.from_product([[exit_date], securities])
        entry = lookup.reindex(entry_index).to_numpy(dtype=float)
        exit_values = lookup.reindex(exit_index).to_numpy(dtype=float)
        returns = np.where(np.isfinite(entry) & (entry > 0), exit_values / entry - 1, np.nan)
        rows.extend(
            {
                "signal_date": signal_date,
                "security_id": security_id,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "forward_return": value,
            }
            for security_id, value in zip(securities, returns, strict=True)
        )
    return pd.DataFrame(rows)


def build_modern_panel(bundle: DataBundle, start_date: object, end_date: object) -> pd.DataFrame:
    calendar = bundle.trading_calendar.loc[bundle.trading_calendar["is_open"], "trade_date"]
    signals = month_end_dates(calendar, start_date, end_date)
    if len(signals) < 2:
        raise ValueError("Modern evaluation needs at least two monthly signal dates")
    factors = build_paper_factor_panel(
        signals,
        bundle.universe_membership,
        bundle.fundamentals,
    )
    factors["bp"] = np.where(factors["pb"] > 0, 1 / factors["pb"], np.nan)
    forward = next_open_forward_returns(signals, bundle.prices)
    return factors.merge(
        forward,
        on=["signal_date", "security_id"],
        how="inner",
        validate="one_to_one",
    )

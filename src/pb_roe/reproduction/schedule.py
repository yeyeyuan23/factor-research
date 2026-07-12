"""Original paper rebalance schedule construction."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

DEFAULT_MONTH_DAYS = ("04-30", "08-31", "10-31")


def previous_trading_day(target: object, open_dates: Iterable[object]) -> pd.Timestamp:
    date = pd.Timestamp(target).normalize()
    calendar = pd.DatetimeIndex(pd.to_datetime(list(open_dates))).normalize().sort_values()
    candidates = calendar[calendar <= date]
    if candidates.empty:
        raise ValueError(f"No trading date on or before {date.date()}")
    return pd.Timestamp(candidates[-1])


def next_trading_day(target: object, open_dates: Iterable[object]) -> pd.Timestamp:
    date = pd.Timestamp(target).normalize()
    calendar = pd.DatetimeIndex(pd.to_datetime(list(open_dates))).normalize().sort_values()
    candidates = calendar[calendar >= date]
    if candidates.empty:
        raise ValueError(f"No trading date on or after {date.date()}")
    return pd.Timestamp(candidates[0])


def paper_rebalance_dates(
    start_date: object,
    end_date: object,
    open_dates: Iterable[object],
    month_days: Iterable[str] = DEFAULT_MONTH_DAYS,
    non_trading_day: str = "previous",
) -> list[pd.Timestamp]:
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    dates: set[pd.Timestamp] = set()
    for year in range(start.year, end.year + 1):
        for month_day in month_days:
            target = pd.Timestamp(f"{year}-{month_day}")
            if start <= target <= end:
                if non_trading_day == "previous":
                    dates.add(previous_trading_day(target, open_dates))
                elif non_trading_day == "next":
                    dates.add(next_trading_day(target, open_dates))
                else:
                    raise ValueError(f"Unsupported non-trading-day rule: {non_trading_day}")
    return sorted(dates)

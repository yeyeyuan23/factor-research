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
    max_execution_delay_days: int = 5,
) -> pd.DataFrame:
    require_columns(
        prices,
        ("trade_date", "security_id", execution_price, "is_suspended"),
        "prices",
    )
    price_frame = prices.copy()
    price_frame["trade_date"] = pd.to_datetime(price_frame["trade_date"]).dt.normalize()
    price_frame = price_frame.sort_values(["security_id", "trade_date"])
    price_frame["previous_close"] = price_frame.groupby("security_id")["close"].shift()
    gap = price_frame["open"] / price_frame["previous_close"] - 1
    one_price = (
        price_frame[["open", "high", "low", "close"]].max(axis=1)
        - price_frame[["open", "high", "low", "close"]].min(axis=1)
    ).abs().le(1e-10)
    limit_threshold = np.where(price_frame.get("is_st", False), 0.045, 0.095)
    price_frame["is_locked_limit"] = one_price & gap.abs().ge(limit_threshold)
    all_dates = pd.DatetimeIndex(price_frame["trade_date"].unique()).sort_values()
    signals = sorted(pd.Timestamp(value).normalize() for value in signal_dates)
    execution_dates: dict[pd.Timestamp, pd.Timestamp] = {}
    for signal_date in signals:
        candidates = all_dates[all_dates > signal_date]
        if not candidates.empty:
            execution_dates[signal_date] = pd.Timestamp(candidates[0])

    tradable = price_frame.loc[
        ~price_frame["is_suspended"].fillna(False) & ~price_frame["is_locked_limit"]
    ]
    locked_lookup = price_frame.set_index(["trade_date", "security_id"])[
        "is_locked_limit"
    ].sort_index()
    securities = sorted(price_frame["security_id"].unique())

    def execution_snapshot(target_date: pd.Timestamp) -> pd.DataFrame:
        candidate_dates = all_dates[all_dates >= target_date][:max_execution_delay_days]
        candidates = tradable[tradable["trade_date"].isin(candidate_dates)].copy()
        candidates["execution_delay_days"] = candidates["trade_date"].map(
            {date: index for index, date in enumerate(candidate_dates)}
        )
        first = candidates.sort_values(["trade_date", "security_id"]).drop_duplicates(
            "security_id", keep="first"
        )
        return first.set_index("security_id").reindex(securities)

    rows: list[dict[str, object]] = []
    for index, signal_date in enumerate(signals[:-1]):
        next_signal = signals[index + 1]
        if signal_date not in execution_dates or next_signal not in execution_dates:
            continue
        intended_entry_date = execution_dates[signal_date]
        intended_exit_date = execution_dates[next_signal]
        entry_snapshot = execution_snapshot(intended_entry_date)
        exit_snapshot = execution_snapshot(intended_exit_date)
        entry = entry_snapshot[execution_price].to_numpy(dtype=float)
        exit_values = exit_snapshot[execution_price].to_numpy(dtype=float)
        intended_entry_index = pd.MultiIndex.from_product(
            [[intended_entry_date], securities]
        )
        entry_locked = (
            locked_lookup.reindex(intended_entry_index).fillna(False).to_numpy(dtype=bool)
        )
        returns = np.where(
            np.isfinite(entry) & (entry > 0) & np.isfinite(exit_values),
            exit_values / entry - 1,
            np.nan,
        )
        rows.extend(
            {
                "signal_date": signal_date,
                "security_id": security_id,
                "entry_date": entry_date,
                "exit_date": exit_date,
                "entry_delay_days": entry_delay,
                "exit_delay_days": exit_delay,
                "forward_return": value,
                "entry_locked_limit": locked,
            }
            for security_id, entry_date, exit_date, entry_delay, exit_delay, value, locked in zip(
                securities,
                entry_snapshot["trade_date"],
                exit_snapshot["trade_date"],
                entry_snapshot["execution_delay_days"],
                exit_snapshot["execution_delay_days"],
                returns,
                entry_locked,
                strict=True,
            )
        )
    return pd.DataFrame(rows)


def build_modern_panel(
    bundle: DataBundle,
    start_date: object,
    end_date: object,
    minimum_listing_days: int = 0,
) -> pd.DataFrame:
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
    prices = bundle.prices.copy()
    prices["trade_date"] = pd.to_datetime(prices["trade_date"]).dt.normalize()
    prices = prices.sort_values(["security_id", "trade_date"])
    prices["listing_days"] = prices.groupby("security_id").cumcount() + 1
    prices["adv_20d"] = prices.groupby("security_id")["amount"].transform(
        lambda values: values.rolling(20, min_periods=10).mean()
    )
    status_columns = [
        column
        for column in (
            "trade_date",
            "security_id",
            "is_suspended",
            "is_st",
            "listing_days",
            "adv_20d",
        )
        if column in prices
    ]
    signal_status = prices.loc[prices["trade_date"].isin(signals), status_columns].rename(
        columns={"trade_date": "signal_date"}
    )
    factors = factors.merge(
        signal_status,
        on=["signal_date", "security_id"],
        how="left",
        validate="one_to_one",
    )
    eligible = factors["listing_days"].ge(minimum_listing_days)
    if "is_suspended" in factors:
        eligible &= ~factors["is_suspended"].fillna(True)
    if "is_st" in factors:
        eligible &= ~factors["is_st"].fillna(True)
    factors = factors.loc[eligible].copy()
    forward = next_open_forward_returns(signals, bundle.prices)
    return factors.merge(
        forward,
        on=["signal_date", "security_id"],
        how="inner",
        validate="one_to_one",
    )

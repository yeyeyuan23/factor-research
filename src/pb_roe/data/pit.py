"""Point-in-time selection primitives."""

from __future__ import annotations

import pandas as pd

from pb_roe.data.schema import require_columns


def active_members(
    membership: pd.DataFrame,
    signal_date: str | pd.Timestamp,
    universe_id: str = "CSI300",
) -> pd.DataFrame:
    require_columns(
        membership,
        ("universe_id", "security_id", "member_from", "member_to"),
        "universe_membership",
    )
    date = pd.Timestamp(signal_date).normalize()
    members = membership.copy()
    members["member_from"] = pd.to_datetime(members["member_from"])
    members["member_to"] = pd.to_datetime(members["member_to"])
    active = members[
        (members["universe_id"] == universe_id)
        & (members["member_from"] <= date)
        & (members["member_to"].isna() | (date < members["member_to"]))
    ]
    return active.sort_values("security_id").reset_index(drop=True)


def fundamentals_asof(
    signals: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> pd.DataFrame:
    """Select the latest effective value for every signal/security/metric."""

    require_columns(signals, ("signal_date", "security_id"), "signals")
    require_columns(
        fundamentals,
        ("security_id", "metric", "effective_date", "report_period", "value"),
        "fundamentals",
    )
    left = signals.copy()
    left["signal_date"] = pd.to_datetime(left["signal_date"]).dt.normalize()
    right = fundamentals.copy()
    right["effective_date"] = pd.to_datetime(right["effective_date"]).dt.normalize()
    right["report_period"] = pd.to_datetime(right["report_period"]).dt.normalize()

    metrics = right[["metric"]].drop_duplicates()
    candidates = left.merge(metrics, how="cross")
    right = right.sort_values(
        ["effective_date", "security_id", "metric", "report_period"]
    ).drop_duplicates(["security_id", "metric", "effective_date"], keep="last")
    candidates = candidates.sort_values(["signal_date", "security_id", "metric"])
    selected = pd.merge_asof(
        candidates,
        right,
        left_on="signal_date",
        right_on="effective_date",
        by=["security_id", "metric"],
        direction="backward",
        allow_exact_matches=True,
    ).dropna(subset=["effective_date"])
    if not selected.empty and (selected["effective_date"] > selected["signal_date"]).any():
        raise AssertionError("Point-in-time selection leaked future fundamentals")
    return selected.reset_index(drop=True)


def membership_panel(
    signal_dates: list[str | pd.Timestamp],
    membership: pd.DataFrame,
    universe_id: str = "CSI300",
) -> pd.DataFrame:
    panels: list[pd.DataFrame] = []
    for signal_date in sorted(pd.Timestamp(value).normalize() for value in signal_dates):
        active = active_members(membership, signal_date, universe_id=universe_id)
        active.insert(0, "signal_date", signal_date)
        panels.append(active)
    if not panels:
        return pd.DataFrame(columns=["signal_date", *membership.columns])
    return pd.concat(panels, ignore_index=True)

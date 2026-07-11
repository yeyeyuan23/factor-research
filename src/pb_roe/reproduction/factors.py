"""PB, ROE, and original percentile-score construction."""

from __future__ import annotations

import pandas as pd

from pb_roe.data.pit import fundamentals_asof, membership_panel
from pb_roe.data.schema import require_columns


def add_paper_scores(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, ("security_id", "pb", "roe"), "paper_factor_snapshot")
    scored = frame.copy()
    valid = scored["pb"].gt(0) & scored[["pb", "roe"]].notna().all(axis=1)
    scored["pb_percentile"] = pd.NA
    scored["roe_percentile"] = pd.NA
    scored["paper_score"] = pd.NA
    scored.loc[valid, "pb_percentile"] = scored.loc[valid, "pb"].rank(
        method="average", pct=True, ascending=True
    )
    scored.loc[valid, "roe_percentile"] = scored.loc[valid, "roe"].rank(
        method="average", pct=True, ascending=True
    )
    scored.loc[valid, "paper_score"] = (
        scored.loc[valid, "roe_percentile"] + 1 - scored.loc[valid, "pb_percentile"]
    )
    for column in ("pb_percentile", "roe_percentile", "paper_score"):
        scored[column] = pd.to_numeric(scored[column], errors="coerce")
    return scored


def build_paper_factor_panel(
    signal_dates: list[object],
    membership: pd.DataFrame,
    fundamentals: pd.DataFrame,
    universe_id: str = "CSI300",
) -> pd.DataFrame:
    members = membership_panel(signal_dates, membership, universe_id=universe_id)
    signals = members[["signal_date", "security_id"]].drop_duplicates()
    selected = fundamentals_asof(signals, fundamentals)
    selected = selected[selected["metric"].isin(("pb", "roe"))]
    values = selected.pivot_table(
        index=["signal_date", "security_id"],
        columns="metric",
        values="value",
        aggfunc="last",
    ).reset_index()
    metadata_columns = [
        column
        for column in ("signal_date", "security_id", "industry", "weight")
        if column in members
    ]
    panel = (
        members[metadata_columns]
        .drop_duplicates()
        .merge(
            values,
            on=["signal_date", "security_id"],
            how="left",
            validate="one_to_one",
        )
    )
    scored_snapshots: list[pd.DataFrame] = []
    for signal_date, snapshot in panel.groupby("signal_date", sort=True):
        scored = add_paper_scores(snapshot.drop(columns="signal_date"))
        scored.insert(0, "signal_date", pd.Timestamp(signal_date))
        scored_snapshots.append(scored)
    if not scored_snapshots:
        return panel.assign(
            pb_percentile=pd.Series(dtype=float),
            roe_percentile=pd.Series(dtype=float),
            paper_score=pd.Series(dtype=float),
        )
    return pd.concat(scored_snapshots, ignore_index=True)

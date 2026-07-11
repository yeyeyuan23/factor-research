"""Original paper portfolio selection and weighting rules."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from pb_roe.data.schema import require_columns

RANK_SLICES = (
    ("TOP10", 0, 10),
    ("TOP20", 0, 20),
    ("TOP50", 0, 50),
    ("RANK50_100", 50, 100),
    ("RANK100_200", 100, 200),
    ("RANK200_PLUS", 200, None),
)


def _slice_ranked(
    frame: pd.DataFrame,
    value_column: str,
    ascending: bool,
    start: int,
    end: int | None,
) -> pd.DataFrame:
    ranked = frame.dropna(subset=[value_column]).sort_values(
        [value_column, "security_id"], ascending=[ascending, True]
    )
    return ranked.iloc[start:end].copy()


def _equal_weights(selected: pd.DataFrame) -> pd.Series:
    if selected.empty:
        return pd.Series(dtype=float, index=selected.index)
    return pd.Series(1 / len(selected), index=selected.index, dtype=float)


def _format_holdings(selected: pd.DataFrame, strategy_id: str, weights: pd.Series) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame(columns=["strategy_id", "signal_date", "security_id", "target_weight"])
    holdings = selected[["signal_date", "security_id"]].copy()
    holdings.insert(0, "strategy_id", strategy_id)
    holdings["target_weight"] = weights.to_numpy(dtype=float)
    return holdings


def build_rank_portfolios(panel: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        panel,
        ("signal_date", "security_id", "pb", "roe", "paper_score"),
        "paper_factor_panel",
    )
    holdings: list[pd.DataFrame] = []
    definitions = (
        ("R1_ROE", "roe", False),
        ("R2_PB", "pb", True),
        ("R3_PB_ROE", "paper_score", False),
    )
    for signal_date, snapshot in panel.groupby("signal_date", sort=True):
        snapshot = snapshot.assign(signal_date=signal_date)
        for prefix, value_column, ascending in definitions:
            for label, start, end in RANK_SLICES:
                selected = _slice_ranked(snapshot, value_column, ascending, start, end)
                holdings.append(
                    _format_holdings(selected, f"{prefix}_{label}", _equal_weights(selected))
                )
        universe = snapshot.dropna(subset=["paper_score"]).copy()
        holdings.append(_format_holdings(universe, "R0_UNIVERSE_EW", _equal_weights(universe)))
    return pd.concat(holdings, ignore_index=True)


def _industry_benchmark_weights(selected: pd.DataFrame, snapshot: pd.DataFrame) -> pd.Series:
    member_weights = pd.to_numeric(snapshot.get("weight"), errors="coerce")
    if member_weights.notna().all() and member_weights.sum() > 0:
        industry_share = member_weights.groupby(snapshot["industry"]).sum()
        industry_share = industry_share / industry_share.sum()
    else:
        industry_share = snapshot.groupby("industry")["security_id"].size().astype(float)
        industry_share = industry_share / industry_share.sum()
    counts = selected.groupby("industry")["security_id"].transform("size")
    return selected["industry"].map(industry_share).astype(float) / counts


def build_industry_portfolios(panel: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    require_columns(
        panel,
        ("signal_date", "security_id", "industry", "paper_score"),
        "paper_factor_panel",
    )
    holdings: list[pd.DataFrame] = []
    for signal_date, snapshot in panel.groupby("signal_date", sort=True):
        snapshot = snapshot.dropna(subset=["industry", "paper_score"]).copy()
        snapshot["signal_date"] = signal_date
        selected = (
            snapshot.sort_values(
                ["industry", "paper_score", "security_id"],
                ascending=[True, False, True],
            )
            .groupby("industry", group_keys=False)
            .head(top_n)
        )
        holdings.append(
            _format_holdings(selected, "R4_PB_ROE_INDUSTRY_EW", _equal_weights(selected))
        )
        benchmark_weights = _industry_benchmark_weights(selected, snapshot)
        holdings.append(
            _format_holdings(
                selected,
                "R4_PB_ROE_INDUSTRY_BENCHMARK_WEIGHT",
                benchmark_weights,
            )
        )
    result = pd.concat(holdings, ignore_index=True)
    if not result.empty:
        sums = result.groupby(["strategy_id", "signal_date"])["target_weight"].sum()
        if not np.allclose(sums.to_numpy(), 1.0):
            raise AssertionError("Industry portfolio weights do not sum to one")
    return result


def build_paper_holdings(panel: pd.DataFrame, industry_top_n: int = 5) -> pd.DataFrame:
    frames: Iterable[pd.DataFrame] = (
        build_rank_portfolios(panel),
        build_industry_portfolios(panel, top_n=industry_top_n),
    )
    return pd.concat(frames, ignore_index=True).sort_values(
        ["strategy_id", "signal_date", "security_id"]
    )

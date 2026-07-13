#!/usr/bin/env python3
"""Create the basic monthly IC chart used in factor analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pb_roe.evaluation.quantiles import quantile_backtest


def monthly_rank_ic(panel: pd.DataFrame, score_column: str) -> pd.Series:
    return panel.groupby("signal_date").apply(
        lambda frame: frame[score_column].corr(frame["target_return"], method="spearman"),
        include_groups=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--quantile-output", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    panel = pd.read_parquet(run_dir / "model_factor_panel.parquet")
    panel = panel[pd.to_datetime(panel["signal_date"]) >= pd.Timestamp("2015-01-01")].copy()
    selection = json.loads((run_dir / "frozen_factor_selection.json").read_text())
    oriented = []
    for feature, direction in selection["selected_directions"].items():
        column = f"{feature}_oriented"
        panel[column] = panel[feature] * int(direction)
        oriented.append(column)
    panel["equal_weight_score"] = panel[oriented].mean(axis=1)
    ic = monthly_rank_ic(panel, "equal_weight_score").dropna()
    dates = pd.to_datetime(ic.index)
    cumulative = ic.cumsum()
    development = ic[dates <= pd.Timestamp("2022-12-31")]
    mean_ic = development.mean()
    icir = mean_ic / development.std(ddof=1) * np.sqrt(12)
    win_rate = (development > 0).mean()

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure, axis = plt.subplots(figsize=(12, 7), dpi=160)
    colors = np.where(ic >= 0, "#4f86c6", "#d65a61")
    axis.bar(dates, ic, width=18, color=colors, label="月度 RankIC")
    axis.axhline(0, color="#333333", linewidth=1)
    axis.axhline(
        mean_ic,
        color="#f26d21",
        linewidth=2,
        linestyle="--",
        label=f"IC均值 = {mean_ic:.3f}",
    )
    axis.set_ylabel("RankIC")
    axis.set_xlabel("月份")
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    axis2 = axis.twinx()
    axis2.plot(dates, cumulative, color="#252233", linewidth=2.5, label="累计IC")
    axis2.set_ylabel("累计IC")
    axis.axvline(pd.Timestamp("2023-01-01"), color="#8f98a6", linestyle=":", linewidth=1.5)
    axis.text(pd.Timestamp("2023-01-15"), axis.get_ylim()[1] * 0.92, "冻结样本外", color="#5b6574")
    handles1, labels1 = axis.get_legend_handles_labels()
    handles2, labels2 = axis2.get_legend_handles_labels()
    axis.legend(handles1 + handles2, labels1 + labels2, loc="upper left", frameon=False, ncol=3)
    factor_count = len(oriented)
    title = (
        f"{factor_count}因子等权综合：开发期IC {mean_ic:.3f}，"
        f"ICIR {icir:.2f}，月胜率 {win_rate:.0%}"
    )
    axis.set_title(
        title,
        fontsize=16,
        fontweight="bold",
        pad=14,
    )
    figure.tight_layout()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, bbox_inches="tight")
    plt.close(figure)

    grouped = []
    for segment, start, end in (
        ("开发期（2015–2022）", "2015-01-01", "2022-12-31"),
        ("冻结期（2023–2025）", "2023-01-01", "2025-12-31"),
    ):
        sample = panel[pd.to_datetime(panel["signal_date"]).between(start, end)]
        quantiles = quantile_backtest(
            sample,
            "equal_weight_score",
            return_column="target_return",
            quantiles=5,
            cost_rate=0.003,
        )
        mean_returns = quantiles.groupby("quantile")["net_return"].mean() * 100
        grouped.append((segment, mean_returns))

    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8), dpi=160, sharey=True)
    colors = ["#d65a61", "#d65a61", "#9aa4b2", "#4f86c6", "#4f86c6"]
    for axis, (segment, mean_returns) in zip(axes, grouped, strict=True):
        bars = axis.bar(mean_returns.index.astype(str), mean_returns, color=colors)
        axis.axhline(0, color="#333333", linewidth=1)
        axis.set_title(segment, fontweight="bold")
        axis.set_xlabel("分组（Q1低 → Q5高）")
        axis.grid(axis="y", alpha=0.25)
        axis.set_axisbelow(True)
        for bar, value in zip(bars, mean_returns, strict=True):
            axis.text(
                bar.get_x() + bar.get_width() / 2,
                value + (0.015 if value >= 0 else -0.04),
                f"{value:.2f}%",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=9,
            )
    axes[0].set_ylabel("30bp成本后平均月收益（%）")
    figure.suptitle(
        f"{factor_count}因子等权综合：五分组收益与单调性",
        fontsize=15,
        fontweight="bold",
    )
    figure.tight_layout()
    figure.savefig(args.quantile_output, bbox_inches="tight")
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

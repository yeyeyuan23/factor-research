#!/usr/bin/env python3
"""Plot the modern BP, ROE, and PB-ROE baseline with Matplotlib."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FACTORS = {
    "bp_z": ("BP", "#2878b5"),
    "roe_z": ("ROE", "#d65a31"),
    "paper_score_z": ("PB-ROE", "#2a9d6f"),
}


def plot_ic(ic_file: Path, output: Path) -> None:
    frame = pd.read_csv(ic_file, parse_dates=["signal_date"])
    figure, axes = plt.subplots(3, 1, figsize=(12, 9), dpi=160, sharex=True)
    for axis, (factor, (label, color)) in zip(axes, FACTORS.items(), strict=True):
        selected = frame[frame["factor"] == factor].sort_values("signal_date")
        ic = selected.set_index("signal_date")["ic"].dropna()
        mean_ic = float(ic.mean())
        axis.bar(
            ic.index,
            ic,
            width=18,
            color=np.where(ic >= 0, color, "#d65a61"),
            alpha=0.72,
        )
        axis.axhline(0, color="#333333", linewidth=1)
        axis.axhline(
            mean_ic,
            color="#f26d21",
            linestyle="--",
            linewidth=1.8,
            label=f"全样本IC均值 = {mean_ic:.3f}",
        )
        axis.axvline(pd.Timestamp("2023-01-01"), color="#777777", linestyle=":")
        cumulative = axis.twinx()
        cumulative.plot(ic.index, ic.cumsum(), color="#252233", linewidth=1.8)
        cumulative.set_ylabel("累计IC")
        axis.set_ylabel("Rank IC")
        axis.set_title(label, loc="left", fontweight="bold")
        axis.grid(axis="y", alpha=0.2)
        axis.legend(frameon=False, loc="upper left")
    axes[-1].set_xlabel("月份（虚线后为2023–2025冻结区间）")
    figure.suptitle("原研报核心信号的现代月度IC（2012-05至2025-10）", fontsize=16)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def plot_quantiles(quantile_file: Path, output: Path) -> None:
    frame = pd.read_csv(quantile_file)
    frame = frame[(frame["cost_bps"] == 30) & frame["factor"].isin(FACTORS)]
    figure, axes = plt.subplots(1, 3, figsize=(13, 4.8), dpi=160, sharey=True)
    colors = ["#d94b32", "#ef8052", "#f0d77b", "#80c36b", "#3daa61"]
    for axis, (factor, (label, _)) in zip(axes, FACTORS.items(), strict=True):
        annual = (
            frame[frame["factor"] == factor]
            .groupby("quantile")["net_return"]
            .mean()
            .reindex(range(1, 6))
            * 12
            * 100
        )
        bars = axis.bar([f"Q{i}" for i in annual.index], annual, color=colors)
        axis.bar_label(bars, fmt="%.1f", padding=2, fontsize=8)
        axis.axhline(0, color="#444444", linewidth=1)
        axis.set_title(label, fontweight="bold")
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("五分组年化净收益（%，30bp成本）")
    figure.suptitle("原研报核心信号的现代五分组表现", fontsize=16)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--ic-output", required=True)
    parser.add_argument("--quantile-output", required=True)
    args = parser.parse_args()

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    run_dir = Path(args.run_dir)
    plot_ic(run_dir / "ic_timeseries.csv", Path(args.ic_output))
    plot_quantiles(run_dir / "quantile_returns.csv", Path(args.quantile_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

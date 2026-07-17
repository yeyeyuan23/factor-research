#!/usr/bin/env python3
"""Plot walk-forward model IC comparisons with Matplotlib."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

MODELS = {
    "Elastic Net": ("elastic-net", "#2878b5"),
    "LightGBM": ("lightgbm", "#d65a31"),
}
SEGMENTS = {
    "开发期\n2015–2022": ("development", "2015-01-01", "2022-12-31"),
    "探索性历史检验\n2023–2025": (
        "exploratory_2023_2025",
        "2023-01-01",
        "2025-12-31",
    ),
}


def monthly_rank_ic(path: Path) -> pd.Series:
    predictions = pd.read_parquet(path)
    predictions["signal_date"] = pd.to_datetime(predictions["signal_date"])
    return predictions.groupby("signal_date").apply(
        lambda frame: frame["prediction"].corr(frame["target_return"], method="spearman"),
        include_groups=False,
    )


def plot_segment_comparison(run_dir: Path, output: Path) -> None:
    summaries = {
        label: pd.read_csv(run_dir / f"{stem}_ic_segments.csv").set_index("segment")
        for label, (stem, _) in MODELS.items()
    }
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), dpi=160)
    width = 0.34
    positions = list(range(len(SEGMENTS)))
    for offset, (label, (_, color)) in zip((-width / 2, width / 2), MODELS.items(), strict=True):
        ic_values = [
            summaries[label].loc[segment, "ic_mean"] * 100 for segment, _, _ in SEGMENTS.values()
        ]
        t_values = [
            summaries[label].loc[segment, "newey_west_t"] for segment, _, _ in SEGMENTS.values()
        ]
        x = [position + offset for position in positions]
        bars = axes[0].bar(x, ic_values, width, label=label, color=color)
        t_bars = axes[1].bar(x, t_values, width, label=label, color=color)
        axes[0].bar_label(bars, fmt="%.2f%%", padding=3, fontsize=9)
        axes[1].bar_label(t_bars, fmt="%.2f", padding=3, fontsize=9)

    for axis in axes:
        axis.set_xticks(positions, SEGMENTS.keys())
        axis.axhline(0, color="#333333", linewidth=1)
        axis.grid(axis="y", alpha=0.25)
        axis.set_axisbelow(True)
    axes[0].set_title("Rank IC均值", fontweight="bold")
    axes[0].set_ylabel("Rank IC（%）")
    axes[0].legend(frameon=False)
    axes[1].set_title("Newey–West t值", fontweight="bold")
    axes[1].axhline(2, color="#777777", linestyle="--", linewidth=1.2, label="t = 2")
    axes[1].legend(frameon=False)
    figure.suptitle("8因子模型输入：预测能力对比", fontsize=16, fontweight="bold")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def plot_ic_timeseries(run_dir: Path, output: Path) -> None:
    series = {
        label: monthly_rank_ic(run_dir / f"{stem}_predictions.parquet").dropna()
        for label, (stem, _) in MODELS.items()
    }
    figure, axes = plt.subplots(2, 1, figsize=(12, 7), dpi=160, sharex=True)
    for label, (_, color) in MODELS.items():
        ic = series[label]
        axes[0].plot(ic.index, ic, label=label, color=color, linewidth=1.25, alpha=0.9)
        axes[1].plot(ic.index, ic.cumsum(), label=label, color=color, linewidth=2.2)
    for axis in axes:
        axis.axhline(0, color="#333333", linewidth=1)
        axis.axvline(pd.Timestamp("2023-01-01"), color="#777777", linestyle="--")
        axis.grid(alpha=0.25)
        axis.set_axisbelow(True)
    axes[0].set_ylabel("月度Rank IC")
    axes[0].set_title("月度IC", fontweight="bold")
    axes[0].legend(frameon=False, ncol=2)
    axes[1].set_ylabel("累计IC")
    axes[1].set_xlabel("月份")
    axes[1].set_title("累计IC", fontweight="bold")
    axes[1].text(
        pd.Timestamp("2023-02-01"),
        axes[1].get_ylim()[1] * 0.9,
        "新版模型探索区间",
        color="#555555",
    )
    figure.suptitle("Elastic Net与LightGBM：IC稳定性", fontsize=16, fontweight="bold")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--segment-output", required=True)
    parser.add_argument("--timeseries-output", required=True)
    args = parser.parse_args()

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    run_dir = Path(args.run_dir)
    plot_segment_comparison(run_dir, Path(args.segment_output))
    plot_ic_timeseries(run_dir, Path(args.timeseries_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

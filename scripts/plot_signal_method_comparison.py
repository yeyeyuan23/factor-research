#!/usr/bin/env python3
"""Compare equal weighting, Elastic Net, and LightGBM IC with Matplotlib."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

COLORS = {
    "三因子等权": "#2a9d6f",
    "Elastic Net": "#2878b5",
    "LightGBM": "#d65a31",
}
SEGMENTS = {"development": "开发期\n2015–2022", "frozen_oos": "冻结期\n2023–2025"}


def load_results(run_dir: Path) -> pd.DataFrame:
    equal = pd.read_csv(run_dir / "equal_weight_factor_ic.csv").assign(method="三因子等权")
    elastic = pd.read_csv(run_dir / "elastic-net_ic_segments.csv").assign(method="Elastic Net")
    lightgbm = pd.read_csv(run_dir / "lightgbm_ic_segments.csv").assign(method="LightGBM")
    return pd.concat([equal, elastic, lightgbm], ignore_index=True)


def plot(frame: pd.DataFrame, output: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8), dpi=160)
    segments = list(SEGMENTS)
    width = 0.24
    for index, method in enumerate(COLORS):
        selected = frame[frame["method"] == method].set_index("segment")
        positions = [position + (index - 1) * width for position in range(len(segments))]
        ic_values = [selected.loc[segment, "ic_mean"] * 100 for segment in segments]
        t_values = [selected.loc[segment, "newey_west_t"] for segment in segments]
        ic_bars = axes[0].bar(
            positions, ic_values, width, label=method, color=COLORS[method]
        )
        t_bars = axes[1].bar(
            positions, t_values, width, label=method, color=COLORS[method]
        )
        axes[0].bar_label(ic_bars, fmt="%.2f%%", padding=2, fontsize=8)
        axes[1].bar_label(t_bars, fmt="%.2f", padding=2, fontsize=8)
    for axis in axes:
        axis.set_xticks(range(len(segments)), [SEGMENTS[segment] for segment in segments])
        axis.axhline(0, color="#333333", linewidth=1)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    axes[0].set_title("Rank IC均值", fontweight="bold")
    axes[0].set_ylabel("Rank IC（%）")
    axes[0].legend(frameon=False)
    axes[1].set_title("Newey–West t值", fontweight="bold")
    axes[1].axhline(2, color="#777777", linestyle="--", linewidth=1.2)
    figure.suptitle("三因子等权与两种模型的预测能力", fontsize=16)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plot(load_results(Path(args.run_dir)), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

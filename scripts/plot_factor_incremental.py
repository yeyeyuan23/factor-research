#!/usr/bin/env python3
"""Plot PB-ROE incremental factor evidence with Matplotlib."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

GREEN = "#2a9d6f"
GRAY = "#9aa0a6"


def plot(input_path: Path, output: Path) -> None:
    frame = pd.read_csv(input_path)
    names = {
        "ep": "EP盈利收益率",
        "ocf_to_price": "OCF/P",
        "revenue_growth": "营收增长",
        "momentum_12_1": "12–1月动量",
        "reversal_1m": "1个月反转",
        "volatility_60d": "低波动",
    }
    frame["label"] = frame["factor"].map(names)
    colors = frame["incremental_pass"].map({True: GREEN, False: GRAY})
    x = np.arange(len(frame))
    figure, axes = plt.subplots(1, 3, figsize=(15, 5.2), dpi=160)
    panels = (
        ("residual_ic_mean", 100, "剔除PB、ROE后的残差IC", "Rank IC（%）", 0),
        ("add_one_delta_ic", 100, "加入候选后的IC增量", "IC增量（百分点）", 0),
        (
            "add_one_improvement_year_rate",
            100,
            "开发年份改善比例",
            "改善年份（%）",
            50,
        ),
    )
    for axis, (column, scale, title, ylabel, gate) in zip(axes, panels, strict=True):
        values = frame[column] * scale
        bars = axis.bar(x, values, color=colors)
        axis.bar_label(bars, fmt="%.1f", padding=2, fontsize=8)
        axis.set_xticks(x, frame["label"], rotation=55, ha="right")
        axis.set_title(title, fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.axhline(gate, color="#333333", linewidth=1, linestyle="--")
        axis.grid(axis="y", alpha=0.22)
        axis.set_axisbelow(True)
    figure.legend(
        handles=[Patch(color=GREEN, label="进入模型"), Patch(color=GRAY, label="剔除")],
        frameon=False,
        loc="center left",
        bbox_to_anchor=(0.995, 0.5),
    )
    figure.suptitle("6个扩展因子相对PB-ROE的开发期增量检验", fontsize=16)
    figure.tight_layout(rect=(0, 0, 0.96, 0.93))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plot(Path(args.input), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

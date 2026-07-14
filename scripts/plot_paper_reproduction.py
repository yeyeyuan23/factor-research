#!/usr/bin/env python3
"""Plot original-paper and reproduction annualized returns with Matplotlib."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


STRATEGIES = {
    "ROE20": "ROE Top20",
    "PB50_100": "PB 50–100",
    "PB_ROE50": "PB-ROE Top50",
    "PB_ROE_industry_equal_weight": "PB-ROE\n行业等权",
    "PB_ROE_industry_benchmark_weight": "PB-ROE\n行业基准权重",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    frame = frame[frame["strategy"].isin(STRATEGIES)].copy()
    frame["strategy"] = pd.Categorical(
        frame["strategy"], categories=list(STRATEGIES), ordered=True
    )
    pivot = frame.pivot(index="strategy", columns="source", values="annualized_net_return")
    pivot = pivot.reindex(list(STRATEGIES)) * 100

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    figure, axis = plt.subplots(figsize=(11, 5.4), dpi=160)
    x = range(len(pivot))
    width = 0.36
    original = axis.bar(
        [position - width / 2 for position in x],
        pivot["original_paper"],
        width,
        label="原研报",
        color="#7a7f87",
    )
    reproduced = axis.bar(
        [position + width / 2 for position in x],
        pivot["reproduction"],
        width,
        label="本项目复现",
        color="#2878b5",
    )
    axis.bar_label(original, fmt="%.1f%%", padding=3, fontsize=9)
    axis.bar_label(reproduced, fmt="%.1f%%", padding=3, fontsize=9)
    axis.set_xticks(list(x), [STRATEGIES[key] for key in pivot.index])
    axis.set_ylabel("成本后年化收益（%）")
    axis.set_title("2005–2011 原研报与本项目复现", fontsize=16, fontweight="bold")
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, ncol=2)
    axis.text(
        0.01,
        0.97,
        "方向与收益量级得到复现；行业等权最优结论未复现",
        transform=axis.transAxes,
        va="top",
        color="#444444",
    )
    figure.tight_layout()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

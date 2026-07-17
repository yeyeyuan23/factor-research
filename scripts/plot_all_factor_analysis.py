#!/usr/bin/env python3
"""Plot IC stability and five-group monotonicity for every candidate factor."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pb_roe.evaluation.quantiles import long_short_spread, quantile_backtest

DEVELOPMENT_END = pd.Timestamp("2022-12-31")
OOS_START = pd.Timestamp("2023-01-01")
LABELS = {
    "ep": "EP盈利收益率",
    "ocf_to_price": "OCF/P经营现金流收益率",
    "revenue_growth": "营收增长",
    "momentum_12_1": "12–1月动量",
    "reversal_1m": "1月反转",
    "roe": "ROE",
    "volatility_60d": "低总波动率",
    "bp": "BP",
}


def monthly_rank_ic(panel: pd.DataFrame, factor: str) -> pd.Series:
    return panel.groupby("signal_date").apply(
        lambda frame: frame[factor].corr(frame["target_return"], method="spearman"),
        include_groups=False,
    )


def slug(value: str) -> str:
    return value.replace("_", "-")


def plot_ic(panel: pd.DataFrame, factor: str, label: str, output: Path) -> None:
    ic = monthly_rank_ic(panel, factor).dropna()
    dates = pd.to_datetime(ic.index)
    development = ic[dates <= DEVELOPMENT_END]
    mean_ic = development.mean()
    icir = mean_ic / development.std(ddof=1) * np.sqrt(12)
    win_rate = (development > 0).mean()

    figure, axis = plt.subplots(figsize=(11, 6), dpi=160)
    axis.bar(dates, ic, width=18, color=np.where(ic >= 0, "#4f86c6", "#d65a61"))
    axis.axhline(0, color="#333333", linewidth=1)
    axis.axhline(
        mean_ic, color="#f26d21", linestyle="--", linewidth=2, label=f"开发期IC均值 = {mean_ic:.3f}"
    )
    axis.axvline(OOS_START, color="#8f98a6", linestyle=":", linewidth=1.5)
    axis.set(xlabel="月份", ylabel="RankIC")
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    cumulative = axis.twinx()
    cumulative.plot(dates, ic.cumsum(), color="#252233", linewidth=2.3, label="累计IC")
    cumulative.set_ylabel("累计IC")
    handles1, labels1 = axis.get_legend_handles_labels()
    handles2, labels2 = cumulative.get_legend_handles_labels()
    axis.legend(handles1 + handles2, labels1 + labels2, loc="upper left", frameon=False)
    axis.set_title(
        f"{label}：开发期IC {mean_ic:.3f}，ICIR {icir:.2f}，月胜率 {win_rate:.0%}",
        fontsize=15,
        fontweight="bold",
    )
    figure.tight_layout()
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def plot_quantiles(panel: pd.DataFrame, factor: str, label: str, output: Path) -> None:
    quantiles = quantile_backtest(
        panel, factor, return_column="target_return", quantiles=5, cost_rate=0.003
    )
    quantiles["signal_date"] = pd.to_datetime(quantiles["signal_date"])
    development = quantiles[quantiles["signal_date"] <= DEVELOPMENT_END]
    annual = development.groupby("quantile")["net_return"].mean() * 12 * 100
    spread = long_short_spread(quantiles)
    spread["signal_date"] = pd.to_datetime(spread["signal_date"])

    figure, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=160)
    colors = ["#d94b32", "#ef8052", "#f0d77b", "#80c36b", "#3daa61"]
    axes[0].bar([f"Q{i}" for i in annual.index], annual, color=colors)
    axes[0].axhline(0, color="#555555", linewidth=1)
    axes[0].set(title="开发期五分组年化超额收益（30bp）", ylabel="年化超额（%）")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].set_axisbelow(True)

    pivot = quantiles.pivot(index="signal_date", columns="quantile", values="net_return")
    for group, color in ((1, "#c52233"), (3, "#777777"), (5, "#259d63")):
        axes[1].plot(
            pivot.index,
            (1 + pivot[group].fillna(0)).cumprod(),
            label=f"Q{group}",
            color=color,
            linewidth=1.5,
        )
    axes[1].plot(
        spread["signal_date"],
        (1 + spread["net_spread"].fillna(0)).cumprod(),
        label="多空 Q5−Q1",
        color="#2461ad",
        linewidth=2.5,
    )
    axes[1].axhline(1, color="#555555", linewidth=1)
    axes[1].axvline(OOS_START, color="#8f98a6", linestyle=":", linewidth=1.5)
    axes[1].set(title="分组累计超额净值", xlabel="月份")
    axes[1].legend(frameon=False)
    axes[1].grid(alpha=0.25)
    figure.suptitle(f"{label}：五分组收益单调性", fontsize=15, fontweight="bold")
    figure.tight_layout()
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    run_dir, output = Path(args.run_dir), Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(run_dir / "model_factor_panel.parquet")
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    panel = panel[panel["signal_date"] >= pd.Timestamp("2015-01-01")].copy()
    validation = pd.read_csv(run_dir / "factor_validation.csv")

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    for row in validation.itertuples(index=False):
        feature = f"{row.factor}_z"
        oriented = f"{feature}_oriented"
        panel[oriented] = panel[feature] * int(row.direction)
        label = LABELS[str(row.factor)]
        name = slug(str(row.factor))
        plot_ic(panel, oriented, label, output / f"{name}-ic.png")
        plot_quantiles(panel, oriented, label, output / f"{name}-quantiles.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

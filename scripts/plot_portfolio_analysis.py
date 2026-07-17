#!/usr/bin/env python3
"""Plot active-risk portfolio results using Matplotlib."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

COLORS = {
    "基准": "#7a7f87",
    "PB-ROE": "#9c755f",
    "5因子等权": "#2a9d6f",
    "Elastic Net": "#2878b5",
    "LightGBM": "#d65a31",
}

METHOD_FILES = {
    "PB-ROE": "pb_roe_baseline",
    "5因子等权": "model_input_equal_weight",
    "Elastic Net": "elastic-net",
    "LightGBM": "lightgbm",
}


def wealth(returns: pd.Series) -> pd.Series:
    return (1 + returns.fillna(0)).cumprod()


def drawdown(returns: pd.Series) -> pd.Series:
    curve = wealth(returns)
    return curve / curve.cummax() - 1


def load_returns(run_dir: Path) -> pd.DataFrame:
    merged: pd.DataFrame | None = None
    for label, stem in METHOD_FILES.items():
        current = pd.read_csv(
            run_dir / f"{stem}_optimized_returns.csv", parse_dates=["signal_date"]
        )
        columns = current[["signal_date", "net_return_30bp"]].rename(
            columns={"net_return_30bp": label}
        )
        if merged is None:
            merged = current[["signal_date", "benchmark_return"]].merge(
                columns, on="signal_date", validate="one_to_one"
            )
        else:
            merged = merged.merge(columns, on="signal_date", validate="one_to_one")
    if merged is None:
        raise ValueError("No portfolio return files were loaded")
    return merged.rename(columns={"benchmark_return": "基准"})


def plot_performance(returns: pd.DataFrame, output: Path) -> None:
    sample = returns[returns["signal_date"] >= pd.Timestamp("2015-01-01")].set_index("signal_date")
    figure, axes = plt.subplots(2, 1, figsize=(12, 7), dpi=160, sharex=True)
    for label in COLORS:
        axes[0].plot(
            sample.index,
            wealth(sample[label]),
            label=label,
            color=COLORS[label],
            linewidth=2.3 if label == "5因子等权" else 1.5,
        )
        axes[1].plot(
            sample.index,
            drawdown(sample[label]) * 100,
            label=label,
            color=COLORS[label],
            linewidth=2.1 if label == "5因子等权" else 1.4,
        )
    for axis in axes:
        axis.axvline(pd.Timestamp("2023-01-01"), color="#555555", linestyle="--")
        axis.grid(alpha=0.25)
        axis.set_axisbelow(True)
    axes[0].set_title("30bp成本后累计净值", fontweight="bold")
    axes[0].set_ylabel("净值")
    axes[0].legend(frameon=False, ncol=5, fontsize=9)
    axes[1].set_title("回撤", fontweight="bold")
    axes[1].set_ylabel("回撤（%）")
    axes[1].set_xlabel("月份")
    axes[1].text(pd.Timestamp("2023-02-01"), -3, "新版探索区间", color="#555555")
    figure.suptitle("主动风险组合表现", fontsize=16, fontweight="bold")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def plot_segment_metrics(run_dir: Path, output: Path) -> None:
    rows = []
    for model, stem in METHOD_FILES.items():
        filename = f"{stem}_portfolio_summary.csv"
        summary = pd.read_csv(run_dir / filename)
        for segment, label in (
            ("development", "开发期"),
            ("exploratory_2023_2025", "探索性历史检验"),
        ):
            row = summary[(summary["segment"] == segment) & (summary["cost_bps"] == 30)].iloc[0]
            rows.extend(
                [
                    {
                        "segment": label,
                        "series": "基准",
                        "annual_return": row["benchmark_annual_return"] * 100,
                        "sharpe": row["benchmark_sharpe"],
                    },
                    {
                        "segment": label,
                        "series": model,
                        "annual_return": row["net_annual_return"] * 100,
                        "sharpe": row["net_sharpe"],
                    },
                ]
            )
    frame = pd.DataFrame(rows).drop_duplicates(
        subset=["segment", "series"], keep="last"
    )
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.8), dpi=160)
    segments = ["开发期", "探索性历史检验"]
    width = 0.15
    for index, series in enumerate(COLORS):
        subset = frame[frame["series"] == series].set_index("segment")
        x = [
            position + (index - (len(COLORS) - 1) / 2) * width
            for position in range(2)
        ]
        annual = [subset.loc[segment, "annual_return"] for segment in segments]
        sharpe = [subset.loc[segment, "sharpe"] for segment in segments]
        bars = axes[0].bar(x, annual, width, label=series, color=COLORS[series])
        axes[1].bar(x, sharpe, width, label=series, color=COLORS[series])
        axes[0].bar_label(bars, fmt="%.2f%%", padding=3, fontsize=9)
    for axis in axes:
        axis.set_xticks(range(2), segments)
        axis.axhline(0, color="#333333", linewidth=1)
        axis.grid(axis="y", alpha=0.25)
        axis.set_axisbelow(True)
    axes[0].set_title("30bp成本后年化收益", fontweight="bold")
    axes[0].set_ylabel("年化收益（%）")
    axes[0].legend(frameon=False)
    axes[1].set_title("Sharpe", fontweight="bold")
    figure.suptitle("分段组合评价", fontsize=16, fontweight="bold")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def plot_oos_yearly(returns: pd.DataFrame, output: Path) -> None:
    sample = returns[returns["signal_date"] >= pd.Timestamp("2023-01-01")].copy()
    sample["year"] = sample["signal_date"].dt.year
    annual = sample.groupby("year")[list(COLORS)].apply(
        lambda frame: (1 + frame).prod() - 1
    )
    figure, axis = plt.subplots(figsize=(10, 4.8), dpi=160)
    width = 0.15
    years = annual.index.tolist()
    for index, series in enumerate(COLORS):
        x = [
            position + (index - (len(COLORS) - 1) / 2) * width
            for position in range(len(years))
        ]
        bars = axis.bar(x, annual[series] * 100, width, label=series, color=COLORS[series])
        axis.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    axis.set_xticks(range(len(years)), [str(year) for year in years])
    axis.axhline(0, color="#333333", linewidth=1)
    axis.grid(axis="y", alpha=0.25)
    axis.set_axisbelow(True)
    axis.set_ylabel("年度收益（%）")
    axis.set_title(
        "2023–2025探索性历史检验：年度收益并非逐年稳定",
        fontsize=15,
        fontweight="bold",
    )
    axis.legend(frameon=False, ncol=5, fontsize=9)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--performance-output", required=True)
    parser.add_argument("--segment-output", required=True)
    parser.add_argument("--yearly-output", required=True)
    args = parser.parse_args()

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    run_dir = Path(args.run_dir)
    returns = load_returns(run_dir)
    plot_performance(returns, Path(args.performance_output))
    plot_segment_metrics(run_dir, Path(args.segment_output))
    plot_oos_yearly(returns, Path(args.yearly_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

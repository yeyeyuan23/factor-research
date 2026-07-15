#!/usr/bin/env python3
"""Generate English Matplotlib charts for the 10-minute HTML presentation."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

BLUE = "#2563a6"
GREEN = "#238b65"
ORANGE = "#d96534"
GRAY = "#7a818a"
RED = "#c94d56"
PALE = "#e8edf2"


def save(figure: plt.Figure, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(output, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def paper_reproduction(results: Path, output: Path) -> None:
    frame = pd.read_csv(results / "paper_reproduction_full.csv")
    strategies = {
        "ROE20": "ROE Top 20",
        "PB50_100": "PB Rank 50–100",
        "PB_ROE50": "PB–ROE Top 50",
        "PB_ROE_industry_equal_weight": "PB–ROE Industry EW",
    }
    selected = frame[frame["strategy"].isin(strategies)].copy()
    pivot = selected.pivot(index="strategy", columns="source", values="annualized_net_return")
    pivot = pivot.reindex(strategies)
    x = np.arange(len(pivot))
    width = 0.34
    figure, axis = plt.subplots(figsize=(11.5, 5.2))
    original = axis.bar(
        x - width / 2,
        pivot["original_paper"] * 100,
        width,
        label="Original paper",
        color=GRAY,
    )
    reproduced = axis.bar(
        x + width / 2,
        pivot["reproduction"] * 100,
        width,
        label="This project",
        color=BLUE,
    )
    axis.bar_label(original, fmt="%.1f%%", padding=3, fontsize=10)
    axis.bar_label(reproduced, fmt="%.1f%%", padding=3, fontsize=10)
    axis.set_xticks(x, [strategies[value] for value in pivot.index])
    axis.set_ylabel("Annualized net return")
    axis.set_title("The historical PB–ROE effect is directionally reproducible", weight="bold")
    axis.set_ylim(0, 42)
    axis.grid(axis="y", alpha=0.22)
    axis.legend(frameon=False, ncol=2)
    save(figure, output)


def modern_baseline(results: Path, output: Path) -> None:
    frame = pd.read_csv(results / "modern_factor_baseline.csv")
    labels = {"BP": "BP", "ROE_TTM": "ROE", "PB_ROE": "PB–ROE"}
    order = list(labels)
    raw = frame[frame["variant"] == "raw"].set_index("factor").reindex(order)
    adjusted = (
        frame[frame["variant"] == "industry_adjusted"].set_index("factor").reindex(order)
    )
    x = np.arange(len(order))
    width = 0.34
    figure, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    for axis, column, title, ylabel in (
        (axes[0], "ic_mean", "Rank IC", "Mean Rank IC (%)"),
        (
            axes[1],
            "net_annual_return_30bp",
            "30 bp long–short return",
            "Annualized net return (%)",
        ),
    ):
        raw_bars = axis.bar(
            x - width / 2, raw[column] * 100, width, label="Raw", color=BLUE
        )
        adj_bars = axis.bar(
            x + width / 2,
            adjusted[column] * 100,
            width,
            label="Industry adjusted",
            color=GREEN,
        )
        axis.bar_label(raw_bars, fmt="%.2f", padding=3, fontsize=9)
        axis.bar_label(adj_bars, fmt="%.2f", padding=3, fontsize=9)
        axis.set_xticks(x, [labels[value] for value in order])
        axis.set_title(title, weight="bold")
        axis.set_ylabel(ylabel)
        axis.axhline(0, color="#333333", linewidth=1)
        axis.grid(axis="y", alpha=0.22)
    axes[0].legend(frameon=False, ncol=2)
    figure.suptitle("PB–ROE still predicts returns, but its economic payoff is much weaker")
    save(figure, output)


def factor_gates(results: Path, output: Path) -> None:
    frame = pd.read_csv(results / "factor_validation_summary.csv")
    names = {
        "paper_score": "PB–ROE",
        "momentum_12_1": "12–1 Momentum",
        "idiosyncratic_volatility": "Low Idio Vol",
        "bp": "BP",
        "beta_252d": "Low Beta",
        "volatility_60d": "Low Total Vol",
        "reversal_1m": "1M Reversal",
        "roe": "ROE",
        "gross_margin": "Gross Margin",
        "earnings_growth": "Earnings Growth",
        "revenue_growth": "Revenue Growth",
        "liquidity_20d": "Low Liquidity",
    }
    selected = frame[frame["selected"]].sort_values("development_ic_mean", ascending=False)
    failed = frame[~frame["selected"]].sort_values("development_ic_mean", ascending=False)
    ordered = pd.concat([selected, failed], ignore_index=True)
    checks = pd.DataFrame(
        {
            "IC ≥ 2%": ordered["development_ic_mean"] >= 0.02,
            "NW t ≥ 2": ordered["development_newey_west_t"] >= 2,
            "Positive years ≥ 50%": ordered["year_positive_rate"] >= 0.5,
            "Monotonicity ≥ 0.8": ordered["quantile_monotonicity_30bp"] >= 0.8,
            "30 bp spread > 0": ordered["long_short_annual_return_30bp"] > 0,
        }
    )
    matrix = checks.astype(int).to_numpy()
    figure, axis = plt.subplots(figsize=(10.8, 6.7))
    axis.imshow(matrix, aspect="auto", cmap=ListedColormap(["#f1c4c8", "#b9dfce"]), vmin=0, vmax=1)
    axis.set_xticks(range(checks.shape[1]), checks.columns, rotation=18, ha="right")
    axis.set_yticks(range(len(ordered)), [names[value] for value in ordered["factor"]])
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(
                column,
                row,
                "PASS" if matrix[row, column] else "FAIL",
                ha="center",
                va="center",
                fontsize=8,
            )
    for tick, is_selected in zip(axis.get_yticklabels(), ordered["selected"], strict=True):
        if is_selected:
            tick.set_weight("bold")
            tick.set_color(GREEN)
    axis.set_title("Only 3 of 12 factors passed every pre-defined gate", weight="bold")
    axis.tick_params(length=0)
    for edge in np.arange(-0.5, matrix.shape[1], 1):
        axis.axvline(edge, color="white", linewidth=1.5)
    for edge in np.arange(-0.5, matrix.shape[0], 1):
        axis.axhline(edge, color="white", linewidth=1.5)
    save(figure, output)


def equal_weight_improvement(results: Path, output: Path) -> None:
    factors = pd.read_csv(results / "factor_validation_summary.csv").set_index("factor")
    equal = pd.read_csv(results / "equal_weight_factor_baseline.csv")
    equal_30 = equal[equal["cost_bps"] == 30].set_index("segment")
    labels = ["PB–ROE\nDevelopment", "3-factor EW\nDevelopment", "3-factor EW\nFrozen"]
    ic = [
        factors.loc["paper_score", "development_ic_mean"] * 100,
        equal_30.loc["development", "ic_mean"] * 100,
        equal_30.loc["frozen_oos", "ic_mean"] * 100,
    ]
    returns = [
        factors.loc["paper_score", "long_short_annual_return_30bp"] * 100,
        equal_30.loc["development", "annual_return"] * 100,
        equal_30.loc["frozen_oos", "annual_return"] * 100,
    ]
    colors = [GRAY, GREEN, BLUE]
    figure, axes = plt.subplots(1, 2, figsize=(11.8, 4.8))
    for axis, values, title, ylabel in (
        (axes[0], ic, "Rank IC", "Mean Rank IC (%)"),
        (axes[1], returns, "30 bp long–short return", "Annualized return (%)"),
    ):
        bars = axis.bar(range(3), values, color=colors)
        axis.bar_label(bars, fmt="%.2f", padding=3)
        axis.set_xticks(range(3), labels)
        axis.set_title(title, weight="bold")
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.22)
    figure.suptitle("The simple 3-factor combination clearly improves the PB–ROE baseline")
    save(figure, output)


def method_comparison(results: Path, output: Path) -> None:
    equal = pd.read_csv(results / "equal_weight_factor_baseline.csv")
    equal = equal[equal["cost_bps"] == 30].set_index("segment")
    elastic = pd.read_csv(results / "elastic_net_summary.csv").set_index("segment")
    light = pd.read_csv(results / "lightgbm_summary.csv")
    light = light[light["model"] == "LightGBM"].set_index("segment")
    methods = ["3-factor EW", "Elastic Net", "LightGBM"]
    colors = [GREEN, BLUE, ORANGE]
    segments = ["Development", "Frozen"]
    values = {
        "Development": [
            equal.loc["development", "ic_mean"] * 100,
            elastic.loc["development_2015_2022", "rank_ic_mean"] * 100,
            light.loc["development_2015_2022", "rank_ic_mean"] * 100,
        ],
        "Frozen": [
            equal.loc["frozen_oos", "ic_mean"] * 100,
            elastic.loc["frozen_oos_2023_2025", "rank_ic_mean"] * 100,
            light.loc["frozen_oos_2023_2025", "rank_ic_mean"] * 100,
        ],
    }
    figure, axis = plt.subplots(figsize=(10.8, 5.1))
    x = np.arange(2)
    width = 0.23
    for index, method in enumerate(methods):
        bars = axis.bar(
            x + (index - 1) * width,
            [values[segment][index] for segment in segments],
            width,
            label=method,
            color=colors[index],
        )
        axis.bar_label(bars, fmt="%.2f%%", padding=3)
    axis.set_xticks(x, ["Development\n2015–2022", "Frozen\n2023–2025"])
    axis.set_ylabel("Mean Rank IC")
    axis.set_title("More complex models did not beat equal weighting", weight="bold")
    axis.grid(axis="y", alpha=0.22)
    axis.legend(frameon=False, ncol=3)
    save(figure, output)


def portfolio_comparison(results: Path, output: Path) -> None:
    frame = pd.read_csv(results / "portfolio_model_comparison.csv")
    frozen = frame[
        (frame["segment"] == "frozen_oos") & (frame["cost_bps"] == 30)
    ].set_index("model")
    labels = ["CSI 300 EW proxy", "Elastic Net", "LightGBM"]
    returns = [
        frozen.iloc[0]["benchmark_annual_return"] * 100,
        frozen.loc["ElasticNet", "net_annual_return"] * 100,
        frozen.loc["LightGBM", "net_annual_return"] * 100,
    ]
    sharpes = [
        frozen.iloc[0]["benchmark_sharpe"],
        frozen.loc["ElasticNet", "net_sharpe"],
        frozen.loc["LightGBM", "net_sharpe"],
    ]
    drawdowns = [
        frozen.iloc[0]["benchmark_max_drawdown"] * 100,
        frozen.loc["ElasticNet", "net_max_drawdown"] * 100,
        frozen.loc["LightGBM", "net_max_drawdown"] * 100,
    ]
    colors = [GRAY, BLUE, ORANGE]
    figure, axes = plt.subplots(1, 3, figsize=(13.2, 4.6))
    for axis, values, title, fmt in (
        (axes[0], returns, "Annualized return", "%.2f%%"),
        (axes[1], sharpes, "Sharpe ratio", "%.2f"),
        (axes[2], drawdowns, "Maximum drawdown", "%.1f%%"),
    ):
        bars = axis.bar(range(3), values, color=colors)
        axis.bar_label(bars, fmt=fmt, padding=3, fontsize=9)
        axis.set_xticks(range(3), labels, rotation=14, ha="right")
        axis.set_title(title, weight="bold")
        axis.axhline(0, color="#333333", linewidth=1)
        axis.grid(axis="y", alpha=0.22)
    figure.suptitle("Elastic Net improved the proxy benchmark, but the edge is modest")
    save(figure, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="docs/results")
    parser.add_argument("--output-dir", default="docs/results/figures/presentation-en")
    args = parser.parse_args()
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": True,
        }
    )
    results = Path(args.results_dir)
    output = Path(args.output_dir)
    paper_reproduction(results, output / "01-paper-reproduction.png")
    modern_baseline(results, output / "02-modern-baseline.png")
    factor_gates(results, output / "03-factor-gates.png")
    equal_weight_improvement(results, output / "04-equal-weight-improvement.png")
    method_comparison(results, output / "05-method-comparison.png")
    portfolio_comparison(results, output / "06-portfolio-comparison.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

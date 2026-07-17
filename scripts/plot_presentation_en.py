#!/usr/bin/env python3
"""Generate English Matplotlib charts for the 10-minute HTML presentation."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

BLUE = "#2563a6"
GREEN = "#238b65"
ORANGE = "#d96534"
GRAY = "#7a818a"
RED = "#c94d56"
IS_YELLOW = "#f2cf37"
TRAIN_YELLOW = "#f7e9a8"
OOS_TEAL = "#35b4cd"
VALID_TEAL = "#74c9da"


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
    selected = frame[frame["selected"]].sort_values(
        "development_ic_mean", ascending=False
    )
    failed = frame[~frame["selected"]].sort_values(
        "development_ic_mean", ascending=False
    )
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
    axis.imshow(
        matrix,
        aspect="auto",
        cmap=ListedColormap(["#f1c4c8", "#b9dfce"]),
        vmin=0,
        vmax=1,
    )
    axis.set_xticks(range(checks.shape[1]), checks.columns, rotation=18, ha="right")
    axis.set_yticks(
        range(len(ordered)), [names[value] for value in ordered["factor"]]
    )
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
    for tick, is_selected in zip(
        axis.get_yticklabels(), ordered["selected"], strict=True
    ):
        if is_selected:
            tick.set_weight("bold")
            tick.set_color(GREEN)
    passed = int(ordered["selected"].sum())
    axis.set_title(
        f"Only {passed} of 12 factors passed every pre-defined gate", weight="bold"
    )
    axis.tick_params(length=0)
    for edge in np.arange(-0.5, matrix.shape[1], 1):
        axis.axvline(edge, color="white", linewidth=1.5)
    for edge in np.arange(-0.5, matrix.shape[0], 1):
        axis.axhline(edge, color="white", linewidth=1.5)
    save(figure, output)


def factor_incrementality(results: Path, output: Path) -> None:
    frame = pd.read_csv(results / "factor_incremental_analysis.csv")
    names = {
        "gross_margin": "Gross margin",
        "revenue_growth": "Revenue growth",
        "earnings_growth": "Earnings growth",
        "momentum_12_1": "12–1 momentum",
        "reversal_1m": "1M reversal",
        "volatility_60d": "Low total vol",
        "liquidity_20d": "Low liquidity",
        "beta_252d": "Low beta",
        "idiosyncratic_volatility": "Low idio vol",
    }
    frame["label"] = frame["factor"].map(names)
    colors = frame["incremental_pass"].map({True: GREEN, False: GRAY})
    x = np.arange(len(frame))
    figure, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    specs = (
        ("residual_ic_mean", 100, "Residual Rank IC", "Mean IC (%)", 0),
        ("add_one_delta_ic", 100, "Add-one IC improvement", "Delta IC (pp)", 0),
        (
            "add_one_improvement_year_rate",
            100,
            "Years beating PB–ROE",
            "Development years (%)",
            50,
        ),
    )
    for axis, (column, scale, title, ylabel, gate) in zip(axes, specs, strict=True):
        values = frame[column] * scale
        bars = axis.bar(x, values, color=colors)
        axis.bar_label(bars, fmt="%.1f", padding=2, fontsize=8)
        axis.set_xticks(x, frame["label"], rotation=55, ha="right")
        axis.set_title(title, weight="bold")
        axis.set_ylabel(ylabel)
        axis.axhline(gate, color="#333333", linewidth=1, linestyle="--")
        axis.grid(axis="y", alpha=0.22)
    figure.legend(
        handles=[Patch(color=GREEN, label="Eligible"), Patch(color=GRAY, label="Rejected")],
        frameon=False,
        loc="center left",
        bbox_to_anchor=(0.995, 0.5),
    )
    figure.suptitle("Six extensions add development-sample information beyond PB–ROE")
    save(figure, output)


def walk_forward_models(results: Path, output: Path) -> None:
    example = pd.read_csv(results / "walk_forward_example.csv")
    for column in example.columns.difference(["model"]):
        example[column] = pd.to_datetime(example[column])
    light = example.loc[example["model"].eq("LightGBM")].sort_values(
        "prediction_date"
    )
    figure, (sample_axis, fold_axis) = plt.subplots(
        2,
        1,
        figsize=(13.8, 7.2),
        gridspec_kw={"height_ratios": [0.9, 2.1]},
    )

    sample_segments = [
        ("Warm-up\nfeatures only", "2010-01-01", "2012-05-31", GRAY),
        ("Modern evaluation", "2012-05-31", "2015-01-01", "#b9d8e9"),
        ("IS development\nselect factors", "2015-01-01", "2023-01-01", IS_YELLOW),
        (
            "Prior OOS for strict rule\nexploratory for revised models",
            "2023-01-01",
            "2026-01-01",
            OOS_TEAL,
        ),
    ]
    for label, start, end, color in sample_segments:
        start_date = pd.Timestamp(start)
        end_date = pd.Timestamp(end)
        sample_axis.broken_barh(
            [
                (
                    mdates.date2num(start_date),
                    mdates.date2num(end_date) - mdates.date2num(start_date),
                )
            ],
            (0.15, 0.7),
            facecolors=color,
        )
        sample_axis.text(
            start_date + (end_date - start_date) / 2,
            0.5,
            label,
            ha="center",
            va="center",
            fontsize=9,
            weight="bold",
        )
    freeze_date = pd.Timestamp("2023-01-01")
    sample_axis.axvline(freeze_date, color="#172033", linestyle="--", linewidth=2)
    sample_axis.text(
        freeze_date,
        1.02,
        "Original strict-rule freeze",
        ha="center",
        va="bottom",
        fontsize=9,
        weight="bold",
    )
    sample_axis.set_xlim(pd.Timestamp("2010-01-01"), pd.Timestamp("2026-01-01"))
    sample_axis.set_ylim(0, 1.2)
    sample_axis.set_yticks([])
    sample_axis.xaxis.set_major_locator(mdates.YearLocator(2))
    sample_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    sample_axis.set_title(
        "1. Evidence status: strict factor was frozen; revised multi-factor models are exploratory"
    )
    sample_axis.grid(axis="x", alpha=0.18)

    rows = list(light.itertuples(index=False))
    y_positions = list(range(len(rows) - 1, -1, -1))
    for row, y_position in zip(rows, y_positions, strict=True):
        for start, end, color in (
            (row.training_start, row.training_end, TRAIN_YELLOW),
            (row.validation_start, row.validation_end, VALID_TEAL),
        ):
            fold_axis.broken_barh(
                [(mdates.date2num(start), mdates.date2num(end) - mdates.date2num(start))],
                (y_position - 0.31, 0.62),
                facecolors=color,
            )
        fold_axis.broken_barh(
            [
                (
                    mdates.date2num(row.excluded_signal_date),
                    mdates.date2num(row.excluded_label_exit_date)
                    - mdates.date2num(row.excluded_signal_date),
                )
            ],
            (y_position - 0.31, 0.62),
            facecolors=RED,
        )
        fold_axis.vlines(
            row.prediction_date,
            y_position - 0.48,
            y_position + 0.48,
            color="#172033",
            linewidth=2,
            linestyle="--",
        )
        fold_axis.text(
            row.prediction_date,
            y_position + 0.44,
            f"Predict {row.prediction_date:%d %b}",
            ha="right",
            va="bottom",
            fontsize=8,
        )
    fold_axis.set_yticks(
        y_positions,
        [f"Fold {index}: monthly refit" for index in range(1, len(rows) + 1)],
    )
    fold_axis.set_xlim(pd.Timestamp("2017-07-01"), pd.Timestamp("2023-05-31"))
    fold_axis.set_ylim(-0.75, len(rows) - 0.25)
    fold_axis.xaxis.set_major_locator(mdates.YearLocator())
    fold_axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fold_axis.set_title(
        "2. Inside each historical forecast: the 60-month mature-label window rolls forward"
    )
    fold_axis.grid(axis="x", alpha=0.2)
    fold_axis.legend(
        handles=[
            Patch(color=TRAIN_YELLOW, label="LightGBM fit: first 48 months"),
            Patch(color=VALID_TEAL, label="Validation: last 12 mature months"),
            Patch(color=RED, label="Latest label not mature—excluded"),
        ],
        frameon=False,
        fontsize=8,
        ncol=3,
        loc="lower left",
    )
    figure.suptitle("Fixed time order outside; rolling walk-forward inside", weight="bold")
    figure.text(
        0.5,
        0.01,
        "Elastic Net uses the same 60 mature months without a validation split.",
        ha="center",
        fontsize=9,
        color="#333333",
    )
    save(figure, output)


def portfolio_comparison(results: Path, output: Path) -> None:
    frame = pd.read_csv(results / "portfolio_model_comparison.csv")
    evaluation = frame[
        (frame["segment"] == "exploratory_2023_2025") & (frame["cost_bps"] == 30)
    ].set_index("model")
    labels = [
        "CSI 300 EW",
        "PB–ROE",
        "8-factor EW",
        "Elastic Net",
        "LightGBM",
    ]
    returns = [
        evaluation.loc["EligibleEqualWeight", "benchmark_annual_return"] * 100,
        evaluation.loc["PBROE", "net_annual_return"] * 100,
        evaluation.loc["EligibleEqualWeight", "net_annual_return"] * 100,
        evaluation.loc["ElasticNet", "net_annual_return"] * 100,
        evaluation.loc["LightGBM", "net_annual_return"] * 100,
    ]
    sharpes = [
        evaluation.loc["EligibleEqualWeight", "benchmark_sharpe"],
        evaluation.loc["PBROE", "net_sharpe"],
        evaluation.loc["EligibleEqualWeight", "net_sharpe"],
        evaluation.loc["ElasticNet", "net_sharpe"],
        evaluation.loc["LightGBM", "net_sharpe"],
    ]
    drawdowns = [
        evaluation.loc["EligibleEqualWeight", "benchmark_max_drawdown"] * 100,
        evaluation.loc["PBROE", "net_max_drawdown"] * 100,
        evaluation.loc["EligibleEqualWeight", "net_max_drawdown"] * 100,
        evaluation.loc["ElasticNet", "net_max_drawdown"] * 100,
        evaluation.loc["LightGBM", "net_max_drawdown"] * 100,
    ]
    colors = [GRAY, RED, GREEN, BLUE, ORANGE]
    figure, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))
    for axis, values, title, fmt in (
        (axes[0], returns, "Annualized return", "%.2f%%"),
        (axes[1], sharpes, "Sharpe ratio", "%.2f"),
        (axes[2], drawdowns, "Maximum drawdown", "%.1f%%"),
    ):
        bars = axis.bar(range(5), values, color=colors)
        axis.bar_label(bars, fmt=fmt, padding=3, fontsize=9)
        axis.set_xticks(range(5), labels, rotation=18, ha="right")
        axis.set_title(title, weight="bold")
        axis.axhline(0, color="#333333", linewidth=1)
        axis.grid(axis="y", alpha=0.22)
    figure.suptitle(
        "The simple eligible-factor portfolio beats the complex models in exploratory history"
    )
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
    factor_incrementality(results, output / "04-factor-incrementality.png")
    walk_forward_models(results, output / "05-walk-forward-timeline.png")
    portfolio_comparison(results, output / "06-portfolio-comparison.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Dependency-free SVG figures generated only from frozen run outputs."""

# ruff: noqa: E501

from __future__ import annotations

import html
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

WIDTH, HEIGHT = 960, 540
COLORS = ("#2563eb", "#dc2626", "#059669", "#7c3aed")


def _svg(title: str, body: str, x_label: str = "", y_label: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{html.escape(title)}">
<rect width="100%" height="100%" fill="white"/>
<style>text{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;fill:#172033}} .title{{font-size:24px;font-weight:600}} .label{{font-size:14px}} .tick{{font-size:12px;fill:#536078}} .grid{{stroke:#d8dee9;stroke-width:1}} .axis{{stroke:#536078;stroke-width:1.2;fill:none}}</style>
<text x="70" y="38" class="title">{html.escape(title)}</text>
<line x1="80" y1="460" x2="920" y2="460" class="axis"/><line x1="80" y1="70" x2="80" y2="460" class="axis"/>
<text x="500" y="515" text-anchor="middle" class="label">{html.escape(x_label)}</text>
<text x="20" y="265" text-anchor="middle" transform="rotate(-90 20 265)" class="label">{html.escape(y_label)}</text>
{body}</svg>"""


def _line_chart(title: str, series: Iterable[tuple[str, pd.Series]], output: Path) -> Path:
    prepared = [(label, values.dropna().astype(float)) for label, values in series]
    all_values = pd.concat([values for _, values in prepared])
    low, high = float(all_values.min()), float(all_values.max())
    span = high - low or 1.0
    elements: list[str] = []
    for tick in range(5):
        value = low + span * tick / 4
        y = 460 - 390 * tick / 4
        elements.append(f'<line x1="80" y1="{y:.1f}" x2="920" y2="{y:.1f}" class="grid"/>')
        elements.append(
            f'<text x="70" y="{y + 4:.1f}" text-anchor="end" class="tick">{value:.2f}</text>'
        )
    for index, (label, values) in enumerate(prepared):
        count = max(len(values) - 1, 1)
        points = " ".join(
            f"{80 + 840 * i / count:.1f},{460 - 390 * (value - low) / span:.1f}"
            for i, value in enumerate(values)
        )
        color = COLORS[index % len(COLORS)]
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"/>'
        )
        legend_y = 20 + index * 18
        elements.append(
            f'<line x1="650" y1="{legend_y}" x2="670" y2="{legend_y}" stroke="{color}" stroke-width="3"/>'
        )
        elements.append(
            f'<text x="676" y="{legend_y + 5}" class="tick">{html.escape(label)}</text>'
        )
    output.write_text(
        _svg(title, "".join(elements), "Time", "Cumulative net value"), encoding="utf-8"
    )
    return output


def _bar_chart(title: str, labels: list[str], values: list[float], output: Path) -> Path:
    bound = max(max((abs(value) for value in values), default=1.0), 1e-9)
    zero = 580
    scale = 300 / bound
    row_height = min(32, 370 / max(len(labels), 1))
    elements = ['<line x1="580" y1="70" x2="580" y2="460" class="axis"/>']
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 78 + index * row_height
        width = abs(value) * scale
        x = zero if value >= 0 else zero - width
        color = COLORS[0] if value >= 0 else COLORS[1]
        elements.append(
            f'<text x="70" y="{y + row_height * 0.65:.1f}" text-anchor="start" class="tick">{html.escape(label)}</text>'
        )
        elements.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{row_height * 0.68:.1f}" fill="{color}"/>'
        )
        elements.append(
            f'<text x="{x + width + (6 if value >= 0 else -6):.1f}" y="{y + row_height * 0.63:.1f}" text-anchor="{("start" if value >= 0 else "end")}" class="tick">{value:.2f}</text>'
        )
    output.write_text(_svg(title, "".join(elements), "Mean Rank IC (%)", ""), encoding="utf-8")
    return output


def generate_static_figures(
    modern_run_dir: str | Path,
    paper_run_dir: str | Path | None,
    output_dir: str | Path,
) -> list[Path]:
    modern, paper = Path(modern_run_dir), Path(paper_run_dir or modern_run_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    returns = pd.read_parquet(paper / "paper_returns.parquet")
    paper_series = []
    for strategy, label in {
        "R0_UNIVERSE_EW": "CSI300 members EW",
        "R3_PB_ROE_TOP50": "PB-ROE Top50",
        "R4_PB_ROE_INDUSTRY_EW": "PB-ROE industry EW",
    }.items():
        values = returns[returns["strategy_id"] == strategy].sort_values("period_end")["net_return"]
        paper_series.append((label, (1 + values).cumprod()))
    saved = [_line_chart("Paper reproduction", paper_series, output / "paper-reproduction.svg")]

    factors = pd.read_csv(modern / "expanded_factor_ic_summary.csv").sort_values("ic_mean")
    saved.append(
        _bar_chart(
            "Expanded factor Rank IC",
            factors["factor"].tolist(),
            (factors["ic_mean"] * 100).tolist(),
            output / "expanded-factor-ic.svg",
        )
    )

    model_labels, model_values = [], []
    for model, label in (("elastic-net", "Elastic Net"), ("lightgbm", "LightGBM")):
        frame = pd.read_csv(modern / f"{model}_ic_segments.csv").set_index("segment")
        for segment in ("development", "frozen_oos"):
            model_labels.append(f"{label} / {segment}")
            model_values.append(float(frame.loc[segment, "ic_mean"] * 100))
    saved.append(
        _bar_chart(
            "Walk-forward model IC", model_labels, model_values, output / "model-ic-comparison.svg"
        )
    )

    portfolio_series = []
    for model, label in (("elastic-net", "Elastic Net (30bp)"), ("lightgbm", "LightGBM (30bp)")):
        frame = pd.read_csv(modern / f"{model}_optimized_returns.csv")
        portfolio_series.append((label, (1 + frame["net_return_30bp"]).cumprod()))
    benchmark = pd.read_csv(modern / "elastic-net_optimized_returns.csv")
    portfolio_series.append(
        ("CSI300 members EW proxy", (1 + benchmark["benchmark_return"]).cumprod())
    )
    saved.append(
        _line_chart("Constrained portfolio", portfolio_series, output / "portfolio-net-value.svg")
    )
    return saved

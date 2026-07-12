"""Presentation-ready IC analysis cards generated from frozen factor outputs."""

# ruff: noqa: E501

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from pb_roe.evaluation.ic import calculate_ic, summarize_ic

WIDTH, HEIGHT = 1600, 900
LABELS = {
    "momentum_12_1_z": "12–1月动量",
    "reversal_1m_z": "1月反转",
    "beta_252d_z": "低Beta",
    "idiosyncratic_volatility_z": "低特异波动",
    "bp_z": "BP价值",
    "paper_score_z": "PB-ROE综合",
    "equal_weight_score": "六因子等权综合",
}


def _text(x: float, y: float, value: object, css: str = "body", anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="{css}" text-anchor="{anchor}">'
        f"{html.escape(str(value))}</text>"
    )


def _card(feature: str, ic: pd.DataFrame, output: Path, selected: bool) -> Path:
    values = ic.sort_values("signal_date").reset_index(drop=True)
    summary = summarize_ic(values).iloc[0]
    development = values[pd.to_datetime(values["signal_date"]) <= pd.Timestamp("2022-12-31")]
    frozen = values[pd.to_datetime(values["signal_date"]) >= pd.Timestamp("2023-01-01")]
    dev = summarize_ic(development).iloc[0]
    oos = summarize_ic(frozen).iloc[0]
    cumulative = values["ic"].fillna(0).cumsum()
    bar_limit = max(0.15, float(values["ic"].abs().max()) * 1.08)
    cum_low, cum_high = min(0.0, float(cumulative.min())), max(0.1, float(cumulative.max()))
    cum_span = cum_high - cum_low or 1.0
    left, right, top, bottom = 90, 1110, 245, 750
    zero_y = top + (bar_limit / (2 * bar_limit)) * (bottom - top)
    count = len(values)
    step = (right - left) / max(count, 1)
    elements: list[str] = []
    for tick in (-1, -0.5, 0, 0.5, 1):
        value = tick * bar_limit
        y = zero_y - value / (2 * bar_limit) * (bottom - top)
        elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>')
        elements.append(_text(left - 12, y + 5, f"{value:.2f}", "tick", "end"))
    points = []
    for index, value in enumerate(values["ic"].fillna(0)):
        x = left + (index + 0.5) * step
        height = abs(float(value)) / (2 * bar_limit) * (bottom - top)
        y = zero_y - height if value >= 0 else zero_y
        color = "#3977c3" if value >= 0 else "#d45a64"
        elements.append(
            f'<rect x="{x - step * 0.37:.2f}" y="{y:.2f}" width="{step * 0.74:.2f}" height="{height:.2f}" fill="{color}"/>'
        )
        cy = bottom - (float(cumulative.iloc[index]) - cum_low) / cum_span * (bottom - top)
        points.append(f"{x:.2f},{cy:.2f}")
    mean_y = zero_y - float(summary["ic_mean"]) / (2 * bar_limit) * (bottom - top)
    elements.append(
        f'<line x1="{left}" y1="{mean_y:.1f}" x2="{right}" y2="{mean_y:.1f}" class="mean"/>'
    )
    elements.append(
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#1e1b2e" stroke-width="4"/>'
    )
    split_index = int((pd.to_datetime(values["signal_date"]) < pd.Timestamp("2023-01-01")).sum())
    split_x = left + split_index * step
    elements.append(
        f'<line x1="{split_x:.1f}" y1="{top}" x2="{split_x:.1f}" y2="{bottom}" class="split"/>'
    )
    elements.append(_text(split_x + 8, top + 20, "冻结样本外", "tick"))
    for index in range(0, count, 24):
        x = left + (index + 0.5) * step
        label = pd.Timestamp(values.loc[index, "signal_date"]).strftime("%Y")
        elements.append(_text(x, bottom + 28, label, "tick", "middle"))
    slope_note = "冻结期增强" if oos["ic_mean"] > dev["ic_mean"] else "冻结期减弱"
    status = "入选" if selected else "综合基准"
    title = LABELS.get(feature, feature)
    header_metric = (
        f"开发期IC {dev['ic_mean']:.3f}｜ICIR {dev['icir']:.2f}｜"
        f"月胜率 {dev['ic_positive_rate']:.0%}｜NW t {dev['newey_west_t']:.2f}"
    )
    full_ic_label = f"全期 IC：{summary['ic_mean']:.3f}"
    oos_ic_label = f"冻结期 IC：{oos['ic_mean']:.3f}"
    oos_t_label = f"冻结期 NW t：{oos['newey_west_t']:.2f}"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{html.escape(title)} IC分析">
<rect x="0" y="0" width="1600" height="900" fill="#ffffff"/>
<style>.title{{font:700 42px -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;fill:#1e1b2e}} .eyebrow{{font:700 18px -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;fill:#0872c9;letter-spacing:3px}} .metric{{font:700 24px -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;fill:#111827}} .body{{font:18px -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;fill:#283246}} .tick{{font:14px -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;fill:#647084}} .grid{{stroke:#e1e5eb;stroke-width:1}} .axis{{stroke:#5d6572;stroke-width:1.5}} .mean{{stroke:#f07119;stroke-width:3;stroke-dasharray:10 8}} .split{{stroke:#0872c9;stroke-width:2;stroke-dasharray:6 6}} .panel{{fill:#f5f7fa;stroke:#d8dde5;stroke-width:1.5}} .accent{{fill:#0872c9}}</style>
{_text(28, 42, "PART II · 因子评价", "eyebrow")}{_text(28, 102, f"{title}：均值、稳定性、胜率一张图", "title")}
<rect x="25" y="140" width="1120" height="700" rx="18" fill="#fff" stroke="#d8dde5" stroke-width="1.5"/>
{_text(585, 188, header_metric, "metric", "middle")}
<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/><line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>
{"".join(elements)}
{_text(600, 805, "月份（2015–2025）", "body", "middle")}{_text(42, 500, "Rank IC", "body", "middle")}
<rect x="1180" y="140" width="390" height="265" rx="18" class="panel"/>
<rect x="1180" y="140" width="8" height="265" rx="4" class="accent"/>
{_text(1210, 185, "关键指标", "metric")}{_text(1210, 228, f"状态：{status}", "body")}{_text(1210, 265, full_ic_label, "body")}{_text(1210, 302, oos_ic_label, "body")}{_text(1210, 339, oos_t_label, "body")}{_text(1210, 376, f"累计 IC：{cumulative.iloc[-1]:.2f}", "body")}
<rect x="1180" y="430" width="390" height="300" rx="18" class="panel"/>
<rect x="1180" y="430" width="8" height="300" rx="4" class="accent"/>
{_text(1210, 478, "阅读要点", "metric")}{_text(1210, 525, f"• {slope_note}", "body")}{_text(1210, 570, "• 蓝柱为正IC，红柱为负IC", "body")}{_text(1210, 615, "• 黑线看累计预测贡献", "body")}{_text(1210, 660, "• 橙线为全期IC均值", "body")}{_text(1210, 705, "• 虚线右侧不参与因子筛选", "body")}
{_text(1185, 790, "方向已统一：数值越高，预期下月收益越高", "tick")}
</svg>'''
    output.write_text(svg, encoding="utf-8")
    return output


def factor_charts_from_cli(run_dir: str, output_dir: str) -> int:
    run = Path(run_dir)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(run / "model_factor_panel.parquet")
    panel = panel[pd.to_datetime(panel["signal_date"]) >= pd.Timestamp("2015-01-01")].copy()
    selection = json.loads((run / "frozen_factor_selection.json").read_text(encoding="utf-8"))
    directions = selection["selected_directions"]
    generated = []
    oriented = []
    for feature, direction in directions.items():
        column = f"{feature}_oriented"
        panel[column] = panel[feature] * int(direction)
        ic = calculate_ic(panel, [column], return_column="target_return")
        ic["factor"] = feature
        path = output / f"{feature.removesuffix('_z').replace('_', '-')}-ic.svg"
        generated.append(str(_card(feature, ic, path, True)))
        oriented.append(column)
    panel["equal_weight_score"] = panel[oriented].mean(axis=1)
    composite_ic = calculate_ic(panel, ["equal_weight_score"], return_column="target_return")
    generated.append(
        str(_card("equal_weight_score", composite_ic, output / "equal-weight-ic.svg", False))
    )
    print(json.dumps({"generated": generated}, ensure_ascii=False, indent=2))
    return 0

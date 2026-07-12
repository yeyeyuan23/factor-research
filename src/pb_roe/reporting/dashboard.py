"""Self-contained HTML dashboard assembled from frozen result files."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot

CSS = """
:root { color-scheme: dark; --bg:#09111f; --card:#111d30; --ink:#e8eef7;
  --muted:#95a4b8; --accent:#32d3a2; --accent2:#6ea8fe; --warn:#f4c95d; }
* { box-sizing:border-box; }
body { margin:0; background:linear-gradient(135deg,#07101c,#0d1830); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
main { max-width:1400px; margin:auto; padding:32px; }
h1 { font-size:42px; margin:0 0 8px; letter-spacing:-1px; }
h2 { margin:0 0 16px; font-size:22px; }
.subtitle { color:var(--muted); margin-bottom:28px; }
.grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }
.card { background:rgba(17,29,48,.94); border:1px solid #243551; border-radius:16px;
  padding:20px; box-shadow:0 12px 32px rgba(0,0,0,.22); min-height:260px; }
.wide { grid-column:1/-1; }
.metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px; }
.metric { padding:15px; border-radius:12px; background:#0c1728; border:1px solid #21324c; }
.metric strong { display:block; font-size:25px; color:var(--accent); }
.metric span { color:var(--muted); font-size:13px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th,td { padding:8px; text-align:left; border-bottom:1px solid #273852; }
th { color:var(--accent2); }
.note { color:var(--muted); font-size:13px; line-height:1.55; }
@media(max-width:900px){
  .grid{grid-template-columns:1fr}
  .wide{grid-column:auto}
  .metrics{grid-template-columns:1fr 1fr}
}
"""


def _read_csv(run_dir: Path, name: str) -> pd.DataFrame:
    path = run_dir / name
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def _read_json(run_dir: Path, name: str) -> dict[str, object]:
    path = run_dir / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _figure_html(figure: go.Figure, include_plotlyjs: bool = False) -> str:
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=45, r=25, t=25, b=40),
        legend=dict(orientation="h", y=1.08),
        font=dict(color="#dce7f5"),
    )
    return plot(
        figure,
        include_plotlyjs="inline" if include_plotlyjs else False,
        output_type="div",
        config={"displaylogo": False, "responsive": True},
    )


def _paper_figure(run_dir: Path) -> go.Figure:
    path = run_dir / "paper_returns.parquet"
    frame = pd.read_parquet(path) if path.is_file() else pd.DataFrame()
    figure = go.Figure()
    if frame.empty:
        return figure
    preferred = [
        "R0_UNIVERSE_EW",
        "R1_ROE_TOP20",
        "R2_PB_TOP50",
        "R3_PB_ROE_TOP50",
        "R4_PB_ROE_INDUSTRY_EW",
    ]
    for strategy in preferred:
        periods = frame[frame["strategy_id"] == strategy].sort_values("period_end")
        if periods.empty:
            continue
        figure.add_trace(
            go.Scatter(
                x=periods["period_end"],
                y=(1 + periods["net_return"]).cumprod(),
                mode="lines+markers",
                name=strategy,
            )
        )
    figure.update_yaxes(title="累计净值")
    return figure


def _ic_figure(run_dir: Path) -> go.Figure:
    frame = _read_csv(run_dir, "ic_summary.csv")
    figure = go.Figure()
    if not frame.empty:
        figure.add_bar(x=frame["factor"], y=frame["ic_mean"], name="IC Mean")
        figure.add_scatter(
            x=frame["factor"],
            y=frame["newey_west_t"],
            name="Newey-West t",
            mode="markers",
            yaxis="y2",
            marker=dict(size=11, color="#f4c95d"),
        )
        figure.update_layout(yaxis2=dict(overlaying="y", side="right", title="t 值"))
    return figure


def _spread_figure(run_dir: Path) -> go.Figure:
    frame = _read_csv(run_dir, "long_short_spreads.csv")
    figure = go.Figure()
    for factor, group in frame.groupby("factor") if not frame.empty else []:
        group = group.sort_values("signal_date")
        figure.add_scatter(
            x=group["signal_date"],
            y=(1 + group["net_spread"]).cumprod(),
            mode="lines",
            name=factor,
        )
    return figure


def _model_ic_figure(run_dir: Path) -> go.Figure:
    rows: list[dict[str, object]] = []
    for model in ("elastic-net", "lightgbm"):
        frame = _read_csv(run_dir, f"{model}_ic_summary.csv")
        if not frame.empty:
            row = frame.iloc[0]
            rows.append({"model": model, "ic_mean": row["ic_mean"], "icir": row["icir"]})
    figure = go.Figure()
    if rows:
        comparison = pd.DataFrame(rows)
        figure.add_bar(x=comparison["model"], y=comparison["ic_mean"], name="IC Mean")
        figure.add_bar(x=comparison["model"], y=comparison["icir"], name="ICIR")
        figure.update_layout(barmode="group")
    return figure


def _importance_figure(run_dir: Path) -> go.Figure:
    frame = _read_csv(run_dir, "lightgbm_diagnostics.csv")
    figure = go.Figure()
    if not frame.empty:
        importance = frame.groupby("feature")["importance_gain"].mean().sort_values()
        figure.add_bar(x=importance.values, y=importance.index, orientation="h")
    return figure


def _optimization_figure(run_dir: Path) -> go.Figure:
    figure = go.Figure()
    for model, label in (("elastic-net", "Elastic Net"), ("lightgbm", "LightGBM")):
        frame = _read_csv(run_dir, f"{model}_optimized_returns.csv")
        if frame.empty:
            continue
        figure.add_scatter(
            x=frame["signal_date"],
            y=(1 + frame["net_return_30bp"]).cumprod(),
            name=f"{label}（30bp）",
            mode="lines",
        )
    benchmark = _read_csv(run_dir, "elastic-net_optimized_returns.csv")
    if not benchmark.empty:
        figure.add_scatter(
            x=benchmark["signal_date"],
            y=(1 + benchmark["benchmark_return"]).cumprod(),
            name="沪深300成员等权代理",
            mode="lines",
            line=dict(dash="dash"),
        )
    figure.update_yaxes(title="累计净值")
    return figure


def _audit_table(run_dir: Path) -> str:
    audit = _read_json(run_dir, "data_audit.json")
    checks = pd.DataFrame(audit.get("checks", []))
    if checks.empty:
        return '<p class="note">未找到数据审计结果。</p>'
    columns = ["check_id", "passed", "observed", "threshold"]
    return checks[columns].to_html(index=False, escape=True, border=0)


def generate_dashboard(
    run_dir: str | Path,
    output_file: str | Path,
    paper_run_dir: str | Path | None = None,
) -> Path:
    run_path = Path(run_dir).expanduser().resolve()
    output = Path(output_file).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    evaluation = _read_json(run_path, "evaluation_run.json")
    paper_path = Path(paper_run_dir).expanduser().resolve() if paper_run_dir else run_path
    optimization = _read_json(run_path, "elastic-net_optimization_run.json")
    paper = _read_json(paper_path, "paper_run.json")
    metric_items = [
        ("复现调仓期", len(paper.get("signal_dates", []))),
        ("现代有效月份", evaluation.get("signal_dates", "-")),
        ("优化月份", optimization.get("months", "-")),
        ("优化回退次数", optimization.get("fallback_months", "-")),
    ]
    metrics = "".join(
        f'<div class="metric"><strong>{html.escape(str(value))}</strong>'
        f"<span>{html.escape(label)}</span></div>"
        for label, value in metric_items
    )
    figures = [
        ("原研报策略方向性复现", _paper_figure(paper_path)),
        ("因子 IC 与显著性", _ic_figure(run_path)),
        ("Top-Bottom 成本后净值", _spread_figure(run_path)),
        ("Elastic Net vs LightGBM", _model_ic_figure(run_path)),
        ("LightGBM 平均特征重要性", _importance_figure(run_path)),
        ("约束优化组合", _optimization_figure(run_path)),
    ]
    cards: list[str] = []
    for index, (title, figure) in enumerate(figures):
        cards.append(
            f'<section class="card"><h2>{html.escape(title)}</h2>'
            f"{_figure_html(figure, include_plotlyjs=index == 0)}</section>"
        )
    cards.append(
        '<section class="card wide"><h2>Research Data Quality Gate</h2>'
        f"{_audit_table(run_path)}</section>"
    )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>PB-ROE Alpha Research Dashboard</title><style>{CSS}</style></head>
<body><main><h1>PB-ROE Alpha Research</h1>
<p class="subtitle">原文复现 · Point-in-Time · 现代因子评价 · 非线性增强 · 风险约束</p>
<div class="metrics">{metrics}</div><div class="grid">{"".join(cards)}</div>
<p class="note">本页面读取冻结结果生成，Plotly 运行库已内嵌，可完全离线展示。</p>
</main></body></html>"""
    output.write_text(document, encoding="utf-8")
    return output

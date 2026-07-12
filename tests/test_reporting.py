import json

import pandas as pd

from pb_roe.reporting.dashboard import generate_dashboard
from pb_roe.reporting.static import generate_static_figures


def test_dashboard_is_self_contained_and_contains_core_sections(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "paper_run.json").write_text(
        json.dumps({"signal_dates": ["2022-04-29"]}), encoding="utf-8"
    )
    (run_dir / "evaluation_run.json").write_text(json.dumps({"signal_dates": 1}), encoding="utf-8")
    (run_dir / "optimization_run.json").write_text(
        json.dumps({"months": 1, "fallback_months": 0}), encoding="utf-8"
    )
    (run_dir / "data_audit.json").write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "check_id": "prices.ohlc_logic",
                        "passed": True,
                        "observed": 0,
                        "threshold": 0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        {
            "strategy_id": ["R0_UNIVERSE_EW"],
            "period_end": ["2022-08-31"],
            "net_return": [0.01],
        }
    ).to_parquet(run_dir / "paper_returns.parquet", index=False)
    output = tmp_path / "dashboard.html"

    generate_dashboard(run_dir, output)

    content = output.read_text(encoding="utf-8")
    assert "PB-ROE Alpha Research" in content
    assert "Research Data Quality Gate" in content
    assert "plotly.js" in content.lower()
    assert 'src="https://cdn.plot.ly' not in content


def test_static_figures_are_generated_from_frozen_results(tmp_path) -> None:
    modern = tmp_path / "modern"
    paper = tmp_path / "paper"
    output = tmp_path / "figures"
    modern.mkdir()
    paper.mkdir()
    pd.DataFrame(
        {
            "strategy_id": ["R0_UNIVERSE_EW", "R3_PB_ROE_TOP50", "R4_PB_ROE_INDUSTRY_EW"],
            "period_end": ["2010-01-31"] * 3,
            "net_return": [0.01, 0.02, 0.015],
        }
    ).to_parquet(paper / "paper_returns.parquet", index=False)
    pd.DataFrame({"factor": ["bp", "roe"], "ic_mean": [0.04, 0.01]}).to_csv(
        modern / "expanded_factor_ic_summary.csv", index=False
    )
    for model in ("elastic-net", "lightgbm"):
        pd.DataFrame({"segment": ["development", "frozen_oos"], "ic_mean": [0.03, 0.05]}).to_csv(
            modern / f"{model}_ic_segments.csv", index=False
        )
        pd.DataFrame(
            {
                "signal_date": ["2023-01-31"],
                "net_return_30bp": [0.01],
                "benchmark_return": [0.005],
            }
        ).to_csv(modern / f"{model}_optimized_returns.csv", index=False)

    paths = generate_static_figures(modern, paper, output)

    assert len(paths) == 4
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)

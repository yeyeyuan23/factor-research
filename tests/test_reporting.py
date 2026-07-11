import json

import pandas as pd

from pb_roe.reporting.dashboard import generate_dashboard


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

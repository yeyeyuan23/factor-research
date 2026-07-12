"""CLI wrapper for offline reporting."""

from __future__ import annotations

import json
from pathlib import Path

from pb_roe.config import load_config
from pb_roe.reporting.dashboard import generate_dashboard
from pb_roe.reporting.static import generate_static_figures


def report_from_cli(
    config_path: str,
    run_dir: str | None,
    paper_run_dir: str | None = None,
    static_dir: str | None = None,
) -> int:
    config = load_config(config_path)
    source = Path(run_dir).resolve() if run_dir else config.output_dir()
    paper_source = Path(paper_run_dir).resolve() if paper_run_dir else None
    output = source / "dashboard.html"
    generate_dashboard(source, output, paper_source)
    figures = (
        generate_static_figures(source, paper_source, Path(static_dir).resolve())
        if static_dir
        else []
    )
    metadata = {
        "run_id": config.run_id,
        "dashboard": str(output),
        "static_figures": [str(path) for path in figures],
        "offline": True,
    }
    (source / "report_run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0

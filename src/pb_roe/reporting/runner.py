"""CLI wrapper for offline reporting."""

from __future__ import annotations

import json
from pathlib import Path

from pb_roe.config import load_config
from pb_roe.reporting.dashboard import generate_dashboard


def report_from_cli(config_path: str, run_dir: str | None) -> int:
    config = load_config(config_path)
    source = Path(run_dir).resolve() if run_dir else config.output_dir()
    output = source / "dashboard.html"
    generate_dashboard(source, output)
    metadata = {"run_id": config.run_id, "dashboard": str(output), "offline": True}
    (source / "report_run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0

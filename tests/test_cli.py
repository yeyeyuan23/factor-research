import json
from pathlib import Path

from pb_roe.cli import main

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_config_check_outputs_summary(capsys) -> None:
    config = REPOSITORY_ROOT / "configs" / "smoke.yaml"

    exit_code = main(["config-check", "--config", str(config)])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["run_id"] == "smoke"
    assert output["mode"] == "smoke"

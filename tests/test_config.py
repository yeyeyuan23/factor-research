from pathlib import Path

import pytest

from pb_roe.config import ConfigError, load_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["paper.yaml", "modern.yaml", "smoke.yaml"])
def test_project_configs_are_valid(name: str) -> None:
    config = load_config(REPOSITORY_ROOT / "configs" / name)

    assert config.run_id
    assert config.mode
    assert len(config.fingerprint) == 16


def test_fingerprint_is_deterministic() -> None:
    path = REPOSITORY_ROOT / "configs" / "paper.yaml"
    assert load_config(path).fingerprint == load_config(path).fingerprint


def test_missing_config_raises() -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(REPOSITORY_ROOT / "configs" / "missing.yaml")

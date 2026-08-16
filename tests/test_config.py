from pathlib import Path

import pytest
import yaml

from pb_roe.config import ConfigError, load_config

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _minimal_config() -> dict:
    return {
        "project": {"run_id": "test", "mode": "smoke"},
        "data": {},
        "universe": {"id": "CSI300"},
        "research": {},
        "costs": {},
        "quality": {
            "membership_coverage": 0.8,
            "announcement_coverage": 0.8,
            "factor_coverage": 0.8,
        },
    }


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


def test_non_mapping_section_raises(tmp_path: Path) -> None:
    values = _minimal_config()
    values["universe"] = "CSI300"
    path = tmp_path / "broken.yaml"
    path.write_text(yaml.safe_dump(values))
    with pytest.raises(ConfigError, match="must be mappings"):
        load_config(path)


def test_missing_universe_id_raises(tmp_path: Path) -> None:
    values = _minimal_config()
    del values["universe"]["id"]
    path = tmp_path / "broken.yaml"
    path.write_text(yaml.safe_dump(values))
    with pytest.raises(ConfigError, match="universe.id"):
        load_config(path)

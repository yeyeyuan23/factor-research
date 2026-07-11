"""Configuration loading and validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a research configuration is incomplete or inconsistent."""


REQUIRED_SECTIONS = ("project", "data", "universe", "research", "costs", "quality")


@dataclass(frozen=True)
class ResearchConfig:
    """Validated configuration plus its source and deterministic fingerprint."""

    source: Path
    values: dict[str, Any]
    fingerprint: str

    @property
    def run_id(self) -> str:
        return str(self.values["project"]["run_id"])

    @property
    def mode(self) -> str:
        return str(self.values["project"]["mode"])

    def section(self, name: str) -> Mapping[str, Any]:
        try:
            section = self.values[name]
        except KeyError as exc:
            raise ConfigError(f"Missing config section: {name}") from exc
        if not isinstance(section, Mapping):
            raise ConfigError(f"Config section must be a mapping: {name}")
        return section

    def output_dir(self, repository_root: Path | None = None) -> Path:
        base = repository_root or self.source.parent.parent
        configured = Path(str(self.section("data")["results_dir"]))
        return (base / configured / self.run_id).resolve()


def _canonical_json(values: Mapping[str, Any]) -> str:
    return json.dumps(
        values,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value),
    )


def _validate(values: Any) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise ConfigError("Configuration root must be a mapping")
    missing = [section for section in REQUIRED_SECTIONS if section not in values]
    if missing:
        raise ConfigError(f"Missing config sections: {', '.join(missing)}")

    project = values["project"]
    if not isinstance(project, dict) or not project.get("run_id") or not project.get("mode"):
        raise ConfigError("project.run_id and project.mode are required")

    quality = values["quality"]
    if not isinstance(quality, dict):
        raise ConfigError("quality must be a mapping")
    for name in ("membership_coverage", "announcement_coverage", "factor_coverage"):
        threshold = quality.get(name)
        if not isinstance(threshold, int | float) or not 0 <= float(threshold) <= 1:
            raise ConfigError(f"quality.{name} must be between 0 and 1")

    return values


def load_config(path: str | Path) -> ResearchConfig:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ConfigError(f"Configuration file does not exist: {source}")
    with source.open("r", encoding="utf-8") as handle:
        values = _validate(yaml.safe_load(handle))
    fingerprint = hashlib.sha256(_canonical_json(values).encode("utf-8")).hexdigest()[:16]
    return ResearchConfig(source=source, values=values, fingerprint=fingerprint)

"""Research data quality gates and CLI reporting."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from pb_roe.config import load_config
from pb_roe.data.bundle import DataBundle
from pb_roe.data.pit import active_members
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.data.schema import PRIMARY_KEYS, SCHEMAS, require_columns
from pb_roe.data.store import ParquetStore


@dataclass(frozen=True)
class AuditCheck:
    check_id: str
    table_name: str
    severity: str
    passed: bool
    observed: Any
    threshold: Any
    details: str = ""


@dataclass(frozen=True)
class AuditReport:
    checks: tuple[AuditCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks if check.severity == "error")

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "checks": [asdict(check) for check in self.checks]}

    def write_json(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _duplicate_check(name: str, frame: pd.DataFrame) -> AuditCheck:
    keys = PRIMARY_KEYS[name]
    require_columns(frame, keys, name)
    duplicate_count = int(frame.duplicated(list(keys), keep=False).sum())
    return AuditCheck(
        check_id=f"{name}.primary_key_unique",
        table_name=name,
        severity="error",
        passed=duplicate_count == 0,
        observed=duplicate_count,
        threshold=0,
    )


def _schema_check(name: str, frame: pd.DataFrame) -> AuditCheck:
    missing = sorted(set(SCHEMAS[name]) - set(frame.columns))
    return AuditCheck(
        check_id=f"{name}.schema",
        table_name=name,
        severity="error",
        passed=not missing,
        observed=missing,
        threshold="no missing columns",
    )


def _ohlc_check(prices: pd.DataFrame) -> AuditCheck:
    require_columns(
        prices,
        ("open", "high", "low", "close", "volume", "is_suspended"),
        "prices",
    )
    price_columns = ["open", "high", "low", "close"]
    tradable = ~prices["is_suspended"].fillna(False)
    tradable_prices = prices.loc[tradable, price_columns]
    invalid_tradable = (
        tradable_prices.isna().any(axis=1)
        | tradable_prices.le(0).any(axis=1)
        | (tradable_prices["high"] < tradable_prices[["open", "close", "low"]].max(axis=1))
        | (tradable_prices["low"] > tradable_prices[["open", "close", "high"]].min(axis=1))
        | prices.loc[tradable, "volume"].isna()
        | prices.loc[tradable, "volume"].lt(0)
    )
    invalid_suspended = prices.loc[~tradable, price_columns].lt(0).any(axis=1)
    invalid = pd.concat((invalid_tradable, invalid_suspended))
    count = int(invalid.sum())
    return AuditCheck("prices.ohlc_logic", "prices", "error", count == 0, count, 0)


def _announcement_coverage(fundamentals: pd.DataFrame, threshold: float) -> AuditCheck:
    require_columns(fundamentals, ("announce_date", "effective_date"), "fundamentals")
    coverage = float(fundamentals[["announce_date", "effective_date"]].notna().all(axis=1).mean())
    return AuditCheck(
        "fundamentals.announcement_coverage",
        "fundamentals",
        "error",
        coverage >= threshold,
        round(coverage, 6),
        threshold,
    )


def _effective_date_check(fundamentals: pd.DataFrame) -> AuditCheck:
    report = pd.to_datetime(fundamentals["report_period"])
    effective = pd.to_datetime(fundamentals["effective_date"])
    invalid = int((effective < report).sum())
    return AuditCheck(
        "fundamentals.effective_after_period",
        "fundamentals",
        "error",
        invalid == 0,
        invalid,
        0,
    )


def _membership_interval_check(membership: pd.DataFrame) -> AuditCheck:
    member_from = pd.to_datetime(membership["member_from"])
    member_to = pd.to_datetime(membership["member_to"])
    invalid = int((member_to.notna() & (member_to <= member_from)).sum())
    return AuditCheck(
        "universe_membership.valid_intervals",
        "universe_membership",
        "error",
        invalid == 0,
        invalid,
        0,
    )


def _membership_coverage_check(
    membership: pd.DataFrame,
    universe_id: str,
    expected_size: int,
    threshold: float,
    as_of: object,
) -> AuditCheck:
    member_count = len(active_members(membership, pd.Timestamp(as_of), universe_id))
    coverage = member_count / expected_size if expected_size else 0.0
    return AuditCheck(
        "universe_membership.coverage",
        "universe_membership",
        "error",
        coverage >= threshold,
        round(coverage, 6),
        threshold,
        f"{member_count}/{expected_size} active members on {pd.Timestamp(as_of).date()}",
    )


def audit_bundle(
    bundle: DataBundle,
    announcement_threshold: float = 0.95,
    membership_expected_size: int | None = None,
    membership_threshold: float = 0.95,
    membership_as_of: object | None = None,
    universe_id: str = "CSI300",
) -> AuditReport:
    checks: list[AuditCheck] = []
    for name, frame in bundle.tables().items():
        checks.append(_schema_check(name, frame))
        if not checks[-1].passed:
            continue
        checks.append(_duplicate_check(name, frame))
    checks.extend(
        (
            _ohlc_check(bundle.prices),
            _announcement_coverage(bundle.fundamentals, announcement_threshold),
            _effective_date_check(bundle.fundamentals),
            _membership_interval_check(bundle.universe_membership),
        )
    )
    if membership_expected_size is not None:
        as_of = membership_as_of or bundle.prices["trade_date"].max()
        checks.append(
            _membership_coverage_check(
                bundle.universe_membership,
                universe_id,
                membership_expected_size,
                membership_threshold,
                as_of,
            )
        )
    return AuditReport(tuple(checks))


def audit_from_cli(config_path: str, input_dir: str | None) -> int:
    config = load_config(config_path)
    provider_names = config.section("data").get("providers", {})
    if input_dir:
        bundle = ParquetStore(input_dir, immutable=False).read_bundle()
    elif all(value == "fixture" for value in provider_names.values()):
        bundle = fixture_bundle()
    else:
        raise FileNotFoundError(
            "--input-dir is required unless all configured providers are fixture"
        )
    quality = config.section("quality")
    universe = config.section("universe")
    research = config.section("research")
    report = audit_bundle(
        bundle,
        announcement_threshold=float(quality["announcement_coverage"]),
        membership_expected_size=int(universe["expected_size"]),
        membership_threshold=float(quality["membership_coverage"]),
        membership_as_of=research["end_date"],
        universe_id=str(universe["id"]),
    )
    output = config.output_dir() / "data_audit.json"
    report.write_json(output)
    print(json.dumps({**report.to_dict(), "output": str(output)}, ensure_ascii=False, indent=2))
    return 0 if report.passed else 1

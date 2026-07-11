"""Canonical schema definitions and normalization helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

SCHEMAS: dict[str, tuple[str, ...]] = {
    "security_master": (
        "security_id",
        "exchange",
        "symbol",
        "name",
        "list_date",
        "delist_date",
        "source",
    ),
    "trading_calendar": ("trade_date", "is_open", "previous_open_date", "next_open_date"),
    "universe_membership": (
        "universe_id",
        "security_id",
        "member_from",
        "member_to",
        "weight",
        "industry",
        "source",
    ),
    "prices": (
        "trade_date",
        "security_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "adjustment_factor",
        "is_suspended",
        "is_st",
        "limit_status",
        "source",
    ),
    "fundamentals": (
        "security_id",
        "report_period",
        "announce_date",
        "revision_date",
        "effective_date",
        "metric",
        "value",
        "unit",
        "statement_type",
        "source",
    ),
}

DATE_COLUMNS = {
    "list_date",
    "delist_date",
    "trade_date",
    "previous_open_date",
    "next_open_date",
    "member_from",
    "member_to",
    "report_period",
    "announce_date",
    "revision_date",
    "effective_date",
    "signal_date",
}

PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "security_master": ("security_id",),
    "trading_calendar": ("trade_date",),
    "universe_membership": ("universe_id", "security_id", "member_from", "source"),
    "prices": ("trade_date", "security_id", "source"),
    "fundamentals": (
        "security_id",
        "report_period",
        "effective_date",
        "metric",
        "source",
    ),
}


class SchemaError(ValueError):
    """Raised when canonical input data violates its declared schema."""


def canonical_security_id(value: object) -> str:
    text = str(value).strip().upper()
    match = re.fullmatch(r"(?:(SH|SZ|BJ)[.\-]?)?(\d{6})(?:[.\-]?(SH|SZ|BJ))?", text)
    if not match:
        raise SchemaError(f"Unsupported security code: {value!r}")
    prefix, symbol, suffix = match.groups()
    exchange = suffix or prefix
    if exchange is None:
        exchange = (
            "SH" if symbol.startswith(("5", "6", "9")) else "BJ" if symbol.startswith("8") else "SZ"
        )
    return f"{symbol}.{exchange}"


def require_columns(frame: pd.DataFrame, required: Iterable[str], table_name: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise SchemaError(f"{table_name} missing columns: {', '.join(missing)}")


def normalize_table(table_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    if table_name not in SCHEMAS:
        raise SchemaError(f"Unknown table: {table_name}")
    require_columns(frame, SCHEMAS[table_name], table_name)
    normalized = frame.loc[:, SCHEMAS[table_name]].copy()
    if "security_id" in normalized:
        normalized["security_id"] = normalized["security_id"].map(canonical_security_id)
    for column in set(normalized.columns) & DATE_COLUMNS:
        normalized[column] = pd.to_datetime(normalized[column], errors="coerce").dt.normalize()
    return normalized

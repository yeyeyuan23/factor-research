"""Immutable Parquet storage with content manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from pb_roe.data.bundle import DataBundle
from pb_roe.data.schema import normalize_table


@dataclass(frozen=True)
class StoredTable:
    name: str
    path: Path
    rows: int
    sha256: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ParquetStore:
    """Writes canonical tables once and rejects accidental raw-data overwrites."""

    def __init__(self, root: str | Path, immutable: bool = True) -> None:
        self.root = Path(root).expanduser().resolve()
        self.immutable = immutable

    def write(self, name: str, frame: pd.DataFrame, overwrite: bool = False) -> StoredTable:
        normalized = normalize_table(name, frame)
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{name}.parquet"
        if path.exists() and self.immutable and not overwrite:
            raise FileExistsError(f"Immutable table already exists: {path}")
        normalized.to_parquet(path, index=False)
        stored = StoredTable(name=name, path=path, rows=len(normalized), sha256=file_sha256(path))
        self._write_manifest(stored)
        return stored

    def read(self, name: str) -> pd.DataFrame:
        path = self.root / f"{name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        return normalize_table(name, pd.read_parquet(path))

    def write_bundle(self, bundle: DataBundle, overwrite: bool = False) -> list[StoredTable]:
        return [
            self.write(name, table, overwrite=overwrite) for name, table in bundle.tables().items()
        ]

    def read_bundle(self) -> DataBundle:
        return DataBundle(**{name: self.read(name) for name in DataBundle.__dataclass_fields__})

    def _write_manifest(self, stored: StoredTable) -> None:
        manifest_path = self.root / "manifest.json"
        manifest = {"created_at": datetime.now(UTC).isoformat(), "tables": {}}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["updated_at"] = datetime.now(UTC).isoformat()
        manifest.setdefault("tables", {})[stored.name] = {
            "file": stored.path.name,
            "rows": stored.rows,
            "sha256": stored.sha256,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

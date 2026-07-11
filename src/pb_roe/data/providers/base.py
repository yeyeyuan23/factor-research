"""Provider protocol shared by network and fixture sources."""

from __future__ import annotations

from datetime import date
from typing import Protocol

import pandas as pd


class ProviderError(RuntimeError):
    """Raised when a source is unavailable or returns an unsupported schema."""


class DataProvider(Protocol):
    name: str

    def fetch_prices(self, security_id: str, start_date: date, end_date: date) -> pd.DataFrame: ...

    def fetch_membership(self, universe_id: str, as_of: date) -> pd.DataFrame: ...

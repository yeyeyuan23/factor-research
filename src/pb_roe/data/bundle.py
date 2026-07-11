"""Canonical in-memory datasets used by research stages."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataBundle:
    security_master: pd.DataFrame
    trading_calendar: pd.DataFrame
    universe_membership: pd.DataFrame
    prices: pd.DataFrame
    fundamentals: pd.DataFrame

    def tables(self) -> dict[str, pd.DataFrame]:
        return {
            "security_master": self.security_master,
            "trading_calendar": self.trading_calendar,
            "universe_membership": self.universe_membership,
            "prices": self.prices,
            "fundamentals": self.fundamentals,
        }

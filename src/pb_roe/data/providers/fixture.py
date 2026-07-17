"""Deterministic smoke dataset that exercises PIT and audit behavior."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pb_roe.data.bundle import DataBundle


def fixture_bundle() -> DataBundle:
    securities = ["000001.SZ", "000002.SZ", "600000.SH", "600001.SH", "600002.SH"]
    security_master = pd.DataFrame(
        {
            "security_id": securities,
            "exchange": [value[-2:] for value in securities],
            "symbol": [value[:6] for value in securities],
            "name": [f"Fixture {index}" for index in range(len(securities))],
            "list_date": pd.Timestamp("2010-01-01"),
            "delist_date": pd.NaT,
            "source": "fixture",
        }
    )
    # One extra year is retained as price-factor warm-up for 12-1 momentum.
    dates = pd.bdate_range("2021-01-04", "2023-12-29")
    trading_calendar = pd.DataFrame(
        {
            "trade_date": dates,
            "is_open": True,
            "previous_open_date": pd.Series(dates).shift(1),
            "next_open_date": pd.Series(dates).shift(-1),
        }
    )
    universe_membership = pd.DataFrame(
        {
            "universe_id": "CSI300",
            "security_id": securities,
            "member_from": pd.Timestamp("2020-01-01"),
            "member_to": pd.NaT,
            "weight": 1 / len(securities),
            "industry": ["Bank", "Property", "Bank", "Industry", "Industry"],
            "source": "fixture",
        }
    )
    price_rows: list[dict[str, object]] = []
    for security_index, security_id in enumerate(securities):
        base = 8 + security_index * 2
        for date_index, trade_date in enumerate(dates):
            close = base * (
                1 + 0.0003 * date_index + 0.01 * np.sin(date_index / 17 + security_index)
            )
            open_price = close * (1 - 0.001)
            price_rows.append(
                {
                    "trade_date": trade_date,
                    "security_id": security_id,
                    "open": open_price,
                    "high": max(open_price, close) * 1.005,
                    "low": min(open_price, close) * 0.995,
                    "close": close,
                    "volume": 1_000_000 + security_index * 100_000,
                    "amount": close * (1_000_000 + security_index * 100_000),
                    "adjustment_factor": 1.0,
                    "is_suspended": False,
                    "is_st": False,
                    "limit_status": "none",
                    "source": "fixture",
                }
            )
    prices = pd.DataFrame(price_rows)
    fundamental_rows: list[dict[str, object]] = []
    for security_index, security_id in enumerate(securities):
        for period_index, (period, announce_date) in enumerate(
            (
                ("2021-03-31", "2021-04-28"),
                ("2021-06-30", "2021-08-25"),
                ("2021-09-30", "2021-10-25"),
                ("2021-12-31", "2022-04-15"),
                ("2022-03-31", "2022-04-28"),
                ("2022-06-30", "2022-08-25"),
                ("2022-09-30", "2022-10-25"),
                ("2022-12-31", "2023-04-15"),
                ("2023-03-31", "2023-04-27"),
                ("2023-06-30", "2023-08-24"),
                ("2023-09-30", "2023-10-25"),
            )
        ):
            quarter = pd.Timestamp(period).quarter
            cumulative_fraction = quarter / 4
            for metric, value, unit in (
                ("pb", 0.8 + security_index * 0.35, "ratio"),
                ("roe", 0.05 + security_index * 0.025, "ratio"),
                (
                    "eps_cumulative",
                    cumulative_fraction * (0.7 + security_index * 0.12)
                    + 0.01 * (period_index // 4),
                    "CNY/share",
                ),
                (
                    "operating_cash_flow_per_share",
                    cumulative_fraction * (0.9 + security_index * 0.10)
                    + 0.015 * (period_index // 4),
                    "CNY/share",
                ),
                (
                    "revenue_growth",
                    0.04 + security_index * 0.012 + 0.002 * (period_index // 4),
                    "ratio",
                ),
            ):
                fundamental_rows.append(
                    {
                        "security_id": security_id,
                        "report_period": period,
                        "announce_date": announce_date,
                        "revision_date": pd.NaT,
                        "effective_date": announce_date,
                        "metric": metric,
                        "value": value,
                        "unit": unit,
                        "statement_type": "consolidated",
                        "source": "fixture",
                    }
                )
    fundamentals = pd.DataFrame(fundamental_rows)
    return DataBundle(
        security_master=security_master,
        trading_calendar=trading_calendar,
        universe_membership=universe_membership,
        prices=prices,
        fundamentals=fundamentals,
    )

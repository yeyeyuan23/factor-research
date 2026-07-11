"""End-to-end runner for original paper reproduction."""

from __future__ import annotations

import json

from pb_roe.config import load_config
from pb_roe.data.audit import audit_bundle
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.data.store import ParquetStore
from pb_roe.reproduction.backtest import backtest_paper_holdings, summarize_paper_returns
from pb_roe.reproduction.factors import build_paper_factor_panel
from pb_roe.reproduction.schedule import DEFAULT_MONTH_DAYS, paper_rebalance_dates
from pb_roe.reproduction.strategies import build_paper_holdings


def reproduce_from_cli(config_path: str, input_dir: str | None) -> int:
    config = load_config(config_path)
    data_config = config.section("data")
    providers = data_config.get("providers", {})
    if input_dir:
        bundle = ParquetStore(input_dir, immutable=False).read_bundle()
    elif all(value == "fixture" for value in providers.values()):
        bundle = fixture_bundle()
    else:
        raise FileNotFoundError("--input-dir is required unless all providers are fixture")

    quality = config.section("quality")
    report = audit_bundle(
        bundle,
        announcement_threshold=float(quality["announcement_coverage"]),
    )
    if not report.passed:
        raise ValueError("Data quality gates failed; reproduction was not started")

    research = config.section("research")
    calendar = bundle.trading_calendar.loc[bundle.trading_calendar["is_open"], "trade_date"]
    signal_dates = paper_rebalance_dates(
        research["start_date"],
        research["end_date"],
        calendar,
        research.get("rebalance_month_days", DEFAULT_MONTH_DAYS),
    )
    if not signal_dates:
        raise ValueError("No paper rebalance dates exist in the configured interval")
    panel = build_paper_factor_panel(
        signal_dates,
        bundle.universe_membership,
        bundle.fundamentals,
        universe_id=str(config.section("universe")["id"]),
    )
    holdings = build_paper_holdings(panel, int(research.get("industry_top_n", 5)))
    costs = config.section("costs")
    initial_cost = float(costs.get("initial_rate", costs.get("base_rate", 0.0)))
    rebalance_cost = float(costs.get("rebalance_rate", costs.get("base_rate", 0.0)))
    returns = backtest_paper_holdings(
        holdings,
        bundle.prices,
        research["end_date"],
        initial_cost=initial_cost,
        rebalance_cost=rebalance_cost,
    )
    summary = summarize_paper_returns(returns)

    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output / "paper_factor_panel.parquet", index=False)
    holdings.to_parquet(output / "paper_holdings.parquet", index=False)
    returns.to_parquet(output / "paper_returns.parquet", index=False)
    summary.to_csv(output / "paper_summary.csv", index=False)
    metadata = {
        "run_id": config.run_id,
        "config_fingerprint": config.fingerprint,
        "signal_dates": [value.date().isoformat() for value in signal_dates],
        "strategies": sorted(returns["strategy_id"].unique().tolist()),
        "output": str(output),
    }
    (output / "paper_run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0

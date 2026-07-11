"""End-to-end optimized portfolio runner."""

from __future__ import annotations

import json

import pandas as pd

from pb_roe.config import load_config
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.models.dataset import load_model_panel
from pb_roe.models.lightgbm import walk_forward_lightgbm
from pb_roe.portfolio.optimizer import PortfolioConstraints, optimize_portfolio
from pb_roe.portfolio.risk import ledoit_wolf_covariance, trailing_return_matrix


def optimize_from_cli(config_path: str, prediction_file: str | None) -> int:
    config = load_config(config_path)
    providers = config.section("data").get("providers", {})
    if not all(value == "fixture" for value in providers.values()):
        raise FileNotFoundError(
            "The current optimizer CLI needs fixture providers; "
            "real runs require a canonical price input"
        )
    bundle = fixture_bundle()
    panel, features = load_model_panel(config, None)
    if prediction_file:
        predictions = pd.read_parquet(prediction_file)
    else:
        predictions, _ = walk_forward_lightgbm(panel, features, config)
    portfolio_config = config.section("portfolio")
    settings = PortfolioConstraints(
        risk_aversion=float(portfolio_config["risk_aversion"]),
        turnover_penalty=float(portfolio_config["turnover_penalty"]),
        max_weight=float(portfolio_config["max_weight"]),
        max_industry_deviation=float(portfolio_config["max_industry_deviation"]),
        max_turnover=float(portfolio_config["max_turnover"]),
    )
    metadata = panel[["signal_date", "security_id", "industry", "forward_return"]].drop_duplicates()
    predictions = predictions.merge(
        metadata, on=["signal_date", "security_id"], how="left", validate="one_to_one"
    )
    previous_weights: pd.Series | None = None
    holding_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []
    diagnostic_rows: list[dict[str, object]] = []
    for signal_date, snapshot in predictions.groupby("signal_date", sort=True):
        snapshot = snapshot.dropna(subset=["prediction", "industry", "forward_return"])
        securities = snapshot["security_id"].tolist()
        trailing = trailing_return_matrix(
            bundle.prices,
            securities,
            signal_date,
            lookback_days=int(portfolio_config["covariance_lookback_days"]),
        )
        covariance = ledoit_wolf_covariance(
            trailing,
            minimum_observations=int(portfolio_config["minimum_return_observations"]),
        )
        eligible = [security for security in securities if security in covariance.index]
        expected = snapshot.set_index("security_id")["prediction"].reindex(eligible)
        industries = snapshot.set_index("security_id")["industry"].reindex(eligible)
        benchmark = pd.Series(1 / len(eligible), index=eligible)
        result = optimize_portfolio(
            expected,
            covariance,
            industries,
            benchmark_weights=benchmark,
            previous_weights=previous_weights,
            constraints=settings,
        )
        realized = snapshot.set_index("security_id")["forward_return"].reindex(result.weights.index)
        gross_return = float((result.weights * realized).sum())
        cost = result.turnover * float(config.section("costs").get("base_rate", 0.0))
        holding_rows.extend(
            {
                "signal_date": pd.Timestamp(signal_date),
                "security_id": security,
                "target_weight": float(weight),
                "prediction": float(expected.get(security, 0.0)),
                "industry": industries.get(security, "Unknown"),
            }
            for security, weight in result.weights.items()
        )
        return_rows.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "gross_return": gross_return,
                "turnover": result.turnover,
                "transaction_cost": cost,
                "net_return": gross_return - cost,
            }
        )
        diagnostic_rows.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "status": result.status,
                "objective_value": result.objective_value,
                "used_fallback": result.used_fallback,
            }
        )
        previous_weights = result.weights

    output = config.output_dir()
    output.mkdir(parents=True, exist_ok=True)
    holdings = pd.DataFrame(holding_rows)
    portfolio_returns = pd.DataFrame(return_rows)
    diagnostics = pd.DataFrame(diagnostic_rows)
    holdings.to_parquet(output / "optimized_holdings.parquet", index=False)
    portfolio_returns.to_csv(output / "optimized_returns.csv", index=False)
    diagnostics.to_csv(output / "optimization_diagnostics.csv", index=False)
    run_metadata = {
        "run_id": config.run_id,
        "months": len(portfolio_returns),
        "fallback_months": int(diagnostics["used_fallback"].sum()),
        "output": str(output),
    }
    (output / "optimization_run.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(run_metadata, ensure_ascii=False, indent=2))
    return 0

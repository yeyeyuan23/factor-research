"""End-to-end optimized portfolio runner."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pb_roe.config import load_config
from pb_roe.data.providers.fixture import fixture_bundle
from pb_roe.data.store import ParquetStore
from pb_roe.evaluation.performance import performance_metrics
from pb_roe.models.dataset import load_model_panel
from pb_roe.models.lightgbm import walk_forward_lightgbm
from pb_roe.portfolio.optimizer import PortfolioConstraints, optimize_portfolio
from pb_roe.portfolio.risk import ledoit_wolf_covariance, trailing_return_matrix

MONTHS_PER_YEAR = 12


def _annualize_monthly_predictions(predictions: pd.Series) -> pd.Series:
    return predictions * MONTHS_PER_YEAR


def optimize_from_cli(
    config_path: str,
    prediction_file: str | None,
    factor_file: str | None = None,
    input_dir: str | None = None,
) -> int:
    config = load_config(config_path)
    providers = config.section("data").get("providers", {})
    is_fixture = all(value == "fixture" for value in providers.values())
    if not is_fixture and not input_dir:
        raise FileNotFoundError(
            "--input-dir with canonical prices is required for real optimization"
        )
    bundle = fixture_bundle() if is_fixture else ParquetStore(input_dir).read_bundle()
    panel, features = load_model_panel(config, factor_file, input_dir if not factor_file else None)
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
    metadata_columns = [
        column
        for column in ("signal_date", "security_id", "industry", "weight", "forward_return")
        if column in panel
    ]
    metadata = panel[metadata_columns].drop_duplicates()
    predictions = predictions.merge(
        metadata, on=["signal_date", "security_id"], how="left", validate="one_to_one"
    )
    previous_weights: pd.Series | None = None
    cost_rates = [
        float(value)
        for value in config.section("costs").get(
            "sensitivity_rates", [config.section("costs").get("base_rate", 0.0)]
        )
    ]
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
        monthly_expected = snapshot.set_index("security_id")["prediction"].reindex(eligible)
        expected = _annualize_monthly_predictions(monthly_expected)
        industries = snapshot.set_index("security_id")["industry"].reindex(eligible)
        if "weight" in snapshot:
            benchmark = snapshot.set_index("security_id")["weight"].reindex(eligible).fillna(0.0)
            benchmark = benchmark / benchmark.sum()
        else:
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
        benchmark_realized = snapshot.set_index("security_id")["forward_return"].reindex(eligible)
        benchmark_return = float((benchmark * benchmark_realized).sum())
        holding_rows.extend(
            {
                "signal_date": pd.Timestamp(signal_date),
                "security_id": security,
                "target_weight": float(weight),
                "prediction": float(monthly_expected.get(security, 0.0)),
                "industry": industries.get(security, "Unknown"),
            }
            for security, weight in result.weights.items()
        )
        return_rows.append(
            {
                "signal_date": pd.Timestamp(signal_date),
                "gross_return": gross_return,
                "turnover": result.turnover,
                "benchmark_return": benchmark_return,
                "gross_excess_return": gross_return - benchmark_return,
                **{
                    f"net_return_{int(round(rate * 10_000))}bp": (
                        gross_return - result.turnover * rate
                    )
                    for rate in cost_rates
                },
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
    model_tag = (
        Path(prediction_file).stem.replace("_predictions", "") if prediction_file else "lightgbm"
    )
    holdings = pd.DataFrame(holding_rows)
    portfolio_returns = pd.DataFrame(return_rows)
    diagnostics = pd.DataFrame(diagnostic_rows)
    research = config.section("research")
    segments = {
        "all": (pd.Timestamp.min, pd.Timestamp.max),
        "development": (pd.Timestamp("2015-01-01"), pd.Timestamp(research["development_end"])),
        "frozen_oos": (pd.Timestamp(research["oos_start"]), pd.Timestamp(research["end_date"])),
    }
    summary_rows: list[dict[str, object]] = []
    for segment, (start, end) in segments.items():
        selected = portfolio_returns[
            pd.to_datetime(portfolio_returns["signal_date"]).between(start, end)
        ]
        benchmark_metrics = performance_metrics(selected["benchmark_return"])
        for rate in cost_rates:
            bps = int(round(rate * 10_000))
            net_column = f"net_return_{bps}bp"
            metrics = performance_metrics(selected[net_column])
            excess = selected[net_column] - selected["benchmark_return"]
            excess_std = float(excess.std(ddof=1))
            summary_rows.append(
                {
                    "segment": segment,
                    "cost_bps": bps,
                    "months": len(selected),
                    "benchmark_annual_return": benchmark_metrics["annual_return"],
                    "benchmark_sharpe": benchmark_metrics["sharpe"],
                    "benchmark_max_drawdown": benchmark_metrics["max_drawdown"],
                    "net_annual_return": metrics["annual_return"],
                    "net_sharpe": metrics["sharpe"],
                    "net_max_drawdown": metrics["max_drawdown"],
                    "mean_annual_excess_return": float(excess.mean() * MONTHS_PER_YEAR),
                    "excess_information_ratio": (
                        float(excess.mean() / excess_std * MONTHS_PER_YEAR**0.5)
                        if excess_std > 0
                        else float("nan")
                    ),
                    "average_monthly_turnover": float(selected["turnover"].mean()),
                }
            )
    portfolio_summary = pd.DataFrame(summary_rows)
    holdings.to_parquet(output / f"{model_tag}_optimized_holdings.parquet", index=False)
    portfolio_returns.to_csv(output / f"{model_tag}_optimized_returns.csv", index=False)
    diagnostics.to_csv(output / f"{model_tag}_optimization_diagnostics.csv", index=False)
    portfolio_summary.to_csv(output / f"{model_tag}_portfolio_summary.csv", index=False)
    run_metadata = {
        "run_id": config.run_id,
        "model": model_tag,
        "config_fingerprint": config.fingerprint,
        "months": len(portfolio_returns),
        "fallback_months": int(diagnostics["used_fallback"].sum()),
        "prediction_units": "monthly_return_annualized_for_annual_covariance",
        "risk_objective": "benchmark_relative_active_risk",
        "output": str(output),
    }
    (output / f"{model_tag}_optimization_run.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(run_metadata, ensure_ascii=False, indent=2))
    return 0

"""Command line interface for the research pipeline."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence

from pb_roe.config import ConfigError, load_config
from pb_roe.logging import configure_logging

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pb-roe", description="PB-ROE research pipeline")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("config-check", help="Validate a YAML config")
    config_parser.add_argument("--config", required=True)

    data_parser = subparsers.add_parser("data", help="Data pipeline commands")
    data_subparsers = data_parser.add_subparsers(dest="data_command", required=True)
    audit_parser = data_subparsers.add_parser("audit", help="Run data quality gates")
    audit_parser.add_argument("--config", required=True)
    audit_parser.add_argument("--input-dir")

    reproduce_parser = subparsers.add_parser("reproduce", help="Run paper reproduction")
    reproduce_parser.add_argument("--config", required=True)
    reproduce_parser.add_argument("--input-dir")

    evaluate_parser = subparsers.add_parser("evaluate", help="Run modern factor evaluation")
    evaluate_parser.add_argument("--config", required=True)
    evaluate_parser.add_argument("--factor-file")

    train_parser = subparsers.add_parser("train", help="Run a walk-forward prediction model")
    train_parser.add_argument("--config", required=True)
    train_parser.add_argument("--factor-file")
    train_parser.add_argument("--model", choices=("elastic-net", "lightgbm"), required=True)

    optimize_parser = subparsers.add_parser("optimize", help="Build constrained portfolios")
    optimize_parser.add_argument("--config", required=True)
    optimize_parser.add_argument("--prediction-file")

    report_parser = subparsers.add_parser("report", help="Generate an offline research dashboard")
    report_parser.add_argument("--config", required=True)
    report_parser.add_argument("--run-dir")

    return parser


def _config_summary(config_path: str) -> dict[str, str]:
    config = load_config(config_path)
    return {
        "run_id": config.run_id,
        "mode": config.mode,
        "fingerprint": config.fingerprint,
        "source": str(config.source),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        if args.command == "config-check":
            print(json.dumps(_config_summary(args.config), ensure_ascii=False, indent=2))
            return 0

        if args.command == "data" and args.data_command == "audit":
            from pb_roe.data.audit import audit_from_cli

            return audit_from_cli(args.config, args.input_dir)

        if args.command == "reproduce":
            from pb_roe.reproduction.runner import reproduce_from_cli

            return reproduce_from_cli(args.config, args.input_dir)

        if args.command == "evaluate":
            from pb_roe.evaluation.runner import evaluate_from_cli

            return evaluate_from_cli(args.config, args.factor_file)

        if args.command == "train":
            from pb_roe.models.runner import train_from_cli

            return train_from_cli(args.config, args.factor_file, args.model)

        if args.command == "optimize":
            from pb_roe.portfolio.runner import optimize_from_cli

            return optimize_from_cli(args.config, args.prediction_file)

        if args.command == "report":
            from pb_roe.reporting.runner import report_from_cli

            return report_from_cli(args.config, args.run_dir)
    except ConfigError as exc:
        LOGGER.error("%s", exc)
        return 2

    parser.error(f"Unsupported command: {args.command}")
    return 2

#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
CONFIG="configs/smoke.yaml"
OUTPUT_DIR="results/runs/smoke"

rm -rf "$OUTPUT_DIR"

"$PYTHON" -m pb_roe config-check --config "$CONFIG"
"$PYTHON" -m pb_roe data audit --config "$CONFIG"
"$PYTHON" -m pb_roe reproduce --config "$CONFIG"
"$PYTHON" -m pb_roe evaluate --config "$CONFIG"
"$PYTHON" -m pb_roe validate-factors --config "$CONFIG"
"$PYTHON" -m pb_roe train --config "$CONFIG" --model elastic-net
"$PYTHON" -m pb_roe train --config "$CONFIG" --model lightgbm
"$PYTHON" -m pb_roe optimize \
  --config "$CONFIG" \
  --factor-file "$OUTPUT_DIR/model_factor_panel.parquet" \
  --prediction-file "$OUTPUT_DIR/elastic-net_predictions.parquet"
"$PYTHON" -m pb_roe optimize \
  --config "$CONFIG" \
  --factor-file "$OUTPUT_DIR/model_factor_panel.parquet" \
  --prediction-file "$OUTPUT_DIR/lightgbm_predictions.parquet"
"$PYTHON" -m pb_roe report --config "$CONFIG"
"$PYTHON" -m pb_roe final-audit --config "$CONFIG"
"$PYTHON" -m pytest
"$PYTHON" -m ruff check --no-cache src tests

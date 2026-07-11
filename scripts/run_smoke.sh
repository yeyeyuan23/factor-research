#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
CONFIG="configs/smoke.yaml"

"$PYTHON" -m pb_roe config-check --config "$CONFIG"
"$PYTHON" -m pb_roe data audit --config "$CONFIG"
"$PYTHON" -m pb_roe reproduce --config "$CONFIG"
"$PYTHON" -m pb_roe evaluate --config "$CONFIG"
"$PYTHON" -m pb_roe train --config "$CONFIG" --model elastic-net
"$PYTHON" -m pb_roe train --config "$CONFIG" --model lightgbm
"$PYTHON" -m pb_roe optimize --config "$CONFIG"
"$PYTHON" -m pb_roe report --config "$CONFIG"
"$PYTHON" -m pb_roe final-audit --config "$CONFIG"
"$PYTHON" -m pytest
"$PYTHON" -m ruff check --no-cache src tests


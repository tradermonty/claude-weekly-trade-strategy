#!/bin/bash
# Run full robustness analysis for weekly trade strategy backtest.
# Usage: bash scripts/run_backtest_matrix.sh

set -euo pipefail

OUT="results/robustness"
mkdir -p "$OUT"

echo "=== Full Robustness Analysis ==="
echo "Output: $OUT"
echo ""

.venv/bin/python -m trading.backtest \
  --start 2025-11-03 \
  --end 2026-02-14 \
  --full-robustness \
  --output "$OUT"

echo ""
echo "=== Results ==="
echo "Cost matrix:  $OUT/cost_matrix.csv"
echo "Report:       $OUT/backtest_robustness.md"

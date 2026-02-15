"""Tests for cost sensitivity matrix and robustness report (Phase 2 & 4)."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from trading.backtest.metrics import BacktestResult
from trading.backtest.robustness import (
    find_breakeven,
    generate_robustness_report,
    write_cost_matrix_csv,
)


def _make_result(net_return: float, gross_return: float = 0.0, sharpe: float = 1.0,
                 max_dd: float = -2.0, trades: int = 50, turnover: float = 1.0,
                 total_cost: float = 10.0) -> BacktestResult:
    return BacktestResult(
        phase="test",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 1),
        trading_days=40,
        blogs_used=8,
        blogs_skipped=0,
        initial_capital=100_000,
        final_value=100_000 + net_return * 1000,
        total_return_pct=net_return,
        max_drawdown_pct=max_dd,
        sharpe_ratio=sharpe,
        total_trades=trades,
        gross_return_pct=gross_return or net_return,
        total_cost=total_cost,
        turnover=turnover,
    )


class TestCostMatrixCSV:

    def test_csv_format(self, tmp_path):
        results = [
            {"mode": "B-transition", "cost_bps": 0, "result": _make_result(5.0, 5.0)},
            {"mode": "B-transition", "cost_bps": 5, "result": _make_result(4.8, 5.0)},
            {"mode": "A-transition", "cost_bps": 0, "result": _make_result(4.5, 4.5)},
        ]
        csv_path = tmp_path / "matrix.csv"
        write_cost_matrix_csv(results, csv_path)

        with open(csv_path) as f:
            reader = csv.reader(f)
            header = next(reader)

        expected_cols = [
            "mode", "cost_bps", "gross_return", "net_return",
            "max_dd", "sharpe", "trades", "turnover", "total_cost",
        ]
        assert header == expected_cols

    def test_csv_row_count(self, tmp_path):
        results = [
            {"mode": f"mode{i}", "cost_bps": c, "result": _make_result(5.0 - c * 0.1)}
            for i in range(4) for c in [0, 2, 5, 10, 20]
        ]
        csv_path = tmp_path / "matrix.csv"
        write_cost_matrix_csv(results, csv_path)

        with open(csv_path) as f:
            reader = csv.reader(f)
            rows = list(reader)
        # header + 20 data rows
        assert len(rows) == 21

    def test_cost_matrix_result_count(self):
        """4 modes x 5 costs = 20 results."""
        results = [
            {"mode": mode, "cost_bps": c, "result": _make_result(5.0)}
            for mode in ["A-transition", "A-friday", "B-transition", "B-friday"]
            for c in [0, 2, 5, 10, 20]
        ]
        assert len(results) == 20


class TestBreakeven:

    def test_breakeven_between_modes(self):
        """B starts ahead at 0 bps but falls behind A at 10 bps."""
        results = [
            {"mode": "B-transition", "cost_bps": 0, "result": _make_result(5.0)},
            {"mode": "B-transition", "cost_bps": 5, "result": _make_result(4.0)},
            {"mode": "B-transition", "cost_bps": 10, "result": _make_result(3.0)},
            {"mode": "A-transition", "cost_bps": 0, "result": _make_result(4.0)},
            {"mode": "A-transition", "cost_bps": 5, "result": _make_result(3.8)},
            {"mode": "A-transition", "cost_bps": 10, "result": _make_result(3.5)},
        ]
        be = find_breakeven(results)
        assert be["breakeven_bps"] is not None
        # B starts at +5, A at +4. At 5 bps: B=4 vs A=3.8 (B still ahead).
        # At 10 bps: B=3 vs A=3.5 (A ahead). Crossover between 5 and 10.
        assert 5 < be["breakeven_bps"] < 10

    def test_no_crossover(self):
        """B always ahead."""
        results = [
            {"mode": "B-transition", "cost_bps": 0, "result": _make_result(5.0)},
            {"mode": "B-transition", "cost_bps": 20, "result": _make_result(4.0)},
            {"mode": "A-transition", "cost_bps": 0, "result": _make_result(3.0)},
            {"mode": "A-transition", "cost_bps": 20, "result": _make_result(2.5)},
        ]
        be = find_breakeven(results)
        assert be["breakeven_bps"] is None
        assert "still ahead" in be["details"]

    def test_higher_cost_lower_net_return(self):
        """Verify logic: more cost => lower net return for same mode."""
        results = [
            {"mode": "B-transition", "cost_bps": 0, "result": _make_result(5.0)},
            {"mode": "B-transition", "cost_bps": 5, "result": _make_result(4.5)},
            {"mode": "B-transition", "cost_bps": 10, "result": _make_result(4.0)},
        ]
        for i in range(len(results) - 1):
            r1 = results[i]["result"]
            r2 = results[i + 1]["result"]
            assert r1.total_return_pct >= r2.total_return_pct


class TestRobustnessReport:

    def test_report_contains_all_sections(self, tmp_path):
        strategy = {"B-transition": _make_result(5.0, 5.1, sharpe=2.5)}
        benchmarks = {"SPY B&H": _make_result(3.0, 3.0, sharpe=1.5)}
        cost_matrix = [
            {"mode": "B-transition", "cost_bps": bps, "result": _make_result(5.0 - bps * 0.05)}
            for bps in [0, 2, 5, 10, 20]
        ] + [
            {"mode": "A-transition", "cost_bps": bps, "result": _make_result(4.0 - bps * 0.02)}
            for bps in [0, 2, 5, 10, 20]
        ]
        breakeven_info = find_breakeven(cost_matrix)

        report_path = tmp_path / "report.md"
        generate_robustness_report(
            strategy, cost_matrix, benchmarks, breakeven_info, report_path,
        )
        content = report_path.read_text()

        expected_headers = [
            "## 1. Executive Summary",
            "## 2. Strategy Comparison",
            "## 3. Cost Sensitivity",
            "## 4. Benchmark Comparison",
            "## 5. Robustness Assessment",
            "## 6. Recommendation",
            "## 7. Data Limitation",
        ]
        for header in expected_headers:
            assert header in content, f"Missing section: {header}"

    def test_adopt_when_strategy_dominates(self, tmp_path):
        strategy = {"B-transition": _make_result(5.0, 5.1, sharpe=2.5)}
        benchmarks = {"SPY B&H": _make_result(3.0, 3.0, sharpe=1.5)}
        breakeven_info = {"breakeven_bps": None, "details": "B always ahead"}
        cost_matrix = [
            {"mode": "B-transition", "cost_bps": 5, "result": _make_result(4.8, sharpe=2.3)},
        ]

        report_path = tmp_path / "report.md"
        generate_robustness_report(
            strategy, cost_matrix, benchmarks, breakeven_info, report_path,
        )
        content = report_path.read_text()
        assert "ADOPT" in content

    def test_reject_when_spy_dominates(self, tmp_path):
        strategy = {"B-transition": _make_result(2.0, 2.1, sharpe=0.8)}
        benchmarks = {"SPY B&H": _make_result(5.0, 5.0, sharpe=2.0)}
        breakeven_info = {"breakeven_bps": 2, "details": "B falls behind at 2 bps"}
        cost_matrix = [
            {"mode": "B-transition", "cost_bps": 5, "result": _make_result(1.5, sharpe=0.5)},
        ]

        report_path = tmp_path / "report.md"
        generate_robustness_report(
            strategy, cost_matrix, benchmarks, breakeven_info, report_path,
        )
        content = report_path.read_text()
        assert "REJECT" in content

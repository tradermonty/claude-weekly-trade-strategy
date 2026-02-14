"""Tests for BacktestMetrics."""

import math
from datetime import date

import pytest

from trading.backtest.metrics import BacktestMetrics, DailySnapshot


def _snap(d: date, value: float, trades: int = 0, scenario: str = "base") -> DailySnapshot:
    return DailySnapshot(
        date=d,
        total_value=value,
        cash=value * 0.2,
        positions_value=value * 0.8,
        scenario=scenario,
        trades_today=trades,
    )


class TestTotalReturn:
    def test_positive_return(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000),
            _snap(date(2026, 1, 6), 103_000),
        ]
        m = BacktestMetrics(snaps, 100_000)
        assert m.total_return_pct == pytest.approx(3.0)

    def test_negative_return(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000),
            _snap(date(2026, 1, 6), 95_000),
        ]
        m = BacktestMetrics(snaps, 100_000)
        assert m.total_return_pct == pytest.approx(-5.0)

    def test_no_snapshots(self):
        m = BacktestMetrics([], 100_000)
        assert m.total_return_pct == 0.0

    def test_zero_capital(self):
        m = BacktestMetrics([_snap(date(2026, 1, 5), 0)], 0)
        assert m.total_return_pct == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000),
            _snap(date(2026, 1, 6), 101_000),
            _snap(date(2026, 1, 7), 102_000),
        ]
        m = BacktestMetrics(snaps, 100_000)
        assert m.max_drawdown_pct == 0.0

    def test_simple_drawdown(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000),
            _snap(date(2026, 1, 6), 105_000),
            _snap(date(2026, 1, 7), 95_000),  # -9.52% from peak
            _snap(date(2026, 1, 8), 98_000),
        ]
        m = BacktestMetrics(snaps, 100_000)
        expected_dd = ((95_000 - 105_000) / 105_000) * 100
        assert m.max_drawdown_pct == pytest.approx(expected_dd, abs=0.01)

    def test_no_snapshots(self):
        m = BacktestMetrics([], 100_000)
        assert m.max_drawdown_pct == 0.0


class TestSharpeRatio:
    def test_positive_sharpe(self):
        # Steady upward: low vol, positive return
        snaps = [_snap(date(2026, 1, d), 100_000 + d * 100) for d in range(5, 26)]
        m = BacktestMetrics(snaps, 100_000)
        assert m.sharpe_ratio > 0

    def test_zero_with_no_variance(self):
        # All same value: 0 std, 0 sharpe
        snaps = [_snap(date(2026, 1, d), 100_000) for d in range(5, 10)]
        m = BacktestMetrics(snaps, 100_000)
        assert m.sharpe_ratio == 0.0

    def test_single_snapshot(self):
        m = BacktestMetrics([_snap(date(2026, 1, 5), 100_000)], 100_000)
        assert m.sharpe_ratio == 0.0


class TestFinalValue:
    def test_returns_last_snapshot(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000),
            _snap(date(2026, 1, 6), 103_456),
        ]
        m = BacktestMetrics(snaps, 100_000)
        assert m.final_value == 103_456

    def test_no_snapshots(self):
        m = BacktestMetrics([], 100_000)
        assert m.final_value == 100_000


class TestTotalTrades:
    def test_counts_all_trades(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000, trades=3),
            _snap(date(2026, 1, 6), 100_000, trades=2),
            _snap(date(2026, 1, 7), 100_000, trades=0),
        ]
        m = BacktestMetrics(snaps, 100_000)
        assert m.total_trades == 5


class TestWeeklyPerformance:
    def test_basic_weekly(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000, trades=5),
            _snap(date(2026, 1, 6), 100_500),
            _snap(date(2026, 1, 7), 101_000),
            _snap(date(2026, 1, 8), 101_500),
            _snap(date(2026, 1, 9), 102_000),
            _snap(date(2026, 1, 12), 102_000, trades=4),
            _snap(date(2026, 1, 13), 102_500),
        ]
        m = BacktestMetrics(snaps, 100_000)
        transitions = [date(2026, 1, 5), date(2026, 1, 12)]
        weeks = m.weekly_performance(transitions)
        assert len(weeks) == 2
        assert weeks[0].blog_date == "2026-01-05"
        assert weeks[0].return_pct == pytest.approx(2.0, abs=0.1)


class TestBuildResult:
    def test_builds_complete_result(self):
        snaps = [
            _snap(date(2026, 1, 5), 100_000, trades=5),
            _snap(date(2026, 1, 9), 103_000, trades=2),
        ]
        m = BacktestMetrics(snaps, 100_000)
        result = m.build_result(
            phase="A",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 9),
            blogs_used=3,
            blogs_skipped=2,
            skipped_reasons=[("2025-11-03", "empty")],
            transition_days=[date(2026, 1, 5)],
        )
        assert result.phase == "A"
        assert result.total_return_pct == pytest.approx(3.0)
        assert result.total_trades == 7
        assert result.blogs_used == 3

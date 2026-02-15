"""Tests for walk-forward validation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from trading.backtest.metrics import BacktestResult
from trading.backtest.walk_forward import (
    WalkForwardResult,
    WeeklyExcess,
    WindowResult,
    compute_expanding_windows,
    compute_mean_excess,
    compute_rolling_windows,
    compute_win_rate,
    determine_verdict,
    extract_daily_excess,
    information_ratio,
    paired_t_test,
    write_walk_forward_report,
)


def _make_result(**kwargs) -> BacktestResult:
    defaults = dict(
        phase="test",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 1),
        trading_days=40,
        blogs_used=8,
        blogs_skipped=0,
        initial_capital=100_000,
        final_value=105_000,
        total_return_pct=5.0,
        max_drawdown_pct=-2.0,
        sharpe_ratio=2.0,
        total_trades=50,
    )
    defaults.update(kwargs)
    return BacktestResult(**defaults)


def _make_wf_result(**kwargs) -> WalkForwardResult:
    fp = _make_result()
    spy = _make_result(phase="SPY B&H", total_return_pct=3.0)
    defaults = dict(
        full_period=fp,
        full_spy=spy,
        weekly_excess=[],
        win_rate=0.0,
        mean_weekly_excess=0.0,
        rolling_windows=[],
        expanding_windows=[],
        t_statistic=0.0,
        p_value=1.0,
        information_ratio=0.0,
        verdict="NOT_SIGNIFICANT",
        verdict_detail="test",
    )
    defaults.update(kwargs)
    return WalkForwardResult(**defaults)


def _make_daily_data(n_weeks: int = 15):
    """Create mock strat/spy values and transition days for n_weeks.

    Returns (strat_values, spy_values, transition_days).
    """
    base = date(2025, 1, 6)  # Monday
    trans: list[date] = []
    strat: dict[date, float] = {}
    spy: dict[date, float] = {}
    val_s = 100_000.0
    val_spy = 100_000.0

    for w in range(n_weeks):
        td = base + timedelta(weeks=w)
        trans.append(td)
        # 5 trading days per week
        for d in range(5):
            day = td + timedelta(days=d)
            val_s *= 1.001   # +0.1% per day
            val_spy *= 1.0005  # +0.05% per day
            strat[day] = val_s
            spy[day] = val_spy

    return strat, spy, trans


class TestWeeklyExcess:

    def test_win_rate_all_positive(self):
        weekly = [
            WeeklyExcess(date(2025, 1, 6), 2.0, 1.0, 1.0),
            WeeklyExcess(date(2025, 1, 13), 1.5, 0.5, 1.0),
            WeeklyExcess(date(2025, 1, 20), 3.0, 1.0, 2.0),
        ]
        assert compute_win_rate(weekly) == 1.0

    def test_win_rate_mixed(self):
        weekly = [
            WeeklyExcess(date(2025, 1, 6), 2.0, 1.0, 1.0),
            WeeklyExcess(date(2025, 1, 13), 0.5, 1.5, -1.0),
        ]
        assert compute_win_rate(weekly) == 0.5

    def test_mean_excess_calculation(self):
        weekly = [
            WeeklyExcess(date(2025, 1, 6), 2.0, 1.0, 1.0),
            WeeklyExcess(date(2025, 1, 13), 0.5, 1.5, -1.0),
            WeeklyExcess(date(2025, 1, 20), 3.0, 1.0, 2.0),
        ]
        expected = (1.0 + (-1.0) + 2.0) / 3
        assert abs(compute_mean_excess(weekly) - expected) < 1e-10


class TestRollingWindows:

    def test_window_count(self):
        """15 weeks / 6-week window / 2-week step -> 5 windows."""
        strat, spy, trans = _make_daily_data(15)
        end = max(strat.keys())
        windows = compute_rolling_windows(strat, spy, trans, 6, 2, end)
        assert len(windows) == 5

    def test_windows_non_overlapping_dates(self):
        """Each window start < end, and starts advance across windows."""
        strat, spy, trans = _make_daily_data(15)
        end = max(strat.keys())
        windows = compute_rolling_windows(strat, spy, trans, 6, 2, end)
        for w in windows:
            assert w.start_date < w.end_date
        for i in range(1, len(windows)):
            assert windows[i].start_date > windows[i - 1].start_date

    def test_all_windows_have_results(self):
        """Each window should have non-zero strategy and SPY returns."""
        strat, spy, trans = _make_daily_data(15)
        end = max(strat.keys())
        windows = compute_rolling_windows(strat, spy, trans, 6, 2, end)
        for w in windows:
            assert w.strategy_return_pct != 0.0
            assert w.spy_return_pct != 0.0


class TestExpandingWindows:

    def test_expanding_monotonic_weeks(self):
        """Weeks should monotonically increase across expanding windows."""
        strat, spy, trans = _make_daily_data(15)
        end = max(strat.keys())
        windows = compute_expanding_windows(strat, spy, trans, 4, 2, end)
        weeks = [w.weeks for w in windows]
        assert weeks == sorted(weeks)
        assert len(set(weeks)) == len(weeks)  # all unique

    def test_expanding_starts_at_min(self):
        """First expanding window should start at min_weeks (4)."""
        strat, spy, trans = _make_daily_data(15)
        end = max(strat.keys())
        windows = compute_expanding_windows(strat, spy, trans, 4, 2, end)
        assert windows[0].weeks == 4


class TestStatisticalTests:

    def test_zero_excess_returns_zero_t(self):
        """All excess returns zero -> t = 0."""
        returns = [0.0] * 50
        t, p = paired_t_test(returns)
        assert t == 0.0

    def test_large_positive_excess_high_t(self):
        """Clearly positive excess with small variance -> high t-statistic."""
        # mean ~= 0.01, std ~= 0.00141 -> t ~= 70.7
        returns = [0.01 + 0.001 * (i % 5 - 2) for i in range(100)]
        t, p = paired_t_test(returns)
        assert t > 2.0

    def test_p_value_bounds(self):
        """p-value should be between 0 and 1."""
        returns = [0.001 * (i % 3 - 1) for i in range(60)]
        t, p = paired_t_test(returns)
        assert 0 <= p <= 1

    def test_information_ratio_sign(self):
        """Positive daily excess -> positive IR."""
        returns = [0.005 + 0.001 * (i % 3 - 1) for i in range(50)]
        ir = information_ratio(returns)
        assert ir > 0


class TestVerdict:

    def test_significant_verdict(self):
        rolling = [
            WindowResult(
                date(2025, 1, 1), date(2025, 2, 1), 4,
                2.0, 1.0, 1.0, 2.0, -1.0,
            ),
        ]
        verdict, _ = determine_verdict(0.03, 0.65, rolling, 100)
        assert verdict == "SIGNIFICANT"

    def test_inconclusive_verdict(self):
        rolling = [
            WindowResult(
                date(2025, 1, 1), date(2025, 2, 1), 4,
                2.0, 1.0, 1.0, 2.0, -1.0,
            ),
        ]
        verdict, _ = determine_verdict(0.08, 0.50, rolling, 70)
        assert verdict == "INCONCLUSIVE"

    def test_not_significant_verdict(self):
        verdict, _ = determine_verdict(0.15, 0.40, [], 30)
        assert verdict == "NOT_SIGNIFICANT"


class TestReport:

    def test_report_contains_sections(self, tmp_path):
        wf_result = _make_wf_result(
            weekly_excess=[
                WeeklyExcess(date(2025, 1, 6), 2.0, 1.0, 1.0),
            ],
            rolling_windows=[
                WindowResult(
                    date(2025, 1, 6), date(2025, 2, 14), 6,
                    3.0, 2.0, 1.0, 2.0, -1.5,
                ),
            ],
            expanding_windows=[
                WindowResult(
                    date(2025, 1, 6), date(2025, 2, 7), 4,
                    2.0, 1.5, 0.5, 1.8, -1.0,
                ),
            ],
            t_statistic=1.42,
            p_value=0.16,
            information_ratio=0.89,
            verdict="INCONCLUSIVE",
            verdict_detail="test detail",
        )
        report_path = tmp_path / "report.md"
        write_walk_forward_report(wf_result, report_path)
        content = report_path.read_text()

        expected = [
            "## 1. Statistical Significance",
            "## 2. Per-Week Performance",
            "## 3. Rolling Windows",
            "## 4. Expanding Window Stability",
            "## 5. Required Sample Size",
        ]
        for header in expected:
            assert header in content, f"Missing: {header}"

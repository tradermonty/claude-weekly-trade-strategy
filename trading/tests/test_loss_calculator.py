"""Tests for the LossCalculator class."""

from __future__ import annotations

from datetime import date

import pytest

from trading.data.models import Portfolio
from trading.layer1.loss_calculator import LossCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_portfolio(account_value: float = 100000.0) -> Portfolio:
    return Portfolio(account_value=account_value, cash=account_value)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDailyLoss:
    """LossCalculator.daily_loss_pct()"""

    def test_daily_loss_none_without_snapshot(self, tmp_db):
        """Returns None if no daily snapshot exists."""
        calc = LossCalculator(tmp_db)
        result = calc.daily_loss_pct(_make_portfolio(100000))
        assert result is None

    def test_daily_loss_calculation(self, tmp_db):
        """Returns correct % when snapshot exists."""
        today = date.today()
        tmp_db.save_opening_snapshot("daily_open", today, 100000)

        calc = LossCalculator(tmp_db)
        # Current value 98000 => -2%
        result = calc.daily_loss_pct(_make_portfolio(98000))

        assert result is not None
        assert result == pytest.approx(-2.0)


class TestWeeklyLoss:
    """LossCalculator.weekly_loss_pct()"""

    def test_weekly_loss_none_without_snapshot(self, tmp_db):
        """Returns None if no weekly snapshot exists."""
        calc = LossCalculator(tmp_db)
        result = calc.weekly_loss_pct(_make_portfolio(100000))
        assert result is None

    def test_weekly_loss_calculation(self, tmp_db):
        """Returns correct % when snapshot exists."""
        today = date.today()
        # get_week_opening_snapshot() searches Mon-Fri, so save on Monday.
        weekday = today.weekday()
        monday = today if weekday == 0 else date.fromordinal(today.toordinal() - weekday)
        tmp_db.save_opening_snapshot("weekly_open", monday, 100000)

        calc = LossCalculator(tmp_db)
        # Current value 95000 => -5%
        result = calc.weekly_loss_pct(_make_portfolio(95000))

        assert result is not None
        assert result == pytest.approx(-5.0)


class TestDrawdown:
    """LossCalculator.drawdown_pct()"""

    def test_drawdown_from_hwm(self, tmp_db):
        """Returns correct drawdown % from high water mark."""
        tmp_db.update_high_water_mark(110000)

        calc = LossCalculator(tmp_db)
        # Current 100000, HWM 110000 => (100000-110000)/110000*100 = -9.0909...%
        result = calc.drawdown_pct(_make_portfolio(100000))

        expected = (100000 - 110000) / 110000 * 100.0
        assert result == pytest.approx(expected)

    def test_drawdown_zero_hwm(self, tmp_db):
        """Returns 0.0 when HWM is 0 (never set)."""
        calc = LossCalculator(tmp_db)
        result = calc.drawdown_pct(_make_portfolio(100000))
        assert result == 0.0


class TestUpdateHWM:
    """LossCalculator.update_hwm_if_needed()"""

    def test_update_hwm_increases(self, tmp_db):
        """HWM is updated when value > current."""
        tmp_db.update_high_water_mark(100000)

        calc = LossCalculator(tmp_db)
        calc.update_hwm_if_needed(_make_portfolio(110000))

        assert tmp_db.get_high_water_mark() == 110000

    def test_update_hwm_does_not_decrease(self, tmp_db):
        """HWM stays same when value < current."""
        tmp_db.update_high_water_mark(120000)

        calc = LossCalculator(tmp_db)
        calc.update_hwm_if_needed(_make_portfolio(110000))

        assert tmp_db.get_high_water_mark() == 120000


class TestSnapshots:
    """LossCalculator.create_daily_snapshot() / create_weekly_snapshot()"""

    def test_create_daily_snapshot(self, tmp_db):
        """Saves daily snapshot correctly and can be read back."""
        calc = LossCalculator(tmp_db)
        calc.create_daily_snapshot(_make_portfolio(100000))

        snapshot = tmp_db.get_opening_snapshot(date.today())
        assert snapshot is not None
        assert snapshot.snapshot_type == "daily_open"
        assert snapshot.account_value == 100000

    def test_create_weekly_snapshot(self, tmp_db):
        """Saves weekly snapshot correctly and can be read back."""
        calc = LossCalculator(tmp_db)
        calc.create_weekly_snapshot(_make_portfolio(105000))

        # create_weekly_snapshot saves with date.today(). Verify via direct
        # DB query since get_week_opening_snapshot only looks Mon-Fri and
        # the test may run on a weekend.
        today = date.today()
        row = tmp_db.conn.execute(
            "SELECT type, date, account_value FROM snapshots "
            "WHERE type = 'weekly_open' AND date = ?",
            (today.isoformat(),),
        ).fetchone()
        assert row is not None
        assert row["type"] == "weekly_open"
        assert row["account_value"] == 105000

"""Tests for the KillSwitch class."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from trading.config import TradingConfig
from trading.data.models import MarketData, Portfolio, Position
from trading.layer1.kill_switch import KillSwitch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_market_data(vix: float = 18.0) -> MarketData:
    return MarketData(timestamp=datetime.now(timezone.utc), vix=vix)


def _make_portfolio(account_value: float = 100000.0) -> Portfolio:
    return Portfolio(account_value=account_value, cash=account_value)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestKillSwitch:
    """KillSwitch.check() should return None when safe, or a reason string."""

    def test_no_trigger_when_all_normal(self, tmp_db, config):
        """No halt when daily=-1%, weekly=-2%, drawdown=-5%, vix=18."""
        today = date.today()

        # Set up daily snapshot: 1% loss means open was ~101010
        daily_open = 100000 / (1 - 0.01)  # ~101010.10
        tmp_db.save_opening_snapshot("daily_open", today, daily_open)

        # Set up weekly snapshot: 2% loss means weekly open was ~102040
        weekly_open = 100000 / (1 - 0.02)  # ~102040.82
        tmp_db.save_opening_snapshot("weekly_open", today, weekly_open)

        # Set up HWM: 5% drawdown means HWM was ~105263
        hwm = 100000 / (1 - 0.05)  # ~105263.16
        tmp_db.update_high_water_mark(hwm)

        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(100000))

        assert result is None

    def test_daily_loss_trigger(self, tmp_db, config):
        """Halt when daily loss <= -3.0%."""
        today = date.today()
        # Daily open was 100000, current is 96000 => -4%
        tmp_db.save_opening_snapshot("daily_open", today, 100000)
        # Ensure no drawdown trigger (HWM = current or close)
        tmp_db.update_high_water_mark(100000)

        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(96000))

        assert result == "daily_loss_exceeded"

    def test_weekly_loss_trigger(self, tmp_db, config):
        """Halt when weekly loss <= -7.0%."""
        today = date.today()
        # get_week_opening_snapshot() searches Mon-Fri of the current week,
        # so save the snapshot on this week's Monday.
        weekday = today.weekday()
        monday = today if weekday == 0 else date.fromordinal(today.toordinal() - weekday)
        # No daily snapshot so daily check returns None (skips)
        # Weekly open was 100000, current is 92000 => -8%
        tmp_db.save_opening_snapshot("weekly_open", monday, 100000)
        # Ensure no drawdown trigger
        tmp_db.update_high_water_mark(100000)

        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(92000))

        assert result == "weekly_loss_exceeded"

    def test_drawdown_trigger(self, tmp_db, config):
        """Halt when drawdown <= -15.0%."""
        # No daily/weekly snapshots (skips those checks)
        # HWM was 120000, current is 100000 => ~-16.67%
        tmp_db.update_high_water_mark(120000)

        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(100000))

        assert result == "drawdown_exceeded"

    def test_vix_extreme_trigger(self, tmp_db, config):
        """Halt when VIX > 40."""
        # No snapshots, no drawdown (HWM=0 means drawdown=0.0)
        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=45.0), _make_portfolio(100000))

        assert result == "vix_extreme"

    def test_api_failures_halt(self, tmp_db, config):
        """Halt when consecutive_api_failures >= 6."""
        # Set up state so API failures are at threshold
        tmp_db.set_state("consecutive_api_failures", "6")
        # No snapshots, no drawdown
        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(100000))

        assert result == "api_consecutive_failures_halt"

    def test_daily_none_skips(self, tmp_db, config):
        """When no daily snapshot exists, the daily check is skipped."""
        # No daily snapshot saved => daily_loss_pct returns None
        # Ensure no drawdown trigger
        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(100000))

        # Should not halt (daily check skipped, no other triggers)
        assert result is None

    def test_weekly_none_skips(self, tmp_db, config):
        """When no weekly snapshot exists, the weekly check is skipped."""
        today = date.today()
        # Save a daily snapshot that is fine (no loss)
        tmp_db.save_opening_snapshot("daily_open", today, 100000)
        # No weekly snapshot
        # No drawdown trigger

        ks = KillSwitch(config, tmp_db)
        result = ks.check(_make_market_data(vix=18.0), _make_portfolio(100000))

        assert result is None

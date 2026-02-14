"""Tests for the Layer 1 RuleEngine."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from trading.config import TradingConfig
from trading.data.database import Database
from trading.data.models import (
    CheckResult,
    CheckResultType,
    MarketData,
    Portfolio,
    Position,
    StrategySpec,
    ScenarioSpec,
    TradingLevel,
)
from trading.layer1.rule_engine import RuleEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine(config: TradingConfig, db: Database) -> RuleEngine:
    """Create a RuleEngine with external services mocked out."""
    with patch("trading.layer1.rule_engine.AlpacaClient"), \
         patch("trading.layer1.rule_engine.EmailNotifier"):
        engine = RuleEngine(config, db)
    # Replace notifier with a no-op so check() doesn't send emails
    engine._notifier = MagicMock()
    return engine


# ===================================================================
# RuleEngine.check()
# ===================================================================


class TestCheckMethod:
    """Tests for RuleEngine.check() orchestration."""

    def test_no_action_normal_conditions(
        self, config, tmp_db, sample_market_data, sample_strategy_spec
    ):
        """Normal market: no kill switch, no VIX cross, no level hit, no drift.

        Should return NO_ACTION.
        Build a portfolio that exactly matches the strategy target allocation
        (including BIL at 28%) so drift_exceeded returns False.
        """
        engine = _make_engine(config, tmp_db)

        # Portfolio that matches target allocation perfectly
        portfolio = Portfolio(
            account_value=100000,
            cash=0,
            positions={
                "SPY": Position("SPY", 32.2, 22000.0, 20000.0, 683.1),   # 22%
                "QQQ": Position("QQQ", 7.5, 4000.0, 3500.0, 531.2),     #  4%
                "DIA": Position("DIA", 18.1, 8000.0, 7800.0, 441.3),    #  8%
                "XLV": Position("XLV", 80.0, 12000.0, 11500.0, 150.0),  # 12%
                "XLP": Position("XLP", 40.0, 4000.0, 3800.0, 100.0),    #  4%
                "GLD": Position("GLD", 22.0, 12000.0, 10000.0, 545.4),  # 12%
                "XLE": Position("XLE", 100.0, 10000.0, 9500.0, 100.0),  # 10%
                "BIL": Position("BIL", 306.0, 28000.0, 28000.0, 91.5),  # 28%
            },
        )

        # Set up a high-water mark above current value so drawdown is benign
        tmp_db.update_high_water_mark(portfolio.account_value)

        # Save a daily snapshot at today's value so daily loss = 0%
        tmp_db.save_opening_snapshot(
            "daily_open", date.today(), portfolio.account_value
        )

        # Save a previous VIX state that does NOT cross any threshold
        # (same side of all thresholds as current VIX 20.5)
        tmp_db.save_market_state(
            timestamp="2026-02-14T10:00:00", vix=20.5,
        )

        # Patch check_stop_order_fills to return None (no fills)
        engine.check_stop_order_fills = MagicMock(return_value=None)

        result = engine.check(
            sample_market_data, portfolio, sample_strategy_spec,
        )

        assert result.type == CheckResultType.NO_ACTION

    def test_halt_on_kill_switch(
        self, config, tmp_db, sample_market_data, sample_portfolio, sample_strategy_spec
    ):
        """If daily loss exceeds limit, check() should return HALT.

        Set up snapshot at 110000 and portfolio at 100000 => -9.1% daily loss,
        exceeding the -3% kill-switch limit.
        """
        engine = _make_engine(config, tmp_db)

        # Snapshot at a higher value => large daily loss
        tmp_db.save_opening_snapshot("daily_open", date.today(), 110000.0)
        # HWM high enough so drawdown doesn't trigger first
        tmp_db.update_high_water_mark(110000.0)

        # Patch stop fills check
        engine.check_stop_order_fills = MagicMock(return_value=None)

        result = engine.check(
            sample_market_data, sample_portfolio, sample_strategy_spec,
        )

        assert result.type == CheckResultType.HALT
        assert "daily_loss" in result.reason


# ===================================================================
# RuleEngine.vix_crossed_threshold()
# ===================================================================


class TestVixCrossedThreshold:
    """Tests for VIX threshold crossing detection."""

    def test_vix_crossed_up_20(self, config, tmp_db, sample_market_data):
        """VIX goes from 19 to 21 -- crosses the 20 (caution) threshold upward."""
        engine = _make_engine(config, tmp_db)

        # Save previous VIX = 19
        tmp_db.save_market_state(timestamp="2026-02-14T10:00:00", vix=19.0)

        # Current VIX = 21
        sample_market_data.vix = 21.0

        assert engine.vix_crossed_threshold(sample_market_data) is True

    def test_vix_crossed_down_17(self, config, tmp_db, sample_market_data):
        """VIX goes from 18 to 16 -- crosses the 17 (risk_on) threshold downward."""
        engine = _make_engine(config, tmp_db)

        tmp_db.save_market_state(timestamp="2026-02-14T10:00:00", vix=18.0)
        sample_market_data.vix = 16.0

        assert engine.vix_crossed_threshold(sample_market_data) is True

    def test_vix_no_cross(self, config, tmp_db, sample_market_data):
        """VIX stays at 19 (was 19 last time) -- no threshold crossed."""
        engine = _make_engine(config, tmp_db)

        tmp_db.save_market_state(timestamp="2026-02-14T10:00:00", vix=19.0)
        sample_market_data.vix = 19.0

        assert engine.vix_crossed_threshold(sample_market_data) is False

    def test_vix_none_returns_false(self, config, tmp_db, sample_market_data):
        """If VIX is None in market data, should return False immediately."""
        engine = _make_engine(config, tmp_db)

        sample_market_data.vix = None

        assert engine.vix_crossed_threshold(sample_market_data) is False


# ===================================================================
# RuleEngine.index_hit_level()
# ===================================================================


class TestIndexHitLevel:
    """Tests for index buy/sell/stop level detection."""

    def test_index_hit_buy_level(
        self, config, tmp_db, sample_market_data, sample_strategy_spec
    ):
        """sp500=6400 is below buy_level=6500 => True."""
        engine = _make_engine(config, tmp_db)
        sample_market_data.sp500 = 6400.0

        assert engine.index_hit_level(sample_market_data, sample_strategy_spec) is True

    def test_index_hit_sell_level(
        self, config, tmp_db, sample_market_data, sample_strategy_spec
    ):
        """sp500=7200 is above sell_level=7100 => True."""
        engine = _make_engine(config, tmp_db)
        sample_market_data.sp500 = 7200.0

        assert engine.index_hit_level(sample_market_data, sample_strategy_spec) is True

    def test_index_hit_stop_level(
        self, config, tmp_db, sample_market_data, sample_strategy_spec
    ):
        """sp500=6200 is below stop_loss=6300 => True."""
        engine = _make_engine(config, tmp_db)
        sample_market_data.sp500 = 6200.0

        assert engine.index_hit_level(sample_market_data, sample_strategy_spec) is True

    def test_index_no_level_hit(
        self, config, tmp_db, sample_market_data, sample_strategy_spec
    ):
        """sp500=6800 is between buy (6500) and sell (7100) levels => False."""
        engine = _make_engine(config, tmp_db)
        sample_market_data.sp500 = 6800.0
        # Also set nasdaq between its levels (buy=20000, sell=23000)
        sample_market_data.nasdaq = 21700.0

        assert engine.index_hit_level(sample_market_data, sample_strategy_spec) is False


# ===================================================================
# RuleEngine.drift_exceeded()
# ===================================================================


class TestDriftExceeded:
    """Tests for portfolio allocation drift detection."""

    def test_drift_exceeded(self, config, tmp_db, sample_strategy_spec):
        """Position drifts >3% from target allocation => True.

        Target SPY=22%, but actual SPY market_value = 30000 / 100000 = 30%.
        Drift = |30 - 22| = 8% > 3% threshold.
        """
        engine = _make_engine(config, tmp_db)

        portfolio = Portfolio(
            account_value=100000,
            cash=20000,
            positions={
                "SPY": Position(
                    symbol="SPY",
                    shares=44.0,
                    market_value=30000.0,  # 30% of 100K
                    cost_basis=28000,
                    current_price=683.1,
                ),
                "QQQ": Position(
                    symbol="QQQ",
                    shares=7.5,
                    market_value=4000.0,  # 4%
                    cost_basis=3500,
                    current_price=531.2,
                ),
                "DIA": Position(
                    symbol="DIA",
                    shares=18.1,
                    market_value=8000.0,  # 8%
                    cost_basis=7800,
                    current_price=441.3,
                ),
                "XLV": Position(
                    symbol="XLV",
                    shares=80.0,
                    market_value=12000.0,  # 12%
                    cost_basis=11500,
                    current_price=150.0,
                ),
                "XLP": Position(
                    symbol="XLP",
                    shares=40.0,
                    market_value=4000.0,  # 4%
                    cost_basis=3800,
                    current_price=100.0,
                ),
                "GLD": Position(
                    symbol="GLD",
                    shares=22.0,
                    market_value=12000.0,  # 12%
                    cost_basis=10000,
                    current_price=545.4,
                ),
                "XLE": Position(
                    symbol="XLE",
                    shares=100.0,
                    market_value=10000.0,  # 10%
                    cost_basis=9500,
                    current_price=100.0,
                ),
            },
        )

        assert engine.drift_exceeded(portfolio, sample_strategy_spec) is True

    def test_drift_within_threshold(self, config, tmp_db, sample_strategy_spec):
        """All positions within 3% of target => False.

        Build a portfolio that matches the target allocation exactly,
        including BIL at 28%.
        """
        engine = _make_engine(config, tmp_db)

        portfolio = Portfolio(
            account_value=100000,
            cash=0,
            positions={
                "SPY": Position("SPY", 32.2, 22000.0, 20000.0, 683.1),   # 22%
                "QQQ": Position("QQQ", 7.5, 4000.0, 3500.0, 531.2),     #  4%
                "DIA": Position("DIA", 18.1, 8000.0, 7800.0, 441.3),    #  8%
                "XLV": Position("XLV", 80.0, 12000.0, 11500.0, 150.0),  # 12%
                "XLP": Position("XLP", 40.0, 4000.0, 3800.0, 100.0),    #  4%
                "GLD": Position("GLD", 22.0, 12000.0, 10000.0, 545.4),  # 12%
                "XLE": Position("XLE", 100.0, 10000.0, 9500.0, 100.0),  # 10%
                "BIL": Position("BIL", 306.0, 28000.0, 28000.0, 91.5),  # 28%
            },
        )

        assert engine.drift_exceeded(portfolio, sample_strategy_spec) is False


# ===================================================================
# RuleEngine.api_failure_alert_needed()
# ===================================================================


class TestApiFailureAlert:
    """Tests for API failure alert threshold."""

    def test_api_failure_alert_at_3(self, config, tmp_db):
        """consecutive_api_failures=3 => True (>= warn threshold of 3)."""
        engine = _make_engine(config, tmp_db)
        tmp_db.set_state("consecutive_api_failures", "3")

        assert engine.api_failure_alert_needed() is True

    def test_api_failure_no_alert_at_2(self, config, tmp_db):
        """consecutive_api_failures=2 => False (below warn threshold of 3)."""
        engine = _make_engine(config, tmp_db)
        tmp_db.set_state("consecutive_api_failures", "2")

        assert engine.api_failure_alert_needed() is False

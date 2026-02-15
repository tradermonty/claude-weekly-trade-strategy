"""Tests for the Layer 3 OrderValidator."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from trading.config import TradingConfig
from trading.data.database import Database
from trading.data.models import (
    Portfolio,
    Position,
    StrategyIntent,
    StrategySpec,
    ScenarioSpec,
    TradingLevel,
    ValidationResult,
    ValidationResultType,
)
from trading.layer3.order_validator import OrderValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_intent(**overrides) -> StrategyIntent:
    """Return a valid StrategyIntent for the base scenario.

    Keyword arguments override individual fields.
    """
    defaults = dict(
        run_id="test123",
        scenario="base",
        rationale="test",
        target_allocation={
            "SPY": 22.0,
            "QQQ": 4.0,
            "DIA": 8.0,
            "XLV": 12.0,
            "XLP": 4.0,
            "GLD": 12.0,
            "XLE": 10.0,
            "BIL": 28.0,
        },
        priority_actions=[],
        confidence="high",
        blog_reference="2026-02-16",
    )
    defaults.update(overrides)
    return StrategyIntent(**defaults)


# ===================================================================
# OrderValidator.validate()
# ===================================================================


class TestValidate:
    """Tests for the full validation pipeline."""

    def test_valid_intent_approved(self, config, tmp_db, sample_strategy_spec):
        """A well-formed intent matching the base scenario should be APPROVED.

        Build a portfolio that already holds positions close to the target
        allocation (including BIL) so no single-order exceeds max_single_order_pct.
        """
        validator = OrderValidator(config, tmp_db)
        intent = _base_intent()

        # Portfolio with positions matching the target allocation
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

        result = validator.validate(intent, sample_strategy_spec, portfolio)

        assert result.is_approved is True
        assert result.errors == []

    def test_unknown_symbol_rejected(
        self, config, tmp_db, sample_portfolio, sample_strategy_spec
    ):
        """An intent containing 'TSLA' (not in ALLOWED_SYMBOLS) is rejected."""
        validator = OrderValidator(config, tmp_db)
        allocation = {
            "SPY": 20.0,
            "QQQ": 4.0,
            "DIA": 8.0,
            "XLV": 12.0,
            "XLP": 4.0,
            "GLD": 12.0,
            "XLE": 10.0,
            "BIL": 26.0,
            "TSLA": 4.0,  # Not allowed
        }
        intent = _base_intent(target_allocation=allocation)

        result = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert result.is_approved is False
        assert any("TSLA" in e for e in result.errors)

    def test_unknown_scenario_rejected(
        self, config, tmp_db, sample_portfolio, sample_strategy_spec
    ):
        """An intent with scenario='moon' (not in strategy_spec) is rejected."""
        validator = OrderValidator(config, tmp_db)
        intent = _base_intent(scenario="moon")

        result = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert result.is_approved is False
        assert any("moon" in e for e in result.errors)

    def test_deviation_exceeded_rejected(
        self, config, tmp_db, sample_portfolio, sample_strategy_spec
    ):
        """SPY=30% vs scenario base SPY=22% => 8% deviation > max_deviation_pct (3%).

        Should be rejected.
        """
        validator = OrderValidator(config, tmp_db)
        allocation = {
            "SPY": 30.0,  # scenario base expects 22.0 => deviation 8%
            "QQQ": 4.0,
            "DIA": 8.0,
            "XLV": 12.0,
            "XLP": 4.0,
            "GLD": 12.0,
            "XLE": 10.0,
            "BIL": 20.0,  # adjusted so total = 100%
        }
        intent = _base_intent(target_allocation=allocation)

        result = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert result.is_approved is False
        assert any("SPY" in e and "deviat" in e.lower() for e in result.errors)

    def test_daily_order_limit(
        self, config, tmp_db, sample_strategy_spec
    ):
        """If 10 trades have already been recorded today, validation should reject.

        max_daily_orders in TradingConfig defaults to 10.
        Uses a portfolio whose positions match the target allocation to isolate
        the daily-order-limit check from single-order-size check.
        """
        validator = OrderValidator(config, tmp_db)

        # Insert 10 trade records for today
        for i in range(10):
            tmp_db.save_trade(
                client_order_id=f"order_{i}",
                symbol="SPY",
                side="buy",
                quantity=1.0,
                status="filled",
                filled_price=683.0,
            )

        # Portfolio with ALL positions (including BIL) matching the base allocation
        # so the single-order-size check does not fire.
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

        intent = _base_intent()
        result = validator.validate(intent, sample_strategy_spec, portfolio)

        assert result.is_approved is False
        assert any("order limit" in e.lower() or "daily" in e.lower() for e in result.errors)

    def test_total_allocation_not_100(
        self, config, tmp_db, sample_portfolio, sample_strategy_spec
    ):
        """Allocation summing to 90% (not ~100%) should be rejected."""
        validator = OrderValidator(config, tmp_db)
        allocation = {
            "SPY": 22.0,
            "QQQ": 4.0,
            "DIA": 8.0,
            "XLV": 12.0,
            "XLP": 4.0,
            "GLD": 12.0,
            "XLE": 10.0,
            "BIL": 18.0,  # total = 90%
        }
        intent = _base_intent(target_allocation=allocation)

        result = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert result.is_approved is False
        assert any("100%" in e or "allocation" in e.lower() for e in result.errors)

    def test_pre_event_freeze_blocks_change(
        self, config, tmp_db, sample_portfolio, sample_strategy_spec
    ):
        """During a pre-event freeze day, changing scenario should be rejected.

        Set current_scenario to 'base', intent has 'bear' scenario,
        and today is a pre-event date.
        """
        validator = OrderValidator(config, tmp_db)

        # Set the current scenario state to "base"
        tmp_db.set_state("current_scenario", "base")

        # Build an intent targeting the "bear" scenario (different from current)
        bear_allocation = sample_strategy_spec.scenarios["bear"].allocation.copy()
        intent = _base_intent(
            scenario="bear",
            target_allocation=bear_allocation,
        )

        # Patch date.today() so that is_pre_event_freeze returns True.
        # We set pre_event_dates to today's ISO string.
        today_iso = date.today().isoformat()
        sample_strategy_spec.pre_event_dates = [today_iso]

        result = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert result.is_approved is False
        assert any("freeze" in e.lower() or "pre-event" in e.lower() for e in result.errors)


# ===================================================================
# OrderValidator.is_pre_event_freeze()
# ===================================================================


class TestIsPreEventFreeze:
    """Tests for the pre-event freeze date check."""

    def test_today_is_freeze_date(self, config, tmp_db, sample_strategy_spec):
        """If today's ISO date is in pre_event_dates, return True."""
        validator = OrderValidator(config, tmp_db)
        today_iso = date.today().isoformat()
        sample_strategy_spec.pre_event_dates = [today_iso]

        assert validator.is_pre_event_freeze(sample_strategy_spec) is True

    def test_today_is_not_freeze_date(self, config, tmp_db, sample_strategy_spec):
        """If today's ISO date is NOT in pre_event_dates, return False."""
        validator = OrderValidator(config, tmp_db)
        sample_strategy_spec.pre_event_dates = ["2099-12-31"]

        assert validator.is_pre_event_freeze(sample_strategy_spec) is False

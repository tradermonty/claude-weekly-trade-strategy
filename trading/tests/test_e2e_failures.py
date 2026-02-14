"""End-to-end failure scenario tests for the trading system.

Tests various failure modes, edge cases, and safety mechanisms across
multiple layers (L1 kill switch, L3 validation/generation/execution)
to ensure the system degrades gracefully and never loses money due to bugs.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from trading.config import TradingConfig
from trading.data.database import Database
from trading.data.models import (
    MarketData,
    Portfolio,
    Position,
    StrategySpec,
    ScenarioSpec,
    TradingLevel,
    StrategyIntent,
    CheckResult,
    CheckResultType,
    ValidationResult,
    ValidationResultType,
    Order,
)
from trading.layer1.rule_engine import RuleEngine
from trading.layer1.kill_switch import KillSwitch
from trading.layer1.loss_calculator import LossCalculator
from trading.layer3.order_validator import OrderValidator
from trading.layer3.order_generator import OrderGenerator
from trading.layer3.order_executor import OrderExecutor
from trading.services.email_notifier import EmailNotifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_market_data(vix: float = 20.5) -> MarketData:
    return MarketData(
        timestamp=datetime.now(timezone.utc),
        vix=vix,
        us10y=4.36,
        sp500=6828.0,
        nasdaq=21700.0,
        dow=44500.0,
        gold=5046.0,
        oil=62.8,
        copper=5.8,
        etf_prices={
            "SPY": 683.1,
            "QQQ": 531.2,
            "DIA": 441.3,
        },
    )


def _make_portfolio(account_value: float = 100000.0, cash: float = 28000.0) -> Portfolio:
    return Portfolio(account_value=account_value, cash=cash)


def _make_intent(
    scenario: str = "base",
    target_allocation: dict[str, float] | None = None,
    run_id: str = "run_001",
) -> StrategyIntent:
    if target_allocation is None:
        target_allocation = {
            "SPY": 22.0,
            "QQQ": 4.0,
            "DIA": 8.0,
            "XLV": 12.0,
            "XLP": 4.0,
            "GLD": 12.0,
            "XLE": 10.0,
            "BIL": 28.0,
        }
    return StrategyIntent(
        run_id=run_id,
        scenario=scenario,
        rationale="Test rationale",
        target_allocation=target_allocation,
        priority_actions=[],
        confidence="medium",
        blog_reference="2026-02-16",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDuplicateOrderPrevention:
    """Verify idempotent order generation via deterministic client_order_ids."""

    def test_duplicate_order_prevention(self, config, sample_portfolio, sample_strategy_spec):
        """Generating orders from the same StrategyIntent twice produces
        identical client_order_ids, preventing duplicate submissions."""
        intent = _make_intent(run_id="dedup_test_001")
        prices = {
            "SPY": 683.1, "QQQ": 531.2, "DIA": 441.3,
            "XLV": 150.0, "XLP": 100.0, "GLD": 545.4,
            "XLE": 100.0, "BIL": 91.5,
        }

        generator = OrderGenerator(config)
        orders_first = generator.generate(intent, sample_portfolio, prices)
        orders_second = generator.generate(intent, sample_portfolio, prices)

        # Both runs must produce the same number of orders
        assert len(orders_first) == len(orders_second)
        assert len(orders_first) > 0, "Expected at least one order to be generated"

        ids_first = [o.client_order_id for o in orders_first]
        ids_second = [o.client_order_id for o in orders_second]

        assert ids_first == ids_second, (
            f"Client order IDs differ between runs: {ids_first} vs {ids_second}"
        )


class TestKillSwitchOverridesClaude:
    """When kill switch triggers, the full pipeline returns HALT regardless
    of what Claude's Layer 2 would suggest."""

    @patch("trading.layer1.rule_engine.AlpacaClient")
    def test_kill_switch_overrides_claude(self, mock_alpaca_cls, tmp_db, config, sample_strategy_spec):
        """A daily loss of -4% (exceeding -3% limit) causes HALT from
        the RuleEngine.check() call, before any Claude analysis runs."""
        today = date.today()

        # Daily open was 100000; current is 96000 => -4% loss
        tmp_db.save_opening_snapshot("daily_open", today, 100000)
        # Prevent drawdown trigger by setting HWM close to current
        tmp_db.update_high_water_mark(100000)

        portfolio = _make_portfolio(account_value=96000.0, cash=10000.0)
        market_data = _make_market_data(vix=20.5)

        engine = RuleEngine(config, tmp_db)
        result = engine.check(market_data, portfolio, sample_strategy_spec)

        assert result.type == CheckResultType.HALT
        assert "daily_loss" in result.reason


class TestApiEscalation3Then6:
    """Test the API failure escalation ladder: 3 consecutive -> ALERT, 6 -> HALT."""

    @patch("trading.layer1.rule_engine.AlpacaClient")
    def test_3_failures_triggers_alert(self, mock_alpaca_cls, tmp_db, config):
        """3 consecutive API failures cause api_failure_alert_needed() to
        return True, producing a TRIGGER_FIRED result."""
        tmp_db.set_state("consecutive_api_failures", "3")

        engine = RuleEngine(config, tmp_db)
        assert engine.api_failure_alert_needed() is True

    def test_6_failures_triggers_halt(self, tmp_db, config):
        """6 consecutive API failures cause the KillSwitch to return a HALT
        reason string (api_consecutive_failures_halt)."""
        tmp_db.set_state("consecutive_api_failures", "6")

        ks = KillSwitch(config, tmp_db)
        market_data = _make_market_data(vix=18.0)
        portfolio = _make_portfolio(100000.0)

        result = ks.check(market_data, portfolio)
        assert result == "api_consecutive_failures_halt"

    @patch("trading.layer1.rule_engine.AlpacaClient")
    def test_reset_to_0_clears_alert(self, mock_alpaca_cls, tmp_db, config):
        """Resetting consecutive_api_failures to 0 clears the alert condition."""
        tmp_db.set_state("consecutive_api_failures", "3")
        engine = RuleEngine(config, tmp_db)
        assert engine.api_failure_alert_needed() is True

        # Reset
        tmp_db.set_state("consecutive_api_failures", "0")
        assert engine.api_failure_alert_needed() is False


class TestStaleBlogHandling:
    """When the blog is very old (>7 days), the system should still function
    and the strategy_spec should carry the original blog_date."""

    def test_stale_blog_date_preserved(self, sample_strategy_spec):
        """A strategy spec parsed from an old blog preserves its date, so
        downstream components know the strategy is stale."""
        # Simulate a blog from 2 weeks ago
        old_spec = StrategySpec(
            blog_date="2026-01-30",
            current_allocation=sample_strategy_spec.current_allocation,
            scenarios=sample_strategy_spec.scenarios,
            trading_levels=sample_strategy_spec.trading_levels,
            stop_losses=sample_strategy_spec.stop_losses,
            vix_triggers=sample_strategy_spec.vix_triggers,
            yield_triggers=sample_strategy_spec.yield_triggers,
            breadth_200ma=sample_strategy_spec.breadth_200ma,
            uptrend_ratio=sample_strategy_spec.uptrend_ratio,
            bubble_score=sample_strategy_spec.bubble_score,
        )

        assert old_spec.blog_date == "2026-01-30"
        # System can still extract scenario allocations from a stale spec
        alloc = old_spec.get_scenario_allocation("base")
        assert len(alloc) > 0

    def test_stale_blog_filename_extraction(self, tmp_path):
        """The strategy parser correctly extracts the date from old blog filenames."""
        from trading.layer2.tools.strategy_parser import _extract_date_from_filename

        assert _extract_date_from_filename("2026-01-15-weekly-strategy.md") == "2026-01-15"
        assert _extract_date_from_filename("2025-06-01-weekly-strategy.md") == "2025-06-01"


class TestHolidayDetection:
    """Verify USMarketCalendar correctly identifies US market holidays for 2026."""

    def test_mlk_day_2026(self):
        """MLK Day 2026 is January 19 (3rd Monday of January)."""
        from trading.core.holidays import USMarketCalendar

        cal = USMarketCalendar()
        # January 2026: 3rd Monday = Jan 19
        assert cal.is_market_holiday(date(2026, 1, 19)) is True
        # Jan 20 is a regular Tuesday, not a holiday
        assert cal.is_market_holiday(date(2026, 1, 20)) is False

    def test_presidents_day_2026(self):
        """Presidents' Day 2026 is February 16 (3rd Monday of February)."""
        from trading.core.holidays import USMarketCalendar

        cal = USMarketCalendar()
        # February 2026: 3rd Monday = Feb 16
        assert cal.is_market_holiday(date(2026, 2, 16)) is True
        assert cal.is_market_holiday(date(2026, 2, 17)) is False

    def test_memorial_day_2026(self):
        """Memorial Day 2026 is May 25 (last Monday of May)."""
        from trading.core.holidays import USMarketCalendar

        cal = USMarketCalendar()
        assert cal.is_market_holiday(date(2026, 5, 25)) is True
        assert cal.is_market_holiday(date(2026, 5, 18)) is False

    def test_thanksgiving_2026(self):
        """Thanksgiving 2026 is November 26 (4th Thursday of November)."""
        from trading.core.holidays import USMarketCalendar

        cal = USMarketCalendar()
        assert cal.is_market_holiday(date(2026, 11, 26)) is True
        assert cal.is_market_holiday(date(2026, 11, 27)) is False  # Black Friday is early close, not holiday

    def test_regular_weekday_not_holiday(self):
        """A regular weekday in March is not a holiday."""
        from trading.core.holidays import USMarketCalendar

        cal = USMarketCalendar()
        assert cal.is_market_holiday(date(2026, 3, 10)) is False

    def test_weekend_not_classified_as_holiday(self):
        """Weekends are not market holidays (they are just non-trading days)."""
        from trading.core.holidays import USMarketCalendar

        cal = USMarketCalendar()
        # Saturday Jan 17, 2026 - not a holiday per the calendar (even though market is closed)
        assert cal.is_market_holiday(date(2026, 1, 17)) is False


class TestEmailSendFailureDoesNotBlock:
    """When SMTP fails, EmailNotifier should still log to file and not raise."""

    def test_alert_does_not_raise_on_smtp_failure(self, config):
        """EmailNotifier.alert() logs to file and does not raise even when
        SMTP is not configured (no sender/password)."""
        notifier = EmailNotifier(config)

        # This should NOT raise — SMTP will fail because no real server is configured
        notifier.alert("Test alert message")
        notifier.critical("Test critical message")

    def test_log_file_created_after_notification(self, config):
        """After sending a notification, a log file should be created in log_dir."""
        notifier = EmailNotifier(config)
        notifier.alert("Test alert for log check")

        today_str = datetime.now().strftime("%Y-%m-%d")
        log_path = config.log_dir / f"notifications_{today_str}.log"
        assert log_path.exists(), f"Expected log file at {log_path}"

        content = log_path.read_text()
        assert "Test alert for log check" in content

    def test_critical_also_logged(self, config):
        """CRITICAL-level notifications are also written to the log file."""
        notifier = EmailNotifier(config)
        notifier.critical("Critical failure test")

        today_str = datetime.now().strftime("%Y-%m-%d")
        log_path = config.log_dir / f"notifications_{today_str}.log"
        content = log_path.read_text()
        assert "CRITICAL" in content
        assert "Critical failure test" in content


class TestValidatorRejectsThenNoOrders:
    """When OrderValidator rejects an intent, no orders should be generated."""

    def test_unknown_symbol_rejected(self, tmp_db, config, sample_portfolio, sample_strategy_spec):
        """An intent containing 'TSLA' (not in ALLOWED_SYMBOLS) is rejected."""
        intent = _make_intent(
            scenario="base",
            target_allocation={
                "SPY": 22.0,
                "QQQ": 4.0,
                "DIA": 8.0,
                "XLV": 12.0,
                "XLP": 4.0,
                "GLD": 12.0,
                "TSLA": 10.0,  # Not in ALLOWED_SYMBOLS
                "BIL": 28.0,
            },
        )

        validator = OrderValidator(config, tmp_db)
        result = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert result.type == ValidationResultType.REJECTED
        assert any("TSLA" in err for err in result.errors)

    def test_rejected_intent_should_not_generate_orders(
        self, tmp_db, config, sample_portfolio, sample_strategy_spec
    ):
        """Demonstrate the intended flow: validate first, only generate if approved."""
        intent = _make_intent(
            scenario="base",
            target_allocation={
                "SPY": 22.0,
                "QQQ": 4.0,
                "DIA": 8.0,
                "XLV": 12.0,
                "XLP": 4.0,
                "GLD": 12.0,
                "TSLA": 10.0,
                "BIL": 28.0,
            },
        )

        validator = OrderValidator(config, tmp_db)
        validation = validator.validate(intent, sample_strategy_spec, sample_portfolio)

        assert not validation.is_approved

        # The correct pipeline flow: only generate orders if validation passes
        orders = []
        if validation.is_approved:
            generator = OrderGenerator(config)
            prices = {"SPY": 683.1, "QQQ": 531.2, "DIA": 441.3}
            orders = generator.generate(intent, sample_portfolio, prices)

        assert len(orders) == 0, "No orders should be generated for a rejected intent"


class TestPreEventFreezeBlocksScenarioChange:
    """During pre-event freeze, scenario changes are blocked."""

    def test_scenario_change_rejected_during_freeze(self, tmp_db, config, sample_portfolio):
        """When today is a pre-event date and current scenario is 'base',
        attempting to change to 'bear' is rejected."""
        # Set current scenario in DB state
        tmp_db.set_state("current_scenario", "base")

        # Create a strategy spec where today is a pre-event date
        today_str = date.today().isoformat()  # e.g. "2026-02-14"
        strategy_spec = StrategySpec(
            blog_date="2026-02-12",
            current_allocation={
                "SPY": 22.0, "QQQ": 4.0, "DIA": 8.0,
                "XLV": 12.0, "XLP": 4.0, "GLD": 12.0,
                "XLE": 10.0, "BIL": 28.0,
            },
            scenarios={
                "base": ScenarioSpec(
                    name="base", probability=45, triggers=[],
                    allocation={
                        "SPY": 22.0, "QQQ": 4.0, "DIA": 8.0,
                        "XLV": 12.0, "XLP": 4.0, "GLD": 12.0,
                        "XLE": 10.0, "BIL": 28.0,
                    },
                ),
                "bear": ScenarioSpec(
                    name="bear", probability=30, triggers=["VIX > 23"],
                    allocation={
                        "SPY": 15.0, "QQQ": 2.0, "DIA": 5.0,
                        "XLV": 15.0, "XLP": 8.0, "GLD": 15.0,
                        "XLE": 5.0, "BIL": 35.0,
                    },
                ),
            },
            trading_levels={},
            stop_losses={},
            vix_triggers={},
            yield_triggers={},
            pre_event_dates=[today_str],  # Today is a pre-event freeze date
        )

        intent = _make_intent(
            scenario="bear",
            target_allocation={
                "SPY": 15.0, "QQQ": 2.0, "DIA": 5.0,
                "XLV": 15.0, "XLP": 8.0, "GLD": 15.0,
                "XLE": 5.0, "BIL": 35.0,
            },
        )

        validator = OrderValidator(config, tmp_db)
        result = validator.validate(intent, strategy_spec, sample_portfolio)

        assert result.type == ValidationResultType.REJECTED
        assert any("freeze" in err.lower() or "Pre-event" in err for err in result.errors)

    def test_same_scenario_allowed_during_freeze(self, tmp_db, config, sample_portfolio):
        """Keeping the same scenario during a freeze is allowed (no scenario change)."""
        tmp_db.set_state("current_scenario", "base")

        today_str = date.today().isoformat()
        strategy_spec = StrategySpec(
            blog_date="2026-02-12",
            current_allocation={
                "SPY": 22.0, "QQQ": 4.0, "DIA": 8.0,
                "XLV": 12.0, "XLP": 4.0, "GLD": 12.0,
                "XLE": 10.0, "BIL": 28.0,
            },
            scenarios={
                "base": ScenarioSpec(
                    name="base", probability=45, triggers=[],
                    allocation={
                        "SPY": 22.0, "QQQ": 4.0, "DIA": 8.0,
                        "XLV": 12.0, "XLP": 4.0, "GLD": 12.0,
                        "XLE": 10.0, "BIL": 28.0,
                    },
                ),
            },
            trading_levels={},
            stop_losses={},
            vix_triggers={},
            yield_triggers={},
            pre_event_dates=[today_str],
        )

        intent = _make_intent(scenario="base")

        validator = OrderValidator(config, tmp_db)
        result = validator.validate(intent, strategy_spec, sample_portfolio)

        # No freeze error because scenario is not changing
        freeze_errors = [e for e in result.errors if "freeze" in e.lower() or "Pre-event" in e]
        assert len(freeze_errors) == 0


class TestFractionalVsWholeShares:
    """Test that order generation handles fractional shares correctly."""

    def test_normal_etfs_get_fractional_shares(self, config):
        """For normal ETFs (SPY, QQQ), fractional shares are generated
        when the target value does not divide evenly by share price."""
        intent = _make_intent(
            target_allocation={
                "SPY": 50.0,
                "BIL": 50.0,
            },
        )
        portfolio = Portfolio(
            account_value=100000,
            cash=100000,
            positions={},
        )
        prices = {"SPY": 683.1, "BIL": 91.5}

        generator = OrderGenerator(config)
        orders = generator.generate(intent, portfolio, prices)

        spy_orders = [o for o in orders if o.symbol == "SPY"]
        assert len(spy_orders) == 1, "Expected exactly one SPY order"

        spy_order = spy_orders[0]
        # $50,000 / $683.1 = ~73.196... shares — should be fractional
        assert spy_order.quantity != int(spy_order.quantity), (
            f"Expected fractional shares for SPY, got {spy_order.quantity}"
        )
        assert spy_order.quantity > 0

    @patch("trading.layer3.order_generator.WHOLE_SHARES_ONLY", frozenset({"SPY"}))
    def test_whole_shares_only_symbol_gets_integer(self, config):
        """If a symbol is in WHOLE_SHARES_ONLY, the order quantity must be
        an integer (floor'd). Currently WHOLE_SHARES_ONLY is empty, so this
        test verifies the mechanism by temporarily patching the constant."""
        intent = _make_intent(
            target_allocation={
                "SPY": 50.0,
                "BIL": 50.0,
            },
        )
        portfolio = Portfolio(
            account_value=100000,
            cash=100000,
            positions={},
        )
        prices = {"SPY": 683.1, "BIL": 91.5}

        generator = OrderGenerator(config)
        orders = generator.generate(intent, portfolio, prices)

        spy_orders = [o for o in orders if o.symbol == "SPY"]
        assert len(spy_orders) == 1
        assert spy_orders[0].quantity == int(spy_orders[0].quantity), (
            f"Expected whole shares for SPY, got {spy_orders[0].quantity}"
        )


class TestSellOrdersBeforeBuyOrders:
    """Verify that generated orders place sells before buys (to free up cash)."""

    def test_sells_come_first(self, config):
        """When an intent requires both selling one position and buying another,
        the sell orders precede buy orders in the returned list."""
        # Portfolio: heavy SPY, no GLD
        portfolio = Portfolio(
            account_value=100000,
            cash=5000,
            positions={
                "SPY": Position(
                    symbol="SPY", shares=73.0,
                    market_value=50000, cost_basis=48000,
                    current_price=683.1,
                ),
                "BIL": Position(
                    symbol="BIL", shares=493.0,
                    market_value=45000, cost_basis=45000,
                    current_price=91.5,
                ),
            },
        )

        # Target: reduce SPY from 50% to 30%, add GLD at 20%
        intent = _make_intent(
            target_allocation={
                "SPY": 30.0,
                "GLD": 20.0,
                "BIL": 50.0,
            },
        )
        prices = {"SPY": 683.1, "GLD": 545.4, "BIL": 91.5}

        generator = OrderGenerator(config)
        orders = generator.generate(intent, portfolio, prices)

        assert len(orders) >= 2, f"Expected at least 2 orders, got {len(orders)}"

        # Find the transition point from sell to buy
        sell_indices = [i for i, o in enumerate(orders) if o.side == "sell"]
        buy_indices = [i for i, o in enumerate(orders) if o.side == "buy"]

        if sell_indices and buy_indices:
            max_sell_idx = max(sell_indices)
            min_buy_idx = min(buy_indices)
            assert max_sell_idx < min_buy_idx, (
                f"Sell orders (indices {sell_indices}) should all come before "
                f"buy orders (indices {buy_indices})"
            )


class TestDryRunDoesNotSubmit:
    """In dry_run mode, OrderExecutor should log but not actually submit orders."""

    def test_dry_run_returns_dry_run_status(self, config, tmp_db):
        """Orders executed in dry_run mode return status='dry_run' and order_id=None."""
        executor = OrderExecutor(config, tmp_db)  # config.dry_run = True
        order = Order(
            client_order_id="test_dry_001",
            symbol="SPY",
            side="buy",
            quantity=1.5,
            order_type="limit",
            limit_price=683.0,
        )

        results = executor.execute([order])

        assert len(results) == 1
        assert results[0]["status"] == "dry_run"
        assert results[0]["order_id"] is None
        assert results[0]["client_order_id"] == "test_dry_001"
        assert results[0]["filled_price"] == 683.0  # limit_price used as filled_price

    def test_dry_run_saves_to_database(self, config, tmp_db):
        """Even in dry_run mode, the trade is recorded in the database."""
        executor = OrderExecutor(config, tmp_db)
        order = Order(
            client_order_id="test_dry_db_001",
            symbol="QQQ",
            side="sell",
            quantity=5.0,
            order_type="limit",
            limit_price=531.0,
        )

        executor.execute([order])

        # Verify trade was saved to DB
        trades = tmp_db.get_recent_trades(limit=1)
        assert len(trades) == 1
        assert trades[0]["client_order_id"] == "test_dry_db_001"
        assert trades[0]["symbol"] == "QQQ"
        assert trades[0]["status"] == "dry_run"

    def test_dry_run_multiple_orders(self, config, tmp_db):
        """Multiple orders in dry_run mode are all processed without submitting."""
        executor = OrderExecutor(config, tmp_db)
        orders = [
            Order(
                client_order_id=f"test_dry_multi_{i}",
                symbol=sym,
                side="buy",
                quantity=1.0,
                order_type="limit",
                limit_price=price,
            )
            for i, (sym, price) in enumerate([
                ("SPY", 683.0), ("QQQ", 531.0), ("GLD", 545.0),
            ])
        ]

        results = executor.execute(orders)

        assert len(results) == 3
        for r in results:
            assert r["status"] == "dry_run"
            assert r["order_id"] is None


class TestOrderGeneratorNoPriceSkips:
    """When a price is missing for a symbol, that symbol is skipped."""

    def test_missing_price_skips_symbol(self, config):
        """If prices dict lacks a symbol, no order is generated for it."""
        intent = _make_intent(
            target_allocation={
                "SPY": 40.0,
                "GLD": 30.0,
                "BIL": 30.0,
            },
        )
        portfolio = Portfolio(
            account_value=100000,
            cash=100000,
            positions={},
        )
        # Only provide price for SPY, not GLD or BIL
        prices = {"SPY": 683.1}

        generator = OrderGenerator(config)
        orders = generator.generate(intent, portfolio, prices)

        symbols_in_orders = {o.symbol for o in orders}
        assert "SPY" in symbols_in_orders
        assert "GLD" not in symbols_in_orders, "GLD should be skipped (no price)"
        assert "BIL" not in symbols_in_orders, "BIL should be skipped (no price)"

    def test_zero_price_skips_symbol(self, config):
        """A zero price is treated as missing (no order generated)."""
        intent = _make_intent(
            target_allocation={
                "SPY": 50.0,
                "GLD": 50.0,
            },
        )
        portfolio = Portfolio(
            account_value=100000,
            cash=100000,
            positions={},
        )
        prices = {"SPY": 683.1, "GLD": 0.0}

        generator = OrderGenerator(config)
        orders = generator.generate(intent, portfolio, prices)

        symbols_in_orders = {o.symbol for o in orders}
        assert "SPY" in symbols_in_orders
        assert "GLD" not in symbols_in_orders


class TestLossCalculatorPremarketSafety:
    """Before 9:30 when no daily snapshot exists, daily_loss_pct returns None
    and kill switch skips the daily loss check."""

    def test_daily_loss_none_without_snapshot(self, tmp_db):
        """When no daily snapshot exists (e.g., pre-market), daily_loss_pct
        returns None rather than crashing or returning 0."""
        calc = LossCalculator(tmp_db)
        portfolio = _make_portfolio(100000.0)

        result = calc.daily_loss_pct(portfolio)
        assert result is None

    def test_kill_switch_skips_daily_when_none(self, tmp_db, config):
        """KillSwitch does not HALT for daily loss when no snapshot exists,
        even if the portfolio value appears to have changed significantly."""
        # No daily snapshot saved
        # No weekly snapshot saved
        # HWM = 0 means drawdown = 0.0 (safe)
        ks = KillSwitch(config, tmp_db)
        market_data = _make_market_data(vix=18.0)
        portfolio = _make_portfolio(50000.0)  # 50% of hypothetical start

        result = ks.check(market_data, portfolio)

        # Should not halt because daily_loss_pct returns None (skipped)
        # and weekly_loss_pct returns None (skipped)
        # and drawdown = (50000-0)/0 => 0.0 (safe, HWM never set)
        assert result is None

    def test_daily_loss_returns_value_with_snapshot(self, tmp_db):
        """When a daily snapshot exists, daily_loss_pct returns a valid float."""
        today = date.today()
        tmp_db.save_opening_snapshot("daily_open", today, 100000)

        calc = LossCalculator(tmp_db)
        portfolio = _make_portfolio(98000.0)

        result = calc.daily_loss_pct(portfolio)
        assert result is not None
        assert result == pytest.approx(-2.0)

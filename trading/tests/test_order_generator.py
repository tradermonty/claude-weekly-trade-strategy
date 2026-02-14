"""Tests for the Layer 3 OrderGenerator."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from trading.config import TradingConfig
from trading.data.models import (
    Order,
    Portfolio,
    Position,
    StrategyIntent,
)
from trading.layer3.order_generator import OrderGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRICES: dict[str, float] = {
    "SPY": 683.1,
    "QQQ": 531.2,
    "DIA": 441.3,
    "XLV": 150.0,
    "XLP": 100.0,
    "GLD": 545.4,
    "XLE": 100.0,
    "BIL": 91.5,
}


def _base_intent(**overrides) -> StrategyIntent:
    """Return a StrategyIntent for the base scenario."""
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


def _portfolio_for_buys() -> Portfolio:
    """Portfolio where most positions are BELOW target => buys needed.

    Account value = 100K.  Every position is ~50% of target allocation
    so the generator should produce buy orders for each.
    """
    return Portfolio(
        account_value=100000,
        cash=60000,
        positions={
            "SPY": Position("SPY", 16.0, 11000.0, 10000.0, 683.1),  # 11% vs target 22%
            "QQQ": Position("QQQ", 3.8, 2000.0, 1800.0, 531.2),    # 2% vs target 4%
            "DIA": Position("DIA", 9.0, 4000.0, 3900.0, 441.3),    # 4% vs target 8%
            "XLV": Position("XLV", 40.0, 6000.0, 5500.0, 150.0),   # 6% vs target 12%
            "XLP": Position("XLP", 20.0, 2000.0, 1900.0, 100.0),   # 2% vs target 4%
            "GLD": Position("GLD", 11.0, 6000.0, 5000.0, 545.4),   # 6% vs target 12%
            "XLE": Position("XLE", 50.0, 5000.0, 4500.0, 100.0),   # 5% vs target 10%
            "BIL": Position("BIL", 150.0, 14000.0, 13500.0, 91.5), # 14% vs target 28%
        },
    )


def _portfolio_for_sells() -> Portfolio:
    """Portfolio where most positions are ABOVE target => sells needed."""
    return Portfolio(
        account_value=100000,
        cash=5000,
        positions={
            "SPY": Position("SPY", 55.0, 37000.0, 35000.0, 683.1),  # 37% vs target 22%
            "QQQ": Position("QQQ", 15.0, 8000.0, 7000.0, 531.2),   # 8% vs target 4%
            "DIA": Position("DIA", 30.0, 13000.0, 12000.0, 441.3),  # 13% vs target 8%
            "XLV": Position("XLV", 100.0, 15000.0, 14000.0, 150.0), # 15% vs target 12%
            "XLP": Position("XLP", 50.0, 5000.0, 4500.0, 100.0),    # 5% vs target 4%
            "GLD": Position("GLD", 18.0, 10000.0, 9000.0, 545.4),   # 10% vs target 12%
            "XLE": Position("XLE", 70.0, 7000.0, 6500.0, 100.0),    # 7% vs target 10%
        },
    )


# ===================================================================
# OrderGenerator.generate()
# ===================================================================


class TestGenerateOrders:
    """Tests for order generation logic."""

    def test_generates_buy_orders(self, config):
        """When target > current, generates buy orders."""
        gen = OrderGenerator(config)
        intent = _base_intent()
        portfolio = _portfolio_for_buys()

        orders = gen.generate(intent, portfolio, PRICES)

        buy_orders = [o for o in orders if o.side == "buy"]
        assert len(buy_orders) > 0

        # Every order should be a buy (portfolio is below target on all positions)
        buy_symbols = {o.symbol for o in buy_orders}
        # SPY, QQQ, DIA, XLV, XLP, GLD, XLE, BIL are all below target
        assert "SPY" in buy_symbols

    def test_generates_sell_orders(self, config):
        """When target < current, generates sell orders."""
        gen = OrderGenerator(config)
        intent = _base_intent()
        portfolio = _portfolio_for_sells()

        orders = gen.generate(intent, portfolio, PRICES)

        sell_orders = [o for o in orders if o.side == "sell"]
        assert len(sell_orders) > 0

        # SPY is 37% vs target 22% => should generate a sell
        spy_sells = [o for o in sell_orders if o.symbol == "SPY"]
        assert len(spy_sells) == 1

    def test_sells_before_buys(self, config):
        """Sell orders should come before buy orders in the returned list.

        Create a mixed scenario: some positions above target, some below.
        """
        gen = OrderGenerator(config)

        # Mixed portfolio: SPY over-allocated, BIL under-allocated
        portfolio = Portfolio(
            account_value=100000,
            cash=10000,
            positions={
                "SPY": Position("SPY", 55.0, 37000.0, 35000.0, 683.1),  # 37% vs 22%
                "QQQ": Position("QQQ", 7.5, 4000.0, 3500.0, 531.2),    # 4% = target
                "DIA": Position("DIA", 18.1, 8000.0, 7800.0, 441.3),   # 8% = target
                "XLV": Position("XLV", 80.0, 12000.0, 11500.0, 150.0), # 12% = target
                "XLP": Position("XLP", 40.0, 4000.0, 3800.0, 100.0),   # 4% = target
                "GLD": Position("GLD", 22.0, 12000.0, 10000.0, 545.4), # 12% = target
                "XLE": Position("XLE", 100.0, 10000.0, 9500.0, 100.0), # 10% = target
                "BIL": Position("BIL", 35.0, 3000.0, 3000.0, 91.5),   # 3% vs 28%
            },
        )

        intent = _base_intent()
        orders = gen.generate(intent, portfolio, PRICES)

        # Should have at least one sell (SPY) and one buy (BIL)
        sell_orders = [o for o in orders if o.side == "sell"]
        buy_orders = [o for o in orders if o.side == "buy"]
        assert len(sell_orders) > 0
        assert len(buy_orders) > 0

        # Find the last sell index and first buy index
        last_sell_idx = max(i for i, o in enumerate(orders) if o.side == "sell")
        first_buy_idx = min(i for i, o in enumerate(orders) if o.side == "buy")
        assert last_sell_idx < first_buy_idx

    def test_skips_small_trades(self, config):
        """Trades below min threshold should be skipped.

        min_trade_pct=0.5% of 100K = $500, min_trade_usd=$100.
        Threshold = max(500, 100) = $500.
        A position that differs by only $200 from target should be skipped.
        """
        gen = OrderGenerator(config)

        # QQQ target = 4% = $4000.  Current QQQ = $3600 => delta = $400 < $500
        portfolio = Portfolio(
            account_value=100000,
            cash=28000,
            positions={
                "SPY": Position("SPY", 32.2, 22000.0, 20000.0, 683.1),
                "QQQ": Position("QQQ", 6.8, 3600.0, 3400.0, 531.2),   # $400 short of target
                "DIA": Position("DIA", 18.1, 8000.0, 7800.0, 441.3),
                "XLV": Position("XLV", 80.0, 12000.0, 11500.0, 150.0),
                "XLP": Position("XLP", 40.0, 4000.0, 3800.0, 100.0),
                "GLD": Position("GLD", 22.0, 12000.0, 10000.0, 545.4),
                "XLE": Position("XLE", 100.0, 10000.0, 9500.0, 100.0),
                "BIL": Position("BIL", 300.0, 28400.0, 28000.0, 91.5),
            },
        )

        intent = _base_intent()
        orders = gen.generate(intent, portfolio, PRICES)

        # QQQ should NOT appear in orders (delta $400 < threshold $500)
        qqq_orders = [o for o in orders if o.symbol == "QQQ"]
        assert len(qqq_orders) == 0

    def test_client_order_id_format(self, config):
        """Client order ID format: {YYYYMMDD}_{run_id}_{symbol}_{scenario}."""
        gen = OrderGenerator(config)
        intent = _base_intent(run_id="abc999")
        portfolio = _portfolio_for_buys()

        orders = gen.generate(intent, portfolio, PRICES)

        today_str = date.today().strftime("%Y%m%d")
        for order in orders:
            assert order.client_order_id.startswith(today_str)
            assert "abc999" in order.client_order_id
            assert order.symbol in order.client_order_id
            assert "base" in order.client_order_id
            # Full format check
            expected_id = f"{today_str}_abc999_{order.symbol}_base"
            assert order.client_order_id == expected_id

    def test_client_order_id_idempotent(self, config):
        """Same intent should produce the same client order IDs across calls."""
        gen = OrderGenerator(config)
        intent = _base_intent(run_id="idem001")
        portfolio = _portfolio_for_buys()

        orders_1 = gen.generate(intent, portfolio, PRICES)
        orders_2 = gen.generate(intent, portfolio, PRICES)

        ids_1 = sorted(o.client_order_id for o in orders_1)
        ids_2 = sorted(o.client_order_id for o in orders_2)

        assert ids_1 == ids_2

    def test_sell_not_more_than_held(self, config):
        """Sell quantity must not exceed the currently held shares.

        Even if target allocation implies selling more than held,
        the generator should cap sells at current_shares.
        """
        gen = OrderGenerator(config)

        # SPY: target 0% (not in allocation), currently holds 10 shares
        portfolio = Portfolio(
            account_value=100000,
            cash=50000,
            positions={
                "SPY": Position("SPY", 10.0, 6831.0, 6500.0, 683.1),
            },
        )

        # Intent with no SPY allocation (everything in BIL)
        intent = _base_intent(
            target_allocation={"BIL": 100.0},
        )

        orders = gen.generate(intent, portfolio, PRICES)

        spy_sells = [o for o in orders if o.symbol == "SPY" and o.side == "sell"]
        assert len(spy_sells) == 1
        # Should sell exactly 10 shares (all held), not more
        assert spy_sells[0].quantity <= 10.0

    def test_no_price_skips(self, config):
        """If a symbol's price is missing, it should be skipped."""
        gen = OrderGenerator(config)
        intent = _base_intent()
        portfolio = _portfolio_for_buys()

        # Provide prices for only a subset -- missing BIL, XLE
        partial_prices = {
            "SPY": 683.1,
            "QQQ": 531.2,
            "DIA": 441.3,
            "XLV": 150.0,
            "XLP": 100.0,
            "GLD": 545.4,
            # "XLE" missing
            # "BIL" missing
        }

        orders = gen.generate(intent, portfolio, partial_prices)

        order_symbols = {o.symbol for o in orders}
        assert "XLE" not in order_symbols
        assert "BIL" not in order_symbols
        # Other symbols should still have orders
        assert "SPY" in order_symbols

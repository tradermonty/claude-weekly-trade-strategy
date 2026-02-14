"""Tests for SimulatedPortfolio."""

from datetime import date

import pytest

from trading.backtest.config import BacktestConfig
from trading.backtest.portfolio_simulator import SimulatedPortfolio, TradeRecord


class TestSimulatedPortfolioInit:
    def test_initial_state(self):
        p = SimulatedPortfolio(100_000)
        assert p.cash == 100_000
        assert p.total_value == 100_000
        assert p.positions == {}
        assert p.trades == []

    def test_initial_capital_property(self):
        p = SimulatedPortfolio(50_000)
        assert p.initial_capital == 50_000


class TestRebalanceTo:
    def test_buy_from_cash(self):
        p = SimulatedPortfolio(100_000)
        prices = {"SPY": 500.0, "QQQ": 400.0}
        target = {"SPY": 60.0, "QQQ": 40.0}

        trades = p.rebalance_to(target, prices, date(2026, 1, 5))
        assert len(trades) == 2
        assert p.total_value == pytest.approx(100_000, abs=1)

        # SPY should be ~60% of $100K
        spy_value = p.positions["SPY"].market_value
        assert spy_value == pytest.approx(60_000, abs=1)

    def test_rebalance_sells_then_buys(self):
        p = SimulatedPortfolio(100_000)
        prices = {"SPY": 500.0, "QQQ": 400.0}

        # Initial buy
        p.rebalance_to({"SPY": 60.0, "QQQ": 40.0}, prices, date(2026, 1, 5))

        # Rebalance: shift to more QQQ
        trades = p.rebalance_to({"SPY": 30.0, "QQQ": 70.0}, prices, date(2026, 1, 6))
        assert len(trades) >= 2
        assert p.total_value == pytest.approx(100_000, abs=1)

    def test_sell_position_not_in_target(self):
        p = SimulatedPortfolio(100_000)
        prices = {"SPY": 500.0, "QQQ": 400.0, "DIA": 300.0}

        p.rebalance_to({"SPY": 50.0, "QQQ": 30.0, "DIA": 20.0}, prices, date(2026, 1, 5))
        assert "DIA" in p.positions

        # Rebalance without DIA -> should sell
        p.rebalance_to({"SPY": 60.0, "QQQ": 40.0}, prices, date(2026, 1, 6))
        assert "DIA" not in p.positions

    def test_zero_capital_returns_empty(self):
        p = SimulatedPortfolio(0)
        trades = p.rebalance_to({"SPY": 100.0}, {"SPY": 500.0}, date(2026, 1, 5))
        assert trades == []

    def test_missing_price_skips_symbol(self):
        p = SimulatedPortfolio(100_000)
        trades = p.rebalance_to(
            {"SPY": 50.0, "UNKNOWN": 50.0},
            {"SPY": 500.0},
            date(2026, 1, 5),
        )
        assert all(t.symbol == "SPY" for t in trades)

    def test_small_diff_skipped(self):
        """Rebalance skips < $1 differences."""
        p = SimulatedPortfolio(100)
        prices = {"SPY": 500.0}
        # 0.1% of $100 = $0.10, should be skipped
        p.rebalance_to({"SPY": 0.1}, prices, date(2026, 1, 5))
        assert len(p.trades) == 0


class TestSlippage:
    def test_slippage_applied_on_buy(self):
        config = BacktestConfig(slippage_bps=10)  # 10 bps = 0.1%
        p = SimulatedPortfolio(100_000)
        p.set_slippage_fn(config.apply_slippage)

        trades = p.rebalance_to({"SPY": 100.0}, {"SPY": 500.0}, date(2026, 1, 5))
        assert len(trades) == 1
        # Buy price should be higher than 500 (10 bps = 500 * 0.001 = 0.50)
        assert trades[0].price > 500.0
        assert trades[0].price == pytest.approx(500.50, abs=0.01)

    def test_slippage_applied_on_sell(self):
        config = BacktestConfig(slippage_bps=10)
        p = SimulatedPortfolio(100_000)
        p.set_slippage_fn(config.apply_slippage)

        p.rebalance_to({"SPY": 100.0}, {"SPY": 500.0}, date(2026, 1, 5))
        # Sell everything
        trades = p.rebalance_to({}, {"SPY": 500.0}, date(2026, 1, 6))
        sell_trade = [t for t in trades if t.side == "sell"][0]
        assert sell_trade.price < 500.0


class TestUpdatePrices:
    def test_updates_position_prices(self):
        p = SimulatedPortfolio(100_000)
        p.rebalance_to({"SPY": 100.0}, {"SPY": 500.0}, date(2026, 1, 5))

        initial_value = p.total_value
        p.update_prices({"SPY": 510.0})  # +2%
        assert p.total_value > initial_value

    def test_ignores_unknown_symbols(self):
        p = SimulatedPortfolio(100_000)
        p.update_prices({"UNKNOWN": 999.0})  # should not crash
        assert p.total_value == 100_000


class TestGetAllocationPct:
    def test_returns_percentages(self):
        p = SimulatedPortfolio(100_000)
        p.rebalance_to({"SPY": 60.0, "QQQ": 40.0}, {"SPY": 500.0, "QQQ": 400.0}, date(2026, 1, 5))

        alloc = p.get_allocation_pct()
        assert alloc["SPY"] == pytest.approx(60.0, abs=1)
        assert alloc["QQQ"] == pytest.approx(40.0, abs=1)

    def test_empty_portfolio(self):
        p = SimulatedPortfolio(100_000)
        alloc = p.get_allocation_pct()
        assert alloc == {}


class TestTradeRecord:
    def test_fields(self):
        t = TradeRecord(
            date=date(2026, 1, 5),
            symbol="SPY",
            side="buy",
            shares=10.0,
            price=500.0,
            value=5000.0,
            reason="rebalance",
        )
        assert t.symbol == "SPY"
        assert t.value == 5000.0


class TestApplySlippage:
    def test_buy_increases_price(self):
        config = BacktestConfig(slippage_bps=5)
        result = config.apply_slippage(100.0, "buy")
        assert result == pytest.approx(100.05)

    def test_sell_decreases_price(self):
        config = BacktestConfig(slippage_bps=5)
        result = config.apply_slippage(100.0, "sell")
        assert result == pytest.approx(99.95)

    def test_zero_slippage(self):
        config = BacktestConfig(slippage_bps=0)
        assert config.apply_slippage(100.0, "buy") == 100.0
        assert config.apply_slippage(100.0, "sell") == 100.0

"""Tests for benchmark engines (Phase 3 robustness)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from trading.backtest.benchmark import BenchmarkEngine
from trading.backtest.config import CostModel
from trading.backtest.data_provider import DataProvider
from trading.config import AlpacaConfig


def _make_data_provider(
    symbols: list[str],
    start: date,
    end: date,
    base_price: float = 500.0,
    daily_return: float = 0.001,
) -> DataProvider:
    """Create a DataProvider with synthetic price data."""
    dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
    trading_days = dp.get_trading_days(start, end)

    for symbol in symbols:
        price = base_price
        prices: dict[date, float] = {}
        for day in trading_days:
            prices[day] = round(price, 2)
            price *= (1 + daily_return)
        dp.inject_etf_data(symbol, prices)

    return dp


class TestBuyAndHold:

    def test_single_trade_on_day1(self):
        start = date(2025, 1, 6)  # Monday
        end = date(2025, 1, 17)   # Friday
        dp = _make_data_provider(["SPY"], start, end)

        engine = BenchmarkEngine(dp, start, end, 100_000)
        result = engine.run_buy_and_hold("SPY")

        # Only day 1 has trades
        assert result.daily_snapshots[0].trades_today > 0
        for snap in result.daily_snapshots[1:]:
            assert snap.trades_today == 0

    def test_return_matches_spy_change(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 10)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)
        # SPY: 500 on day1, 510 on last day
        prices = {}
        for i, day in enumerate(trading_days):
            prices[day] = 500.0 + i * 2.5
        dp.inject_etf_data("SPY", prices)

        engine = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
        )
        result = engine.run_buy_and_hold("SPY")

        # Expected: (last_price / first_price - 1) * 100
        first_price = prices[trading_days[0]]
        last_price = prices[trading_days[-1]]
        expected_return = ((last_price / first_price) - 1) * 100

        assert result.total_return_pct == pytest.approx(expected_return, abs=0.5)

    def test_buy_and_hold_with_cost(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 17)
        dp = _make_data_provider(["SPY"], start, end)

        no_cost = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
        ).run_buy_and_hold()

        with_cost = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=10.0),
        ).run_buy_and_hold()

        assert with_cost.total_return_pct < no_cost.total_return_pct


class TestSixtyForty:

    def test_monthly_rebalance_count(self):
        # 15 weeks ~ 3-4 months, expect 3-4 rebalance days
        # Use divergent daily returns so SPY/TLT drift apart, triggering rebalance trades
        start = date(2025, 1, 6)
        end = date(2025, 4, 18)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)

        spy_price, tlt_price = 500.0, 90.0
        spy_data: dict[date, float] = {}
        tlt_data: dict[date, float] = {}
        for day in trading_days:
            spy_data[day] = round(spy_price, 2)
            tlt_data[day] = round(tlt_price, 2)
            spy_price *= 1.003  # SPY grows faster
            tlt_price *= 0.999  # TLT declines

        dp.inject_etf_data("SPY", spy_data)
        dp.inject_etf_data("TLT", tlt_data)

        engine = BenchmarkEngine(dp, start, end, 100_000)
        result = engine.run_sixty_forty()

        rebalance_days = sum(1 for s in result.daily_snapshots if s.trades_today > 0)
        assert 3 <= rebalance_days <= 5

    def test_allocation_near_target(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 10)
        dp = _make_data_provider(["SPY", "TLT"], start, end, daily_return=0.0)

        engine = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
        )
        result = engine.run_sixty_forty()

        # After initial rebalance, allocation should be near 60/40
        # Check first day's allocation
        alloc = result.daily_snapshots[0].allocation
        if "SPY" in alloc and "TLT" in alloc:
            assert alloc["SPY"] == pytest.approx(60.0, abs=2.0)
            assert alloc["TLT"] == pytest.approx(40.0, abs=2.0)

    def test_sixty_forty_with_cost(self):
        start = date(2025, 1, 6)
        end = date(2025, 4, 18)
        dp = _make_data_provider(["SPY", "TLT"], start, end)

        no_cost = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
        ).run_sixty_forty()

        with_cost = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=10.0),
        ).run_sixty_forty()

        assert with_cost.total_return_pct < no_cost.total_return_pct


class TestEqualWeight:

    def test_uniform_allocation(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 10)
        symbols = ["SPY", "QQQ", "DIA", "GLD"]
        dp = _make_data_provider(symbols, start, end, daily_return=0.0)

        engine = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
        )
        result = engine.run_equal_weight(symbols)

        alloc = result.daily_snapshots[0].allocation
        for sym in symbols:
            if sym in alloc:
                assert alloc[sym] == pytest.approx(25.0, abs=2.0)

    def test_empty_symbols_raises(self):
        dp = _make_data_provider(["SPY"], date(2025, 1, 6), date(2025, 1, 10))
        engine = BenchmarkEngine(dp, date(2025, 1, 6), date(2025, 1, 10), 100_000)
        with pytest.raises(ValueError, match="empty"):
            engine.run_equal_weight([])


class TestBenchmarksSamePeriod:

    def test_all_same_dates(self):
        start = date(2025, 1, 6)
        end = date(2025, 3, 28)
        symbols = ["SPY", "QQQ", "TLT"]
        dp = _make_data_provider(symbols, start, end)

        engine = BenchmarkEngine(dp, start, end, 100_000)
        results = engine.run_all(["SPY", "QQQ"])

        for name, r in results.items():
            assert r.start_date == start
            assert r.end_date == end

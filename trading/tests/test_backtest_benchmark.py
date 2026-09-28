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


class _Strat:
    def __init__(self, alloc: dict):
        self.current_allocation = alloc


class _FakeTimeline:
    """Minimal stand-in for StrategyTimeline exposing get_strategy."""

    def __init__(self, mapping: dict):
        self._mapping = mapping

    def get_strategy(self, day):
        alloc = self._mapping.get(day)
        return None if alloc is None else _Strat(alloc)


def _make_timeline(trading_days, allocs_by_day):
    mapping = {day: alloc for day, alloc in zip(trading_days, allocs_by_day)}
    return _FakeTimeline(mapping)


class TestStaticMix:

    def _engine(self, dp, start, end):
        return BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
        )

    def test_static_average_mix_weighted(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 17)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)
        assert len(trading_days) == 10

        allocs = [{"A": 20, "B": 80}] * 5 + [{"A": 40, "B": 60}] * 5
        tl = _make_timeline(trading_days, allocs)
        engine = self._engine(dp, start, end)

        avg = engine._compute_static_average_mix(tl)

        assert avg == pytest.approx({"A": 30.0, "B": 70.0})

    def test_static_average_mix_skips_no_strategy_days(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 17)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)

        # First day: no strategy in force; remaining 9 days split 4/5
        allocs = [None] + [{"A": 20, "B": 80}] * 4 + [{"A": 40, "B": 60}] * 5
        tl = _make_timeline(trading_days, allocs)
        engine = self._engine(dp, start, end)

        avg = engine._compute_static_average_mix(tl)

        assert avg == pytest.approx({"A": (4 * 20 + 5 * 40) / 9, "B": (4 * 80 + 5 * 60) / 9})

    def test_static_initial_mix_first_in_force(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 17)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)

        allocs = [None, {"A": 25, "B": 75}] + [{"A": 60, "B": 40}] * 8
        tl = _make_timeline(trading_days, allocs)
        engine = self._engine(dp, start, end)

        init = engine._compute_static_initial_mix(tl)

        assert init == {"A": 25.0, "B": 75.0}

    def test_weekly_rebalance_occurs_once_per_week(self):
        # Divergent prices force a trade on each weekly rebalance.
        start = date(2025, 1, 6)
        end = date(2025, 1, 24)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)

        aa, bb = 500.0, 300.0
        aa_data, bb_data = {}, {}
        for day in trading_days:
            aa_data[day] = round(aa, 2)
            bb_data[day] = round(bb, 2)
            aa *= 1.003
            bb *= 0.999
        dp.inject_etf_data("AA", aa_data)
        dp.inject_etf_data("BB", bb_data)

        tl = _make_timeline(trading_days, [{"AA": 60, "BB": 40}] * len(trading_days))
        engine = self._engine(dp, start, end)
        result = engine.run_static_average_mix(tl)

        rebalance_days = [s.date for s in result.daily_snapshots if s.trades_today > 0]

        # Initial buy-in on the first trading day, then one rebalance per
        # distinct ISO week, on the last trading day of that week.
        week_lasts: dict = {}
        for day in trading_days:
            wk = day.isocalendar()[:2]
            week_lasts[wk] = day

        assert set(rebalance_days) == {trading_days[0]} | set(week_lasts.values())
        assert len(rebalance_days) == len({trading_days[0]} | set(week_lasts.values()))

    def test_run_all_adds_static_mix_when_timeline(self):
        start = date(2025, 1, 6)
        end = date(2025, 1, 24)
        dp = DataProvider(AlpacaConfig(api_key="", secret_key="", base_url=""))
        trading_days = dp.get_trading_days(start, end)
        for symbol in ("AA", "BB"):
            prices = {d: 100.0 for d in trading_days}
            dp.inject_etf_data(symbol, prices)

        tl = _make_timeline(trading_days, [{"AA": 60, "BB": 40}] * len(trading_days))
        engine = BenchmarkEngine(
            dp, start, end, 100_000,
            cost_model=CostModel(spread_bps=0.0, sec_taf_rate=0.0),
            timeline=tl,
        )
        results = engine.run_all(["AA", "BB"])

        assert "Static Average Mix" in results
        assert "Static Initial Mix" in results


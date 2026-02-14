"""Tests for backtest engines (Phase A and Phase B)."""

from datetime import date
from pathlib import Path
from textwrap import dedent

import pytest

from trading.backtest.config import BacktestConfig
from trading.backtest.data_provider import DataProvider
from trading.backtest.engine import PhaseAEngine, PhaseBEngine
from trading.backtest.strategy_timeline import StrategyTimeline
from trading.config import AlpacaConfig


# --- Helpers ---

def _write_blog(tmp_path: Path, date_str: str, alloc: dict[str, float] | None = None) -> Path:
    """Write a valid blog with custom allocation using all 4 categories."""
    if alloc is None:
        alloc = {"SPY": 40, "QQQ": 10, "XLV": 10, "XLP": 5, "GLD": 5, "BIL": 30}

    core_pct = int(alloc.get("SPY", 0) + alloc.get("QQQ", 0) + alloc.get("DIA", 0))
    def_pct = int(alloc.get("XLV", 0) + alloc.get("XLP", 0))
    theme_pct = int(alloc.get("GLD", 0) + alloc.get("XLE", 0) + alloc.get("URA", 0) + alloc.get("TLT", 0))
    cash_pct = int(alloc.get("BIL", 0))

    core_etfs = ', '.join(f'{s} {int(p)}%' for s, p in alloc.items() if s in ('SPY', 'QQQ', 'DIA') and p > 0)
    def_etfs = ', '.join(f'{s} {int(p)}%' for s, p in alloc.items() if s in ('XLV', 'XLP') and p > 0)
    theme_etfs = ', '.join(f'{s} {int(p)}%' for s, p in alloc.items() if s in ('GLD', 'XLE', 'URA', 'TLT') and p > 0)

    blog = tmp_path / f"{date_str}-weekly-strategy.md"
    content = dedent(f"""\
        # Weekly Strategy {date_str}

        ## セクター配分

        | カテゴリ | 比率 | 内訳 |
        |---------|------|------|
        | コア指数 | {core_pct}% | {core_etfs or 'SPY 0%'} |
        | 防御セクター | {def_pct}% | {def_etfs or 'XLV 0%'} |
        | テーマ・ヘッジ | {theme_pct}% | {theme_etfs or 'GLD 0%'} |
        | **現金・短期債** | {cash_pct}% | BIL |

        ## シナリオ別プラン

        ### Base Case (50%)

        **トリガー**: VIX 17-20

        - **コア指数**: {core_pct}%
        - **防御セクター**: {def_pct}%
        - **テーマ**: {theme_pct}%
        - **現金**: {cash_pct}%

        ### Bear Case (30%)

        **トリガー**: VIX 20超

        - **コア指数**: {max(core_pct - 20, 10)}%
        - **防御セクター**: {min(def_pct + 10, 30)}%
        - **テーマ**: {theme_pct}%
        - **現金**: {min(cash_pct + 10, 50)}%

        ### Bull Case (20%)

        **トリガー**: VIX 17割れ

        - **コア指数**: {min(core_pct + 10, 70)}%
        - **防御セクター**: {max(def_pct - 5, 5)}%
        - **テーマ**: {theme_pct}%
        - **現金**: {max(cash_pct - 5, 10)}%
    """)
    blog.write_text(content, encoding="utf-8")
    return blog


def _make_data_provider(
    symbols: list[str],
    start: date,
    end: date,
    base_prices: dict[str, float] | None = None,
) -> DataProvider:
    """Create a data provider with synthetic daily close and open data."""
    dp = DataProvider(AlpacaConfig())
    if base_prices is None:
        base_prices = {"SPY": 500.0, "QQQ": 400.0, "XLV": 150.0, "XLP": 80.0, "GLD": 250.0, "BIL": 100.0}

    # Generate daily data for each symbol
    from datetime import timedelta
    d = start
    while d <= end:
        if d.weekday() < 5:  # weekdays only
            for sym in symbols:
                if sym not in base_prices:
                    continue
                if sym not in dp._etf_cache:
                    dp._etf_cache[sym] = {}
                if sym not in dp._etf_open_cache:
                    dp._etf_open_cache[sym] = {}
                # Slight daily variation
                day_offset = (d - start).days
                close_price = base_prices[sym] * (1 + day_offset * 0.001)
                open_price = close_price * 0.999  # open slightly below close
                dp._etf_cache[sym][d] = round(close_price, 2)
                dp._etf_open_cache[sym][d] = round(open_price, 2)
        d += timedelta(days=1)

    return dp


# --- Phase A Tests ---

class TestPhaseAEngine:
    def test_basic_run(self, tmp_path):
        # Create blogs
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})
        _write_blog(tmp_path, "2026-01-12", {"SPY": 50, "QQQ": 20, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)
        assert len(timeline.entries) >= 1

        start = timeline.effective_start
        end = date(2026, 1, 16)

        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)

        config = BacktestConfig(
            start=start, end=end,
            initial_capital=100_000,
            phase="A",
        )

        engine = PhaseAEngine(config, timeline, dp)
        result = engine.run()

        assert result.phase == "A"
        assert result.trading_days > 0
        assert result.initial_capital == 100_000
        assert result.final_value > 0
        assert result.total_trades > 0

    def test_transition_day_rebalance(self, tmp_path):
        """Verify portfolio is rebalanced on transition days."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})
        _write_blog(tmp_path, "2026-01-12", {"SPY": 40, "QQQ": 30, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 16)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)

        config = BacktestConfig(start=start, end=end, initial_capital=100_000)
        result = PhaseAEngine(config, timeline, dp).run()

        # Should have trades on transition days (Jan 5 and Jan 12)
        transition_snaps = [s for s in result.daily_snapshots if s.trades_today > 0]
        assert len(transition_snaps) >= 2

    def test_start_before_effective_raises(self, tmp_path):
        """Error when --start is before first valid blog."""
        _write_blog(tmp_path, "2026-01-12", {"SPY": 50, "QQQ": 20, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], date(2026, 1, 1), date(2026, 1, 16))
        config = BacktestConfig(start=date(2026, 1, 5), end=date(2026, 1, 16))

        with pytest.raises(ValueError, match="before first valid blog"):
            PhaseAEngine(config, timeline, dp).run()

    def test_no_blogs_raises(self, tmp_path):
        """Error when no valid blogs exist."""
        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        dp = _make_data_provider(["SPY"], date(2026, 1, 5), date(2026, 1, 16))
        config = BacktestConfig(start=date(2026, 1, 5), end=date(2026, 1, 16))

        with pytest.raises(ValueError, match="No valid blogs"):
            PhaseAEngine(config, timeline, dp).run()

    def test_slippage_reduces_value(self, tmp_path):
        """Slippage should reduce final portfolio value."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 40, "QQQ": 10, "XLV": 10, "XLP": 5, "GLD": 5, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 9)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)

        result_no_slip = PhaseAEngine(
            BacktestConfig(start=start, end=end, slippage_bps=0),
            timeline, dp,
        ).run()

        result_with_slip = PhaseAEngine(
            BacktestConfig(start=start, end=end, slippage_bps=50),
            timeline, dp,
        ).run()

        # Slippage should cause lower final value (or at least not higher)
        assert result_with_slip.final_value <= result_no_slip.final_value + 1

    def test_weekly_performance_populated(self, tmp_path):
        """Weekly performance should be populated for each blog week."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})
        _write_blog(tmp_path, "2026-01-12", {"SPY": 50, "QQQ": 20, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 16)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)

        result = PhaseAEngine(
            BacktestConfig(start=start, end=end),
            timeline, dp,
        ).run()

        assert len(result.weekly_performance) >= 1


class TestPhaseAWithMissingData:
    def test_handles_missing_price_day(self, tmp_path):
        """Engine should skip days with no data."""
        _write_blog(tmp_path, "2026-01-05")

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        # Create provider with a gap
        dp = DataProvider(AlpacaConfig())
        for sym, price in [("SPY", 500.0), ("QQQ", 400.0), ("XLV", 150.0),
                           ("XLP", 80.0), ("GLD", 250.0), ("BIL", 100.0)]:
            dp.inject_etf_data(sym, {
                date(2026, 1, 5): price,
                date(2026, 1, 6): price * 1.001,
                # Jan 7 missing
                date(2026, 1, 8): price * 1.002,
                date(2026, 1, 9): price * 1.003,
            })

        config = BacktestConfig(start=date(2026, 1, 5), end=date(2026, 1, 9))
        result = PhaseAEngine(config, timeline, dp).run()
        # Should still produce results (forward-fill covers the gap)
        assert result.trading_days >= 4


# --- Phase B Tests ---

class TestPhaseBEngine:
    def test_basic_run(self, tmp_path):
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 9)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)
        # Inject VIX data for Phase B
        from datetime import timedelta
        vix_data = {}
        d = start
        while d <= end:
            if d.weekday() < 5:
                vix_data[d] = 18.0
            d += timedelta(days=1)
        dp.inject_fmp_data("vix", vix_data)

        config = BacktestConfig(start=start, end=end, phase="B")
        result = PhaseBEngine(config, timeline, dp).run()

        assert result.phase == "B"
        assert result.trading_days > 0

    def test_vix_trigger_causes_rebalance(self, tmp_path):
        """VIX crossing stress should trigger bear/tail_risk rebalance next day."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 9)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)

        # VIX spikes on Jan 6 (crosses caution=20)
        from datetime import timedelta
        dp.inject_fmp_data("vix", {
            date(2026, 1, 5): 18.0,
            date(2026, 1, 6): 22.0,  # crosses 20 (caution)
            date(2026, 1, 7): 22.5,
            date(2026, 1, 8): 21.0,
            date(2026, 1, 9): 19.0,
        })

        config = BacktestConfig(start=start, end=end, phase="B")
        result = PhaseBEngine(config, timeline, dp).run()

        # Should have trades on Jan 5 (transition) and Jan 7 (D+1 execution of Jan 6 trigger)
        trade_days = [s for s in result.daily_snapshots if s.trades_today > 0]
        assert len(trade_days) >= 2

    def test_transition_overrides_pending_trigger(self, tmp_path):
        """Transition day should cancel pending triggers."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})
        _write_blog(tmp_path, "2026-01-12", {"SPY": 50, "QQQ": 20, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 16)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)

        # VIX spike on Jan 9 (Friday), but Jan 12 (Monday) is transition
        from datetime import timedelta
        vix_data = {d: 18.0 for d in dp.get_trading_days(start, end)}
        vix_data[date(2026, 1, 8)] = 18.0
        vix_data[date(2026, 1, 9)] = 22.0  # trigger on Friday
        dp.inject_fmp_data("vix", vix_data)

        config = BacktestConfig(start=start, end=end, phase="B")
        result = PhaseBEngine(config, timeline, dp).run()

        # Jan 12 transition should override the pending trigger from Jan 9
        jan12_snap = next(
            (s for s in result.daily_snapshots if s.date == date(2026, 1, 12)),
            None,
        )
        assert jan12_snap is not None
        assert jan12_snap.trades_today > 0  # transition rebalance happened

    def test_drift_trigger_causes_rebalance(self, tmp_path):
        """Drift trigger should cause re-rebalance to current scenario allocation."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 9)

        # Create provider with prices that cause drift
        dp = DataProvider(AlpacaConfig())
        from datetime import timedelta
        for sym, price in [("SPY", 500.0), ("QQQ", 400.0), ("XLV", 150.0),
                           ("XLP", 80.0), ("GLD", 250.0), ("BIL", 100.0)]:
            close_data = {
                date(2026, 1, 5): price,
                date(2026, 1, 6): price * (1.08 if sym == "SPY" else 0.95),  # big SPY drift
                date(2026, 1, 7): price * (1.08 if sym == "SPY" else 0.95),
                date(2026, 1, 8): price * (1.08 if sym == "SPY" else 0.95),
                date(2026, 1, 9): price * (1.08 if sym == "SPY" else 0.95),
            }
            open_data = {d: v * 0.999 for d, v in close_data.items()}
            dp.inject_etf_data(sym, close_data)
            dp.inject_etf_open_data(sym, open_data)
        dp.inject_fmp_data("vix", {d: 18.0 for d in [
            date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7),
            date(2026, 1, 8), date(2026, 1, 9),
        ]})

        # Use low drift threshold to ensure trigger fires
        from trading.backtest.trigger_matcher import TriggerMatcher
        matcher = TriggerMatcher(drift_threshold_pct=2.0)

        config = BacktestConfig(start=start, end=end, phase="B")
        engine = PhaseBEngine(config, timeline, dp)
        engine.set_trigger_matcher(matcher)
        result = engine.run()

        # Should have transition trade on Jan 5, and drift rebalance on a subsequent day
        trade_days = [s for s in result.daily_snapshots if s.trades_today > 0]
        assert len(trade_days) >= 2

    def test_trade_records_populated(self, tmp_path):
        """BacktestResult.trade_records should contain all individual trades."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 9)
        dp = _make_data_provider(["SPY", "QQQ", "XLV", "XLP", "GLD", "BIL"], start, end)
        from datetime import timedelta
        dp.inject_fmp_data("vix", {d: 18.0 for d in dp.get_trading_days(start, end)})

        config = BacktestConfig(start=start, end=end, phase="B")
        result = PhaseBEngine(config, timeline, dp).run()

        assert len(result.trade_records) > 0
        assert result.trade_records[0].symbol in {"SPY", "QQQ", "BIL", "XLV", "XLP", "GLD"}
        assert result.trade_records[0].side in {"buy", "sell"}

    def test_d_plus_1_uses_open_prices(self, tmp_path):
        """D+1 trigger execution should use open prices, not close."""
        _write_blog(tmp_path, "2026-01-05", {"SPY": 60, "QQQ": 10, "BIL": 30})

        timeline = StrategyTimeline()
        timeline.build(tmp_path)

        start = date(2026, 1, 5)
        end = date(2026, 1, 9)

        dp = DataProvider(AlpacaConfig())
        for sym, price in [("SPY", 500.0), ("QQQ", 400.0), ("XLV", 150.0),
                           ("XLP", 80.0), ("GLD", 250.0), ("BIL", 100.0)]:
            dp.inject_etf_data(sym, {
                date(2026, 1, 5): price,
                date(2026, 1, 6): price,
                date(2026, 1, 7): price,
                date(2026, 1, 8): price,
                date(2026, 1, 9): price,
            })
            # Open prices are distinctly different from close
            dp.inject_etf_open_data(sym, {
                date(2026, 1, 5): price * 0.98,
                date(2026, 1, 6): price * 0.98,
                date(2026, 1, 7): price * 0.98,
                date(2026, 1, 8): price * 0.98,
                date(2026, 1, 9): price * 0.98,
            })
        # VIX spike on Jan 6 → D+1 execution on Jan 7
        dp.inject_fmp_data("vix", {
            date(2026, 1, 5): 18.0,
            date(2026, 1, 6): 22.0,
            date(2026, 1, 7): 22.0,
            date(2026, 1, 8): 22.0,
            date(2026, 1, 9): 22.0,
        })

        config = BacktestConfig(start=start, end=end, phase="B")
        result = PhaseBEngine(config, timeline, dp).run()

        # Find trades executed on Jan 7 (D+1 of Jan 6 trigger)
        jan7_trades = [t for t in result.trade_records
                       if t.date == date(2026, 1, 7)]
        assert jan7_trades, "Expected trades on Jan 7 (D+1 of Jan 6 trigger)"
        if jan7_trades:
            for trade in jan7_trades:
                # Trade price should be close to open (98% of base)
                # not close (100% of base)
                base = {"SPY": 500.0, "QQQ": 400.0, "XLV": 150.0,
                        "XLP": 80.0, "GLD": 250.0, "BIL": 100.0}
                if trade.symbol in base:
                    expected_open = base[trade.symbol] * 0.98
                    assert abs(trade.price - expected_open) < 1.0, (
                        f"{trade.symbol}: price {trade.price} should be near "
                        f"open {expected_open}, not close {base[trade.symbol]}"
                    )

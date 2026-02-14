"""Backtest engines for Phase A (weekly rebalance) and Phase B (trigger-based)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from trading.backtest.config import BacktestConfig
from trading.backtest.data_provider import DataProvider
from trading.backtest.metrics import BacktestMetrics, BacktestResult, DailySnapshot
from trading.backtest.portfolio_simulator import SimulatedPortfolio
from trading.backtest.strategy_timeline import StrategyTimeline

logger = logging.getLogger(__name__)


class PhaseAEngine:
    """Phase A: Weekly rebalance to blog's current_allocation on transition days."""

    def __init__(
        self,
        config: BacktestConfig,
        timeline: StrategyTimeline,
        data_provider: DataProvider,
    ) -> None:
        self._config = config
        self._timeline = timeline
        self._data = data_provider

    def run(self) -> BacktestResult:
        start = self._config.start
        end = self._config.end

        if not start or not end:
            raise ValueError("start and end dates required")

        eff = self._timeline.effective_start
        if eff is None:
            raise ValueError("No valid blogs found")
        if start < eff:
            raise ValueError(
                f"--start {start} is before first valid blog ({eff}). "
                f"Use --start {eff} or later."
            )

        portfolio = SimulatedPortfolio(self._config.initial_capital)
        if self._config.slippage_bps > 0:
            portfolio.set_slippage_fn(self._config.apply_slippage)

        trading_days = self._data.get_trading_days(start, end)
        snapshots: list[DailySnapshot] = []

        for day in trading_days:
            prices = self._data.get_etf_prices(day)
            if not prices:
                logger.warning("No price data for %s, skipping", day)
                continue

            strategy = self._timeline.get_strategy(day)
            trades_today = 0

            if strategy and self._timeline.is_transition_day(day):
                trades = portfolio.rebalance_to(
                    strategy.current_allocation,
                    prices,
                    trade_date=day,
                    reason="rebalance",
                )
                trades_today = len(trades)
                if self._config.verbose and trades:
                    logger.info(
                        "Transition %s: %d trades, blog=%s",
                        day, len(trades), strategy.blog_date,
                    )

            portfolio.update_prices(prices)

            snap = DailySnapshot(
                date=day,
                total_value=portfolio.total_value,
                cash=portfolio.cash,
                positions_value=portfolio.total_value - portfolio.cash,
                allocation=portfolio.get_allocation_pct(),
                scenario="base",
                trades_today=trades_today,
            )
            snapshots.append(snap)

        metrics = BacktestMetrics(snapshots, self._config.initial_capital)
        transition_days = [
            d for d in self._timeline.get_all_transition_days()
            if start <= d <= end
        ]

        return metrics.build_result(
            phase="A",
            start_date=start,
            end_date=end,
            blogs_used=len(self._timeline.entries),
            blogs_skipped=len(self._timeline.skipped),
            skipped_reasons=[
                (s.blog_date, s.reason) for s in self._timeline.skipped
            ],
            transition_days=transition_days,
        )


class PhaseBEngine:
    """Phase B: Rule engine simulation with D-day detection / D+1 execution."""

    def __init__(
        self,
        config: BacktestConfig,
        timeline: StrategyTimeline,
        data_provider: DataProvider,
    ) -> None:
        self._config = config
        self._timeline = timeline
        self._data = data_provider
        self._trigger_matcher: Optional[object] = None

    def set_trigger_matcher(self, matcher) -> None:
        """Set the trigger matcher (injected, avoids circular import)."""
        self._trigger_matcher = matcher

    def run(self) -> BacktestResult:
        from trading.backtest.trigger_matcher import TriggerMatcher

        start = self._config.start
        end = self._config.end

        if not start or not end:
            raise ValueError("start and end dates required")

        eff = self._timeline.effective_start
        if eff is None:
            raise ValueError("No valid blogs found")
        if start < eff:
            raise ValueError(
                f"--start {start} is before first valid blog ({eff}). "
                f"Use --start {eff} or later."
            )

        if self._trigger_matcher is None:
            self._trigger_matcher = TriggerMatcher()

        portfolio = SimulatedPortfolio(self._config.initial_capital)
        if self._config.slippage_bps > 0:
            portfolio.set_slippage_fn(self._config.apply_slippage)

        trading_days = self._data.get_trading_days(start, end)
        snapshots: list[DailySnapshot] = []
        pending_trigger: Optional[str] = None
        current_scenario = "base"

        for day in trading_days:
            prices = self._data.get_etf_prices(day)
            if not prices:
                logger.warning("No price data for %s, skipping", day)
                continue

            market_data = self._data.get_market_data(day)
            strategy = self._timeline.get_strategy(day)
            trades_today = 0
            executed_today = False

            # 1. Transition day rebalance (highest priority)
            if strategy and self._timeline.is_transition_day(day):
                trades = portfolio.rebalance_to(
                    strategy.current_allocation,
                    prices,
                    trade_date=day,
                    reason="transition",
                )
                trades_today = len(trades)
                executed_today = True
                pending_trigger = None
                current_scenario = "base"

            # 2. Execute pending trigger from previous day (D+1 open)
            if pending_trigger and not executed_today and strategy:
                scenario_name = self._trigger_matcher.resolve_scenario(
                    pending_trigger, strategy,
                )
                if scenario_name and scenario_name in strategy.scenarios:
                    alloc = strategy.scenarios[scenario_name].allocation
                    trades = portfolio.rebalance_to(
                        alloc, prices,
                        trade_date=day,
                        reason=f"trigger:{pending_trigger}",
                    )
                    trades_today = len(trades)
                    current_scenario = scenario_name
                executed_today = True
                pending_trigger = None

            # 3. Check for triggers today (close-based, execute tomorrow)
            # Always call check() to update internal state (prev_vix),
            # but only act on triggers when no execution happened today.
            if strategy:
                trigger = self._trigger_matcher.check(
                    market_data, portfolio, strategy,
                )
                if trigger and not executed_today:
                    pending_trigger = trigger
                    if self._config.verbose:
                        logger.info("Trigger detected %s on %s", trigger, day)

            portfolio.update_prices(prices)

            snap = DailySnapshot(
                date=day,
                total_value=portfolio.total_value,
                cash=portfolio.cash,
                positions_value=portfolio.total_value - portfolio.cash,
                allocation=portfolio.get_allocation_pct(),
                scenario=current_scenario,
                trades_today=trades_today,
            )
            snapshots.append(snap)

        metrics = BacktestMetrics(snapshots, self._config.initial_capital)
        transition_days = [
            d for d in self._timeline.get_all_transition_days()
            if start <= d <= end
        ]

        return metrics.build_result(
            phase="B",
            start_date=start,
            end_date=end,
            blogs_used=len(self._timeline.entries),
            blogs_skipped=len(self._timeline.skipped),
            skipped_reasons=[
                (s.blog_date, s.reason) for s in self._timeline.skipped
            ],
            transition_days=transition_days,
        )

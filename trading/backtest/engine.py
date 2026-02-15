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


def _is_last_trading_day_of_week(day: date, trading_days: list[date]) -> bool:
    """Return True if *day* is the last trading day of its ISO week.

    The check looks at the next trading day in the calendar.  If the next
    trading day falls in a different ISO week (or *day* is the very last
    trading day in the list), the current day is the week-end rebalance
    point.
    """
    idx = _bisect_index(trading_days, day)
    if idx is None:
        return False
    if idx == len(trading_days) - 1:
        return True  # last trading day overall
    next_day = trading_days[idx + 1]
    return next_day.isocalendar()[1] != day.isocalendar()[1]


def _bisect_index(trading_days: list[date], day: date) -> Optional[int]:
    """Binary-search *day* in the sorted *trading_days* list."""
    lo, hi = 0, len(trading_days) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if trading_days[mid] == day:
            return mid
        elif trading_days[mid] < day:
            lo = mid + 1
        else:
            hi = mid - 1
    return None


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
        portfolio.set_cost_model(self._config.cost_model)

        trading_days = self._data.get_trading_days(start, end)
        snapshots: list[DailySnapshot] = []

        for day in trading_days:
            prices = self._data.get_etf_prices(day)
            if not prices:
                logger.warning("No price data for %s, skipping", day)
                continue

            strategy = self._timeline.get_strategy(day)
            trades_today = 0

            should_rebalance = False
            if self._config.rebalance_timing == "week_end":
                # Week-end mode: rebalance on transition days AND last
                # trading day of each week.
                if self._timeline.is_transition_day(day):
                    should_rebalance = True
                elif _is_last_trading_day_of_week(day, trading_days):
                    should_rebalance = True
            else:
                # Default transition mode
                if self._timeline.is_transition_day(day):
                    should_rebalance = True

            if strategy and should_rebalance:
                trades = portfolio.rebalance_to(
                    strategy.current_allocation,
                    prices,
                    trade_date=day,
                    reason="rebalance",
                )
                trades_today = len(trades)
                if self._config.verbose and trades:
                    logger.info(
                        "Rebalance %s: %d trades, blog=%s",
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

        metrics = BacktestMetrics(
            snapshots, self._config.initial_capital,
            trade_records=portfolio.trades,
        )
        transition_days = [
            d for d in self._timeline.get_all_transition_days()
            if start <= d <= end
        ]

        phase_label = "A" if self._config.rebalance_timing == "transition" else "A-friday"
        return metrics.build_result(
            phase=phase_label,
            start_date=start,
            end_date=end,
            blogs_used=len(self._timeline.entries),
            blogs_skipped=len(self._timeline.skipped),
            skipped_reasons=[
                (s.blog_date, s.reason) for s in self._timeline.skipped
            ],
            transition_days=transition_days,
            trade_records=portfolio.trades,
            total_cost=portfolio.total_costs,
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
        portfolio.set_cost_model(self._config.cost_model)

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

            # 1. Scheduled rebalance (highest priority)
            is_transition = self._timeline.is_transition_day(day)
            is_week_end = (
                self._config.rebalance_timing == "week_end"
                and _is_last_trading_day_of_week(day, trading_days)
            )
            if strategy and (is_transition or is_week_end):
                trades = portfolio.rebalance_to(
                    strategy.current_allocation,
                    prices,
                    trade_date=day,
                    reason="transition" if is_transition else "week_end_rebalance",
                )
                trades_today = len(trades)
                executed_today = True
                pending_trigger = None
                current_scenario = "base"

            # 2. Execute pending trigger from previous day (D+1 open)
            if pending_trigger and not executed_today and strategy:
                # Use open prices for D+1 execution; fall back to close
                open_prices = self._data.get_etf_open_prices(day)
                exec_prices = {**prices, **open_prices}

                if pending_trigger == "drift":
                    # Drift: re-rebalance to current scenario allocation
                    if current_scenario in strategy.scenarios:
                        alloc = strategy.scenarios[current_scenario].allocation
                    else:
                        alloc = strategy.current_allocation
                    trades = portfolio.rebalance_to(
                        alloc, exec_prices,
                        trade_date=day,
                        reason="trigger:drift",
                    )
                    trades_today = len(trades)
                else:
                    scenario_name = self._trigger_matcher.resolve_scenario(
                        pending_trigger, strategy,
                    )
                    if scenario_name and scenario_name in strategy.scenarios:
                        alloc = strategy.scenarios[scenario_name].allocation
                        current_scenario = scenario_name
                    else:
                        # No candidate matched → fall back to current_allocation
                        alloc = strategy.current_allocation
                    trades = portfolio.rebalance_to(
                        alloc, exec_prices,
                        trade_date=day,
                        reason=f"trigger:{pending_trigger}",
                    )
                    trades_today = len(trades)
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

        metrics = BacktestMetrics(
            snapshots, self._config.initial_capital,
            trade_records=portfolio.trades,
        )
        transition_days = [
            d for d in self._timeline.get_all_transition_days()
            if start <= d <= end
        ]

        phase_label = "B" if self._config.rebalance_timing == "transition" else "B-friday"
        return metrics.build_result(
            phase=phase_label,
            start_date=start,
            end_date=end,
            blogs_used=len(self._timeline.entries),
            blogs_skipped=len(self._timeline.skipped),
            skipped_reasons=[
                (s.blog_date, s.reason) for s in self._timeline.skipped
            ],
            transition_days=transition_days,
            trade_records=portfolio.trades,
            total_cost=portfolio.total_costs,
        )

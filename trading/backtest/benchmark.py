"""Benchmark engines: SPY B&H, 60/40, Equal-Weight for comparison."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from trading.backtest.config import CostModel
from trading.backtest.data_provider import DataProvider
from trading.backtest.metrics import BacktestMetrics, BacktestResult, DailySnapshot
from trading.backtest.portfolio_simulator import SimulatedPortfolio

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """Run benchmark strategies for comparison with blog-based strategies."""

    def __init__(
        self,
        data_provider: DataProvider,
        start: date,
        end: date,
        initial_capital: float = 100_000.0,
        cost_model: Optional[CostModel] = None,
    ) -> None:
        self._data = data_provider
        self._start = start
        self._end = end
        self._initial_capital = initial_capital
        self._cost_model = cost_model or CostModel(spread_bps=0.0, sec_taf_rate=0.0)

    def run_buy_and_hold(self, symbol: str = "SPY") -> BacktestResult:
        """Buy 100% of one symbol on day 1, hold until end."""
        portfolio = SimulatedPortfolio(self._initial_capital)
        portfolio.set_cost_model(self._cost_model)

        trading_days = self._data.get_trading_days(self._start, self._end)
        snapshots: list[DailySnapshot] = []
        bought = False

        for day in trading_days:
            prices = self._data.get_etf_prices(day)
            if not prices or symbol not in prices:
                continue

            trades_today = 0
            if not bought:
                trades = portfolio.rebalance_to(
                    {symbol: 100.0}, prices,
                    trade_date=day, reason="buy_and_hold",
                )
                trades_today = len(trades)
                bought = True
            else:
                portfolio.update_prices(prices)

            snapshots.append(DailySnapshot(
                date=day,
                total_value=portfolio.total_value,
                cash=portfolio.cash,
                positions_value=portfolio.total_value - portfolio.cash,
                allocation=portfolio.get_allocation_pct(),
                scenario="buy_and_hold",
                trades_today=trades_today,
            ))

        return self._build_result(f"SPY B&H", snapshots, portfolio)

    def run_sixty_forty(self) -> BacktestResult:
        """60% SPY + 40% TLT, monthly rebalance."""
        portfolio = SimulatedPortfolio(self._initial_capital)
        portfolio.set_cost_model(self._cost_model)

        trading_days = self._data.get_trading_days(self._start, self._end)
        snapshots: list[DailySnapshot] = []
        last_rebalance_month: Optional[int] = None
        target = {"SPY": 60.0, "TLT": 40.0}

        for day in trading_days:
            prices = self._data.get_etf_prices(day)
            if not prices:
                continue
            if "SPY" not in prices or "TLT" not in prices:
                continue

            trades_today = 0
            month_key = day.year * 12 + day.month

            if last_rebalance_month is None or month_key != last_rebalance_month:
                # First trading day of a new month (or first day overall)
                trades = portfolio.rebalance_to(
                    target, prices,
                    trade_date=day, reason="monthly_rebalance",
                )
                trades_today = len(trades)
                last_rebalance_month = month_key
            else:
                portfolio.update_prices(prices)

            snapshots.append(DailySnapshot(
                date=day,
                total_value=portfolio.total_value,
                cash=portfolio.cash,
                positions_value=portfolio.total_value - portfolio.cash,
                allocation=portfolio.get_allocation_pct(),
                scenario="60/40",
                trades_today=trades_today,
            ))

        return self._build_result("60/40 SPY+TLT", snapshots, portfolio)

    def run_equal_weight(self, symbols: list[str]) -> BacktestResult:
        """Equal-weight across given symbols, monthly rebalance."""
        if not symbols:
            raise ValueError("symbols list cannot be empty")

        portfolio = SimulatedPortfolio(self._initial_capital)
        portfolio.set_cost_model(self._cost_model)

        n = len(symbols)
        target = {s: 100.0 / n for s in symbols}

        trading_days = self._data.get_trading_days(self._start, self._end)
        snapshots: list[DailySnapshot] = []
        last_rebalance_month: Optional[int] = None

        for day in trading_days:
            prices = self._data.get_etf_prices(day)
            if not prices:
                continue
            # Need at least some symbols to have prices
            available = {s: target[s] for s in symbols if s in prices}
            if not available:
                continue

            trades_today = 0
            month_key = day.year * 12 + day.month

            if last_rebalance_month is None or month_key != last_rebalance_month:
                # Redistribute to available symbols only
                n_avail = len(available)
                adj_target = {s: 100.0 / n_avail for s in available}
                trades = portfolio.rebalance_to(
                    adj_target, prices,
                    trade_date=day, reason="monthly_rebalance",
                )
                trades_today = len(trades)
                last_rebalance_month = month_key
            else:
                portfolio.update_prices(prices)

            snapshots.append(DailySnapshot(
                date=day,
                total_value=portfolio.total_value,
                cash=portfolio.cash,
                positions_value=portfolio.total_value - portfolio.cash,
                allocation=portfolio.get_allocation_pct(),
                scenario="equal_weight",
                trades_today=trades_today,
            ))

        return self._build_result("Equal-Weight", snapshots, portfolio)

    def run_all(self, strategy_symbols: list[str]) -> dict[str, BacktestResult]:
        """Run all benchmarks and return results keyed by name."""
        results: dict[str, BacktestResult] = {}

        results["SPY B&H"] = self.run_buy_and_hold("SPY")
        results["60/40 SPY+TLT"] = self.run_sixty_forty()
        results["Equal-Weight"] = self.run_equal_weight(strategy_symbols)

        return results

    def _build_result(
        self,
        name: str,
        snapshots: list[DailySnapshot],
        portfolio: SimulatedPortfolio,
    ) -> BacktestResult:
        metrics = BacktestMetrics(
            snapshots, self._initial_capital,
            trade_records=portfolio.trades,
        )
        return metrics.build_result(
            phase=name,
            start_date=self._start,
            end_date=self._end,
            blogs_used=0,
            blogs_skipped=0,
            skipped_reasons=[],
            transition_days=[],
            trade_records=portfolio.trades,
            total_cost=portfolio.total_costs,
        )

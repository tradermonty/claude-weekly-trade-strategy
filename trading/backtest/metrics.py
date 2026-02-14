"""Performance metrics and snapshot tracking for backtests."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DailySnapshot:
    """Daily portfolio snapshot."""

    date: date
    total_value: float
    cash: float
    positions_value: float
    allocation: dict[str, float] = field(default_factory=dict)  # {symbol: pct}
    scenario: str = ""  # active scenario name
    trades_today: int = 0


@dataclass
class WeeklyPerformance:
    """Performance for one blog week."""

    blog_date: str
    start_value: float
    end_value: float
    return_pct: float
    trades: int
    scenario: str


@dataclass
class BacktestResult:
    """Complete backtest result data."""

    phase: str
    start_date: date
    end_date: date
    trading_days: int
    blogs_used: int
    blogs_skipped: int
    initial_capital: float
    final_value: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_trades: int
    daily_snapshots: list[DailySnapshot] = field(default_factory=list)
    weekly_performance: list[WeeklyPerformance] = field(default_factory=list)
    skipped_reasons: list[tuple[str, str]] = field(default_factory=list)


class BacktestMetrics:
    """Calculate performance metrics from daily snapshots."""

    def __init__(self, snapshots: list[DailySnapshot], initial_capital: float) -> None:
        self._snapshots = snapshots
        self._initial_capital = initial_capital

    @property
    def total_return_pct(self) -> float:
        if not self._snapshots or self._initial_capital <= 0:
            return 0.0
        return ((self._snapshots[-1].total_value / self._initial_capital) - 1) * 100

    @property
    def max_drawdown_pct(self) -> float:
        if not self._snapshots:
            return 0.0
        peak = self._snapshots[0].total_value
        max_dd = 0.0
        for snap in self._snapshots:
            if snap.total_value > peak:
                peak = snap.total_value
            dd = ((snap.total_value - peak) / peak) * 100 if peak > 0 else 0.0
            if dd < max_dd:
                max_dd = dd
        return max_dd

    @property
    def sharpe_ratio(self) -> float:
        """Annualized Sharpe ratio (risk-free rate = 0 for simplicity)."""
        if len(self._snapshots) < 2:
            return 0.0
        daily_returns = self._daily_returns()
        if not daily_returns:
            return 0.0
        mean_r = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return (mean_r / std) * math.sqrt(252)

    @property
    def final_value(self) -> float:
        if not self._snapshots:
            return self._initial_capital
        return self._snapshots[-1].total_value

    @property
    def total_trades(self) -> int:
        return sum(s.trades_today for s in self._snapshots)

    def weekly_performance(
        self,
        transition_days: list[date],
    ) -> list[WeeklyPerformance]:
        """Calculate per-week performance aligned to blog transitions."""
        if not self._snapshots or not transition_days:
            return []

        snap_map = {s.date: s for s in self._snapshots}
        results: list[WeeklyPerformance] = []

        for i, trans_day in enumerate(transition_days):
            # Find end of this week (day before next transition, or last snapshot)
            if i + 1 < len(transition_days):
                end_candidates = [
                    s for s in self._snapshots
                    if s.date >= trans_day and s.date < transition_days[i + 1]
                ]
            else:
                end_candidates = [
                    s for s in self._snapshots if s.date >= trans_day
                ]

            if not end_candidates:
                continue

            start_snap = end_candidates[0]
            end_snap = end_candidates[-1]
            start_val = start_snap.total_value
            end_val = end_snap.total_value
            ret = ((end_val / start_val) - 1) * 100 if start_val > 0 else 0.0
            trades = sum(s.trades_today for s in end_candidates)

            blog_date_str = trans_day.isoformat()
            # Find the matching blog date (transition may differ from blog date)
            scenario = start_snap.scenario or "base"

            results.append(WeeklyPerformance(
                blog_date=blog_date_str,
                start_value=start_val,
                end_value=end_val,
                return_pct=ret,
                trades=trades,
                scenario=scenario,
            ))

        return results

    def build_result(
        self,
        phase: str,
        start_date: date,
        end_date: date,
        blogs_used: int,
        blogs_skipped: int,
        skipped_reasons: list[tuple[str, str]],
        transition_days: list[date],
    ) -> BacktestResult:
        """Build a complete BacktestResult."""
        return BacktestResult(
            phase=phase,
            start_date=start_date,
            end_date=end_date,
            trading_days=len(self._snapshots),
            blogs_used=blogs_used,
            blogs_skipped=blogs_skipped,
            initial_capital=self._initial_capital,
            final_value=self.final_value,
            total_return_pct=self.total_return_pct,
            max_drawdown_pct=self.max_drawdown_pct,
            sharpe_ratio=self.sharpe_ratio,
            total_trades=self.total_trades,
            daily_snapshots=list(self._snapshots),
            weekly_performance=self.weekly_performance(transition_days),
            skipped_reasons=skipped_reasons,
        )

    def _daily_returns(self) -> list[float]:
        """Calculate daily returns as fractions."""
        returns = []
        for i in range(1, len(self._snapshots)):
            prev = self._snapshots[i - 1].total_value
            curr = self._snapshots[i].total_value
            if prev > 0:
                returns.append((curr - prev) / prev)
        return returns

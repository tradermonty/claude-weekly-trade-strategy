"""Backtest configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


@dataclass
class CostModel:
    """Transaction cost model: spread + SEC TAF.

    spread_bps: one-way half-spread in basis points (SPY~1, URA~5-10).
    sec_taf_rate: SEC Transaction Activity Fee per dollar of sell proceeds.
    """

    spread_bps: float = 1.0
    sec_taf_rate: float = 22.90e-6  # $22.90 per $1M sell proceeds (~0.2 bps)

    def calculate_cost(self, side: str, shares: float, price: float) -> float:
        """Return the dollar cost of a trade (spread + TAF for sells)."""
        value = shares * price
        cost = (self.spread_bps / 10_000) * value  # half-spread
        if side == "sell":
            cost += self.sec_taf_rate * value
        return cost


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    start: Optional[date] = None
    end: Optional[date] = None
    initial_capital: float = 100_000.0
    phase: str = "A"  # "A" or "B"
    slippage_bps: float = 0.0  # basis points
    blogs_dir: Path = field(default_factory=lambda: Path("blogs"))
    output_dir: Optional[Path] = None
    verbose: bool = False
    rebalance_timing: str = "transition"  # "transition" or "week_end"
    cost_model: CostModel = field(default_factory=CostModel)

    def apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to a price. Buy pays more, sell receives less."""
        factor = self.slippage_bps / 10_000
        if side == "buy":
            return price * (1 + factor)
        else:
            return price * (1 - factor)

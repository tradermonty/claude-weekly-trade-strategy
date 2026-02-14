"""Backtest configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


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

    def apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to a price. Buy pays more, sell receives less."""
        factor = self.slippage_bps / 10_000
        if side == "buy":
            return price * (1 + factor)
        else:
            return price * (1 - factor)

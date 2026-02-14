"""Simulated portfolio for backtesting."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from trading.core.constants import WHOLE_SHARES_ONLY

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a single simulated trade."""

    date: date
    symbol: str
    side: str  # "buy" or "sell"
    shares: float
    price: float
    value: float  # shares * price
    reason: str = ""  # "rebalance", "trigger:bear", etc.


@dataclass
class _Position:
    """Internal position tracking."""

    symbol: str
    shares: float = 0.0
    cost_basis: float = 0.0  # total cost
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price


class SimulatedPortfolio:
    """Track portfolio state and execute simulated trades."""

    def __init__(self, initial_capital: float) -> None:
        self._cash: float = initial_capital
        self._positions: dict[str, _Position] = {}
        self._initial_capital: float = initial_capital
        self._trades: list[TradeRecord] = []
        self._slippage_fn: Optional[callable] = None

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> dict[str, _Position]:
        return dict(self._positions)

    @property
    def trades(self) -> list[TradeRecord]:
        return list(self._trades)

    @property
    def total_value(self) -> float:
        pos_value = sum(p.market_value for p in self._positions.values())
        return self._cash + pos_value

    @property
    def initial_capital(self) -> float:
        return self._initial_capital

    def set_slippage_fn(self, fn) -> None:
        """Set a slippage function: fn(price, side) -> adjusted_price."""
        self._slippage_fn = fn

    def update_prices(self, prices: dict[str, float]) -> None:
        """Update current prices for mark-to-market valuation."""
        for symbol, price in prices.items():
            if symbol in self._positions:
                self._positions[symbol].current_price = price

    def rebalance_to(
        self,
        target_allocation: dict[str, float],
        prices: dict[str, float],
        trade_date: date = date.min,
        reason: str = "rebalance",
    ) -> list[TradeRecord]:
        """Rebalance portfolio to target allocation percentages.

        Args:
            target_allocation: {symbol: target_pct} where pct is 0-100.
            prices: {symbol: price} for all symbols in target.
            trade_date: Date for trade records.
            reason: Reason string for trade records.

        Returns:
            List of trades executed.
        """
        self.update_prices(prices)
        total = self.total_value
        if total <= 0:
            return []

        trades: list[TradeRecord] = []

        # Sell first (to free up cash), then buy
        sell_orders: list[tuple[str, float]] = []
        buy_orders: list[tuple[str, float]] = []

        for symbol, target_pct in target_allocation.items():
            if symbol not in prices or prices[symbol] <= 0:
                logger.warning("No price for %s, skipping", symbol)
                continue

            target_value = total * (target_pct / 100.0)
            current_value = self._positions[symbol].market_value if symbol in self._positions else 0.0
            diff = target_value - current_value

            if abs(diff) < 1.0:  # less than $1 change, skip
                continue

            if diff < 0:
                sell_orders.append((symbol, diff))
            else:
                buy_orders.append((symbol, diff))

        # Sell positions not in target
        for symbol in list(self._positions.keys()):
            if symbol not in target_allocation or target_allocation.get(symbol, 0) == 0:
                pos = self._positions[symbol]
                if pos.shares > 0:
                    sell_orders.append((symbol, -pos.market_value))

        # Execute sells
        for symbol, diff in sell_orders:
            price = prices.get(symbol)
            if not price or price <= 0:
                continue
            exec_price = self._apply_slippage(price, "sell")
            shares_to_sell = min(
                abs(diff) / exec_price,
                self._positions.get(symbol, _Position(symbol)).shares,
            )
            shares_to_sell = self._round_shares(symbol, shares_to_sell)
            if shares_to_sell <= 0:
                continue

            trade = self._execute_sell(symbol, shares_to_sell, exec_price, trade_date, reason)
            if trade:
                trades.append(trade)

        # Execute buys
        for symbol, diff in buy_orders:
            price = prices.get(symbol)
            if not price or price <= 0:
                continue
            exec_price = self._apply_slippage(price, "buy")
            shares_to_buy = diff / exec_price
            shares_to_buy = self._round_shares(symbol, shares_to_buy)
            cost = shares_to_buy * exec_price
            if cost > self._cash or shares_to_buy <= 0:
                # Buy what we can afford
                shares_to_buy = self._round_shares(symbol, self._cash / exec_price)
                if shares_to_buy <= 0:
                    continue

            trade = self._execute_buy(symbol, shares_to_buy, exec_price, trade_date, reason)
            if trade:
                trades.append(trade)

        return trades

    def get_allocation_pct(self) -> dict[str, float]:
        """Get current allocation as percentages."""
        total = self.total_value
        if total <= 0:
            return {}
        result: dict[str, float] = {}
        for symbol, pos in self._positions.items():
            if pos.shares > 0:
                result[symbol] = (pos.market_value / total) * 100.0
        return result

    def _execute_buy(
        self, symbol: str, shares: float, price: float,
        trade_date: date, reason: str,
    ) -> Optional[TradeRecord]:
        cost = shares * price
        if cost > self._cash + 0.01:  # floating point tolerance
            return None
        cost = min(cost, self._cash)  # prevent negative cash from rounding

        self._cash -= cost
        if symbol not in self._positions:
            self._positions[symbol] = _Position(symbol)
        pos = self._positions[symbol]
        pos.cost_basis += cost
        pos.shares += shares
        pos.current_price = price

        trade = TradeRecord(
            date=trade_date, symbol=symbol, side="buy",
            shares=shares, price=price, value=cost, reason=reason,
        )
        self._trades.append(trade)
        return trade

    def _execute_sell(
        self, symbol: str, shares: float, price: float,
        trade_date: date, reason: str,
    ) -> Optional[TradeRecord]:
        if symbol not in self._positions:
            return None
        pos = self._positions[symbol]
        shares = min(shares, pos.shares)
        if shares <= 0:
            return None

        proceeds = shares * price
        # Adjust cost basis proportionally
        if pos.shares > 0:
            fraction = shares / pos.shares
            pos.cost_basis *= (1 - fraction)
        pos.shares -= shares
        pos.current_price = price
        self._cash += proceeds

        # Remove empty positions
        if pos.shares < 1e-9:
            del self._positions[symbol]

        trade = TradeRecord(
            date=trade_date, symbol=symbol, side="sell",
            shares=shares, price=price, value=proceeds, reason=reason,
        )
        self._trades.append(trade)
        return trade

    def _apply_slippage(self, price: float, side: str) -> float:
        if self._slippage_fn:
            return self._slippage_fn(price, side)
        return price

    @staticmethod
    def _round_shares(symbol: str, shares: float) -> float:
        """Round shares: whole for WHOLE_SHARES_ONLY, else 6 decimal places."""
        if symbol in WHOLE_SHARES_ONLY:
            return float(int(shares))
        return round(shares, 6)

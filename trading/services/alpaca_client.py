"""Alpaca API client wrapping the alpaca-py SDK."""

from __future__ import annotations

import logging
from typing import Optional

from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    ReplaceOrderRequest,
    StopOrderRequest,
)

from trading.config import AlpacaConfig
from trading.data.models import Order, Portfolio, Position

logger = logging.getLogger(__name__)


class AlpacaClient:
    """Thin wrapper around the alpaca-py SDK.

    Converts alpaca-py objects into the project's own data models
    (:class:`Position`, :class:`Portfolio`, :class:`Order`).
    """

    def __init__(self, config: AlpacaConfig) -> None:
        self._config = config
        self._trading = TradingClient(
            api_key=config.api_key,
            secret_key=config.secret_key,
            paper=config.is_paper,
            url_override=config.base_url,
        )
        self._data = StockHistoricalDataClient(
            api_key=config.api_key,
            secret_key=config.secret_key,
        )

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def get_account(self) -> Optional[dict]:
        """Return account info as a plain dict, or *None* on error."""
        try:
            acct = self._trading.get_account()
            return {
                "account_number": acct.account_number,
                "status": str(acct.status),
                "equity": float(acct.equity),
                "cash": float(acct.cash),
                "buying_power": float(acct.buying_power),
                "portfolio_value": float(acct.portfolio_value),
                "currency": acct.currency,
            }
        except APIError as exc:
            logger.error("Alpaca get_account error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self) -> Optional[dict[str, Position]]:
        """Return current positions keyed by symbol."""
        try:
            raw = self._trading.get_all_positions()
            positions: dict[str, Position] = {}
            for p in raw:
                positions[p.symbol] = Position(
                    symbol=p.symbol,
                    shares=float(p.qty),
                    market_value=float(p.market_value),
                    cost_basis=float(p.cost_basis),
                    current_price=float(p.current_price),
                )
            return positions
        except APIError as exc:
            logger.error("Alpaca get_positions error: %s", exc)
            return None

    def get_position(self, symbol: str) -> Optional[Position]:
        """Return a single position, or *None* if not held / on error."""
        try:
            p = self._trading.get_open_position(symbol)
            return Position(
                symbol=p.symbol,
                shares=float(p.qty),
                market_value=float(p.market_value),
                cost_basis=float(p.cost_basis),
                current_price=float(p.current_price),
            )
        except APIError:
            return None

    # ------------------------------------------------------------------
    # Portfolio (convenience)
    # ------------------------------------------------------------------

    def get_portfolio(self) -> Optional[Portfolio]:
        """Build a :class:`Portfolio` from account + positions."""
        acct = self.get_account()
        positions = self.get_positions()
        if acct is None or positions is None:
            return None
        return Portfolio(
            account_value=acct["equity"],
            cash=acct["cash"],
            positions=positions,
        )

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------

    def get_quote(self, symbol: str) -> Optional[float]:
        """Return the latest mid-price for *symbol*, or *None*."""
        try:
            req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self._data.get_stock_latest_quote(req)
            q = quotes.get(symbol)
            if q is None:
                return None
            bid = float(q.bid_price) if q.bid_price else 0.0
            ask = float(q.ask_price) if q.ask_price else 0.0
            if bid and ask:
                return round((bid + ask) / 2, 4)
            return ask or bid or None
        except APIError as exc:
            logger.error("Alpaca get_quote(%s) error: %s", symbol, exc)
            return None

    def get_quotes(self, symbols: list[str]) -> dict[str, float]:
        """Return latest mid-prices for multiple symbols."""
        result: dict[str, float] = {}
        if not symbols:
            return result
        try:
            req = StockLatestQuoteRequest(symbol_or_symbols=symbols)
            quotes = self._data.get_stock_latest_quote(req)
            for sym, q in quotes.items():
                bid = float(q.bid_price) if q.bid_price else 0.0
                ask = float(q.ask_price) if q.ask_price else 0.0
                if bid and ask:
                    result[sym] = round((bid + ask) / 2, 4)
                elif ask or bid:
                    result[sym] = ask or bid
        except APIError as exc:
            logger.error("Alpaca get_quotes error: %s", exc)
        return result

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def submit_order(self, order: Order) -> Optional[dict]:
        """Submit an order and return summary dict, or *None* on error."""
        try:
            tif = _parse_tif(order.time_in_force)
            side = OrderSide.BUY if order.side == "buy" else OrderSide.SELL

            if order.order_type == "market":
                req = MarketOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    time_in_force=tif,
                    client_order_id=order.client_order_id,
                )
            elif order.order_type == "limit":
                req = LimitOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    time_in_force=tif,
                    limit_price=order.limit_price,
                    client_order_id=order.client_order_id,
                )
            elif order.order_type == "stop":
                req = StopOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    time_in_force=tif,
                    stop_price=order.stop_price,
                    client_order_id=order.client_order_id,
                )
            else:
                logger.error("Unknown order_type: %s", order.order_type)
                return None

            result = self._trading.submit_order(req)
            return _order_to_dict(result)
        except APIError as exc:
            logger.error("Alpaca submit_order error: %s", exc)
            return None

    def replace_order(
        self,
        order_id: str,
        qty: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Replace (modify) an existing order."""
        try:
            req = ReplaceOrderRequest(
                qty=qty,
                stop_price=stop_price,
                client_order_id=client_order_id,
            )
            result = self._trading.replace_order_by_id(order_id, req)
            return _order_to_dict(result)
        except APIError as exc:
            logger.error("Alpaca replace_order(%s) error: %s", order_id, exc)
            return None

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order. Returns True on success."""
        try:
            self._trading.cancel_order_by_id(order_id)
            return True
        except APIError as exc:
            logger.error("Alpaca cancel_order(%s) error: %s", order_id, exc)
            return False

    def get_order(self, order_id: str) -> Optional[dict]:
        """Fetch a single order by ID."""
        try:
            result = self._trading.get_order_by_id(order_id)
            return _order_to_dict(result)
        except APIError as exc:
            logger.error("Alpaca get_order(%s) error: %s", order_id, exc)
            return None

    def list_open_stop_orders(self, symbol: str | None = None) -> list[dict]:
        """List open stop orders, optionally filtered by symbol."""
        try:
            req = GetOrdersRequest(
                status=QueryOrderStatus.OPEN,
            )
            orders = self._trading.get_orders(req)
            results: list[dict] = []
            for o in orders:
                if o.order_type != OrderType.STOP:
                    continue
                if symbol and o.symbol != symbol:
                    continue
                results.append(_order_to_dict(o))
            return results
        except APIError as exc:
            logger.error("Alpaca list_open_stop_orders error: %s", exc)
            return []


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_tif(tif_str: str) -> TimeInForce:
    mapping = {
        "day": TimeInForce.DAY,
        "gtc": TimeInForce.GTC,
        "ioc": TimeInForce.IOC,
        "fok": TimeInForce.FOK,
    }
    return mapping.get(tif_str.lower(), TimeInForce.DAY)


def _order_to_dict(order) -> dict:
    """Convert an alpaca-py order object to a plain dict."""
    return {
        "id": str(order.id),
        "client_order_id": order.client_order_id,
        "symbol": order.symbol,
        "side": str(order.side),
        "qty": str(order.qty) if order.qty else None,
        "order_type": str(order.order_type),
        "status": str(order.status),
        "limit_price": str(order.limit_price) if order.limit_price else None,
        "stop_price": str(order.stop_price) if order.stop_price else None,
        "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
        "created_at": str(order.created_at) if order.created_at else None,
    }

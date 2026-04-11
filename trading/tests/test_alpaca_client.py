"""Tests for AlpacaClient and _order_to_dict contract."""

from unittest.mock import MagicMock, patch, PropertyMock

from trading.services.alpaca_client import AlpacaClient, _order_to_dict


def _make_mock_order(**overrides):
    """Create a mock alpaca-py order object with enum-like attributes."""
    from types import SimpleNamespace

    class _FakeEnum:
        """Simulates an alpaca-py Enum whose .value is the plain string."""
        def __init__(self, value):
            self.value = value
        def __str__(self):
            # Python 3.11+ Enum: str() returns "ClassName.MEMBER"
            return f"FakeEnum.{self.value.upper()}"

    defaults = {
        "id": "abc-123",
        "client_order_id": "test-order-001",
        "symbol": "SPY",
        "side": _FakeEnum("buy"),
        "qty": 10,
        "order_type": _FakeEnum("stop"),
        "status": _FakeEnum("filled"),
        "limit_price": None,
        "stop_price": 450.00,
        "filled_avg_price": 449.50,
        "created_at": "2026-04-10T10:00:00Z",
        "filled_at": "2026-04-10T10:01:00Z",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestOrderToDictContract:
    """Verify _order_to_dict returns plain strings for enum fields."""

    def test_normalizes_enums_to_plain_strings(self):
        order = _make_mock_order()
        d = _order_to_dict(order)
        assert d["side"] == "buy"
        assert d["order_type"] == "stop"
        assert d["status"] == "filled"

    def test_canceled_spelling(self):
        from types import SimpleNamespace

        class _Enum:
            def __init__(self, v):
                self.value = v
            def __str__(self):
                return f"OrderStatus.{self.value.upper()}"

        order = _make_mock_order(status=_Enum("canceled"))
        d = _order_to_dict(order)
        assert d["status"] == "canceled"  # American English, single L

    def test_includes_filled_at(self):
        order = _make_mock_order(filled_at="2026-04-10T10:01:00Z")
        d = _order_to_dict(order)
        assert d["filled_at"] == "2026-04-10T10:01:00Z"

    def test_filled_at_none_when_not_filled(self):
        order = _make_mock_order(filled_at=None)
        d = _order_to_dict(order)
        assert d["filled_at"] is None

    def test_all_expected_keys_present(self):
        order = _make_mock_order()
        d = _order_to_dict(order)
        expected_keys = {
            "id", "client_order_id", "symbol", "side", "qty",
            "order_type", "status", "limit_price", "stop_price",
            "filled_avg_price", "created_at", "filled_at",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# AlpacaClient new public methods
# ---------------------------------------------------------------------------

def _make_alpaca_client():
    """Create AlpacaClient with mocked SDK clients."""
    with patch("trading.services.alpaca_client.TradingClient"), \
         patch("trading.services.alpaca_client.StockHistoricalDataClient"):
        from trading.config import AlpacaConfig
        cfg = AlpacaConfig(api_key="test", secret_key="test")
        client = AlpacaClient(cfg)
    return client


class TestListClosedOrders:

    def test_returns_dicts(self):
        client = _make_alpaca_client()
        mock_order = _make_mock_order(status=type("E", (), {"value": "filled"})())
        client._trading.get_orders = MagicMock(return_value=[mock_order])
        result = client.list_closed_orders()
        assert len(result) == 1
        assert result[0]["status"] == "filled"
        assert result[0]["symbol"] == "SPY"

    def test_api_error_returns_empty(self):
        from alpaca.common.exceptions import APIError
        client = _make_alpaca_client()
        client._trading.get_orders = MagicMock(side_effect=APIError(400, "test"))
        result = client.list_closed_orders()
        assert result == []


class TestGetOrderByClientId:

    def test_found(self):
        client = _make_alpaca_client()
        order1 = _make_mock_order(client_order_id="abc-001")
        order2 = _make_mock_order(client_order_id="abc-002")
        client._trading.get_orders = MagicMock(return_value=[order1, order2])
        result = client.get_order_by_client_id("abc-002")
        assert result is not None
        assert result["client_order_id"] == "abc-002"

    def test_not_found(self):
        client = _make_alpaca_client()
        order1 = _make_mock_order(client_order_id="abc-001")
        client._trading.get_orders = MagicMock(return_value=[order1])
        result = client.get_order_by_client_id("xyz-999")
        assert result is None

    def test_api_error_returns_none(self):
        from alpaca.common.exceptions import APIError
        client = _make_alpaca_client()
        client._trading.get_orders = MagicMock(side_effect=APIError(400, "test"))
        result = client.get_order_by_client_id("abc-001")
        assert result is None

"""Tests for the FMPClient class.

All HTTP calls are mocked via unittest.mock so no real API access is needed.
"""

from __future__ import annotations

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from trading.services.fmp_client import FMPClient
from trading.config import FMPConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_urlopen(response_data):
    """Create a mock context-manager response that returns *response_data* as JSON."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = json.dumps(response_data).encode("utf-8")
    return mock_resp


def _make_client() -> FMPClient:
    """Create an FMPClient with a dummy API key."""
    return FMPClient(FMPConfig(api_key="test_key"))


# ---------------------------------------------------------------------------
# fetch_quotes
# ---------------------------------------------------------------------------

class TestFetchQuotes:

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_success(self, mock_urlopen) -> None:
        """Successful quote fetch returns a dict keyed by symbol."""
        mock_urlopen.return_value = _mock_urlopen([
            {"symbol": "^VIX", "price": 20.5, "name": "VIX"},
            {"symbol": "^GSPC", "price": 6828.3, "name": "S&P 500"},
        ])

        client = _make_client()
        result = client.fetch_quotes(["^VIX", "^GSPC"])

        assert result is not None
        assert "^VIX" in result
        assert "^GSPC" in result
        assert result["^VIX"]["price"] == 20.5
        assert result["^GSPC"]["price"] == 6828.3

    def test_empty_list_returns_empty_dict(self) -> None:
        """Passing an empty symbol list returns an empty dict (no HTTP call)."""
        client = _make_client()
        result = client.fetch_quotes([])
        assert result == {}

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_http_error_returns_none(self, mock_urlopen) -> None:
        """An HTTPError from the server results in None."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=BytesIO(b""),
        )

        client = _make_client()
        result = client.fetch_quotes(["^VIX", "^GSPC"])
        assert result is None

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_timeout_returns_none(self, mock_urlopen) -> None:
        """A URLError (network / timeout) results in None."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection timed out")

        client = _make_client()
        result = client.fetch_quotes(["^VIX"])
        assert result is None

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_single_symbol(self, mock_urlopen) -> None:
        """Fetching a single symbol works correctly."""
        mock_urlopen.return_value = _mock_urlopen([
            {"symbol": "^VIX", "price": 15.3},
        ])

        client = _make_client()
        result = client.fetch_quotes(["^VIX"])

        assert result is not None
        assert len(result) == 1
        assert result["^VIX"]["price"] == 15.3

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_json_decode_error_returns_none(self, mock_urlopen) -> None:
        """Malformed JSON from the server results in None."""
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b"not valid json"
        mock_urlopen.return_value = mock_resp

        client = _make_client()
        result = client.fetch_quotes(["^VIX"])
        assert result is None


# ---------------------------------------------------------------------------
# fetch_treasury
# ---------------------------------------------------------------------------

class TestFetchTreasury:

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_success(self, mock_urlopen) -> None:
        """Successful treasury fetch returns yield values."""
        mock_urlopen.return_value = _mock_urlopen([
            {
                "date": "2026-02-14",
                "month1": 5.25,
                "month3": 5.20,
                "year2": 4.50,
                "year5": 4.20,
                "year10": 4.36,
                "year30": 4.55,
            }
        ])

        client = _make_client()
        result = client.fetch_treasury()

        assert result is not None
        assert result["year10"] == 4.36
        assert result["year2"] == 4.50
        assert result["year30"] == 4.55
        # "date" should be excluded from the result
        assert "date" not in result

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_empty_response_returns_none(self, mock_urlopen) -> None:
        """An empty list from the API returns None."""
        mock_urlopen.return_value = _mock_urlopen([])

        client = _make_client()
        result = client.fetch_treasury()
        assert result is None

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_http_error_returns_none(self, mock_urlopen) -> None:
        """An HTTPError from the server results in None."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=BytesIO(b""),
        )

        client = _make_client()
        result = client.fetch_treasury()
        assert result is None

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_url_error_returns_none(self, mock_urlopen) -> None:
        """A URLError (network issue) results in None."""
        mock_urlopen.side_effect = urllib.error.URLError("DNS resolution failed")

        client = _make_client()
        result = client.fetch_treasury()
        assert result is None

    @patch("trading.services.fmp_client.urllib.request.urlopen")
    def test_non_numeric_values_skipped(self, mock_urlopen) -> None:
        """Non-numeric yield values are silently skipped."""
        mock_urlopen.return_value = _mock_urlopen([
            {
                "date": "2026-02-14",
                "year10": 4.36,
                "year2": "N/A",
            }
        ])

        client = _make_client()
        result = client.fetch_treasury()

        assert result is not None
        assert result["year10"] == 4.36
        assert "year2" not in result


# ---------------------------------------------------------------------------
# symbol_for (static method)
# ---------------------------------------------------------------------------

class TestSymbolFor:

    def test_known_vix(self) -> None:
        """symbol_for('vix') returns the VIX index ticker."""
        assert FMPClient.symbol_for("vix") == "^VIX"

    def test_known_sp500(self) -> None:
        """symbol_for('sp500') returns the S&P 500 ticker."""
        assert FMPClient.symbol_for("sp500") == "^GSPC"

    def test_known_nasdaq(self) -> None:
        """symbol_for('nasdaq') returns the Nasdaq 100 ticker."""
        assert FMPClient.symbol_for("nasdaq") == "^NDX"

    def test_known_gold(self) -> None:
        """symbol_for('gold') returns the gold futures ticker."""
        assert FMPClient.symbol_for("gold") == "GCUSD"

    def test_unknown_returns_none(self) -> None:
        """An unrecognised indicator returns None."""
        assert FMPClient.symbol_for("bitcoin") is None

    def test_unknown_empty_string(self) -> None:
        """An empty string returns None."""
        assert FMPClient.symbol_for("") is None

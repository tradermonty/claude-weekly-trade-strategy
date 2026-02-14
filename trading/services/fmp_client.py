"""FMP (Financial Modeling Prep) API client for market data."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from trading.config import FMPConfig
from trading.core.constants import FMP_SYMBOLS

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10  # seconds


class FMPClient:
    """Client for the FMP REST API using urllib (no external dependencies)."""

    def __init__(self, config: FMPConfig) -> None:
        self._api_key = config.api_key
        self._base_url = config.base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def symbol_for(indicator: str) -> Optional[str]:
        """Return the FMP ticker for a named indicator, or *None*."""
        return FMP_SYMBOLS.get(indicator)

    # ------------------------------------------------------------------
    # Quote endpoint
    # ------------------------------------------------------------------

    def fetch_quotes(self, symbols: list[str]) -> Optional[dict[str, dict]]:
        """Fetch latest quotes for *symbols* (e.g. ``["^VIX", "^GSPC"]``).

        Returns a dict keyed by symbol, each value being the raw JSON
        object from FMP, or *None* on any HTTP / network error.
        """
        if not symbols:
            return {}

        joined = ",".join(symbols)
        url = f"{self._base_url}/quote/{joined}?apikey={self._api_key}"
        data = self._get_json(url)
        if data is None:
            return None

        result: dict[str, dict] = {}
        for item in data:
            sym = item.get("symbol")
            if sym:
                result[sym] = item
        return result

    # ------------------------------------------------------------------
    # Treasury endpoint
    # ------------------------------------------------------------------

    def fetch_treasury(self) -> Optional[dict[str, float]]:
        """Fetch US Treasury yields.

        Returns a dict like ``{"month1": 5.25, "year10": 4.35, ...}``
        or *None* on failure.
        """
        url = f"{self._base_url}/treasury?apikey={self._api_key}"
        data = self._get_json(url)
        if data is None:
            return None

        if not data:
            logger.warning("FMP treasury endpoint returned empty data")
            return None

        # The endpoint returns a list of daily snapshots; take the latest.
        latest = data[0] if isinstance(data, list) else data

        result: dict[str, float] = {}
        for key, value in latest.items():
            if key == "date":
                continue
            try:
                result[key] = float(value)
            except (TypeError, ValueError):
                pass
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Optional[list | dict]:
        """Issue a GET request and return parsed JSON, or *None*."""
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            logger.error("FMP HTTP %s for %s: %s", exc.code, url.split("?")[0], exc.reason)
            return None
        except urllib.error.URLError as exc:
            logger.error("FMP network error for %s: %s", url.split("?")[0], exc.reason)
            return None
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("FMP response error: %s", exc)
            return None

"""Historical data provider for backtesting with caching."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from trading.config import AlpacaConfig, FMPConfig
from trading.core.constants import ALLOWED_SYMBOLS, FMP_SYMBOLS
from trading.core.holidays import USMarketCalendar
from trading.data.models import MarketData

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # seconds
_calendar = USMarketCalendar()


class DataProvider:
    """Fetch and cache historical market data for backtesting.

    Phase A uses Alpaca ETF data only.
    Phase B also uses FMP for VIX, indices, and treasury data.
    """

    def __init__(
        self,
        alpaca_config: AlpacaConfig,
        fmp_config: Optional[FMPConfig] = None,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self._alpaca = alpaca_config
        self._fmp = fmp_config
        self._cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._etf_cache: dict[str, dict[date, float]] = {}  # symbol -> {date: close}
        self._etf_open_cache: dict[str, dict[date, float]] = {}  # symbol -> {date: open}
        self._fmp_cache: dict[str, dict[date, float]] = {}  # indicator -> {date: value}

    def load_etf_data(
        self,
        symbols: list[str],
        start: date,
        end: date,
    ) -> None:
        """Load ETF daily close and open prices into cache.

        Tries Alpaca first, falls back to FMP if Alpaca is unavailable.
        """
        for symbol in symbols:
            if symbol in self._etf_cache:
                continue
            cached_close = self._load_disk_cache(f"etf_{symbol}")
            cached_open = self._load_disk_cache(f"etf_{symbol}_open")
            if cached_close:
                self._etf_cache[symbol] = cached_close
                if cached_open:
                    self._etf_open_cache[symbol] = cached_open
                dates = sorted(cached_close.keys())
                if dates and dates[0] <= start and dates[-1] >= end:
                    if symbol in self._etf_open_cache:
                        logger.info("Using cached ETF data for %s", symbol)
                        continue

            # Try Alpaca first
            close_data: dict[date, float] = {}
            open_data: dict[date, float] = {}
            if self._alpaca.api_key and self._alpaca.secret_key:
                close_data, open_data = self._fetch_alpaca_bars(symbol, start, end)

            # Fallback to FMP for ETFs
            if not close_data and self._fmp and self._fmp.api_key:
                logger.info("Falling back to FMP for %s", symbol)
                close_data, open_data = self._fetch_fmp_historical(symbol, start, end)

            if close_data:
                self._etf_cache[symbol] = close_data
                self._save_disk_cache(f"etf_{symbol}", close_data)
            if open_data:
                self._etf_open_cache[symbol] = open_data
                self._save_disk_cache(f"etf_{symbol}_open", open_data)

    def load_fmp_data(
        self,
        start: date,
        end: date,
    ) -> None:
        """Load FMP historical data (VIX, indices) into cache."""
        if not self._fmp or not self._fmp.api_key:
            logger.warning("FMP config not available, Phase B data unavailable")
            return

        indicators = {
            "vix": "^VIX",
            "sp500": "^GSPC",
            "nasdaq": "^NDX",
            "dow": "^DJI",
        }
        for key, symbol in indicators.items():
            if key in self._fmp_cache:
                continue
            cached = self._load_disk_cache(f"fmp_{key}")
            if cached:
                self._fmp_cache[key] = cached
                dates = sorted(cached.keys())
                if dates and dates[0] <= start and dates[-1] >= end:
                    logger.info("Using cached FMP data for %s", key)
                    continue

            close_data, _open_data = self._fetch_fmp_historical(symbol, start, end)
            if close_data:
                self._fmp_cache[key] = close_data
                self._save_disk_cache(f"fmp_{key}", close_data)

    def get_etf_prices(self, d: date) -> dict[str, float]:
        """Get ETF close prices for a given date.

        Uses forward-fill for missing dates (up to 3 days).
        """
        prices: dict[str, float] = {}
        for symbol, data in self._etf_cache.items():
            price = self._get_with_ffill(data, d)
            if price is not None:
                prices[symbol] = price
        return prices

    def get_etf_open_prices(self, d: date) -> dict[str, float]:
        """Get ETF open prices for a given date.

        Uses forward-fill for missing dates (up to 3 days).
        Returns empty dict if no open price data is available.
        """
        prices: dict[str, float] = {}
        for symbol, data in self._etf_open_cache.items():
            price = self._get_with_ffill(data, d)
            if price is not None:
                prices[symbol] = price
        return prices

    def get_market_data(self, d: date) -> MarketData:
        """Get market data (VIX, indices) for a given date (Phase B)."""
        etf_prices = self.get_etf_prices(d)

        vix = self._get_fmp_value("vix", d)
        sp500 = self._get_fmp_value("sp500", d)
        nasdaq = self._get_fmp_value("nasdaq", d)
        dow = self._get_fmp_value("dow", d)

        return MarketData(
            timestamp=datetime.combine(d, datetime.min.time()),
            vix=vix,
            sp500=sp500,
            nasdaq=nasdaq,
            dow=dow,
            etf_prices=etf_prices,
        )

    def get_trading_days(self, start: date, end: date) -> list[date]:
        """Return list of trading days between start and end (inclusive)."""
        days: list[date] = []
        d = start
        while d <= end:
            if d.weekday() < 5 and not _calendar.is_market_holiday(d):
                days.append(d)
            d += timedelta(days=1)
        return days

    def has_etf_data(self, d: date) -> bool:
        """Check if we have ETF data for a given date."""
        return any(d in data for data in self._etf_cache.values())

    def validate_data_alignment(self, start: date, end: date) -> list[str]:
        """Verify ETF and FMP data are aligned on the same trading days.

        Returns list of warning messages.
        """
        warnings: list[str] = []
        trading_days = self.get_trading_days(start, end)

        for d in trading_days:
            etf_count = sum(1 for data in self._etf_cache.values() if d in data)
            if etf_count == 0:
                # Check if forward-fill would cover it
                has_ffill = any(
                    self._get_with_ffill(data, d) is not None
                    for data in self._etf_cache.values()
                )
                if not has_ffill:
                    warnings.append(f"No ETF data for {d}")

        return warnings

    # --- Private: Alpaca ---

    def _fetch_alpaca_bars(
        self, symbol: str, start: date, end: date,
    ) -> tuple[dict[date, float], dict[date, float]]:
        """Fetch daily bars from Alpaca. Returns (close_prices, open_prices)."""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame

            client = StockHistoricalDataClient(
                api_key=self._alpaca.api_key,
                secret_key=self._alpaca.secret_key,
            )
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.combine(start, datetime.min.time()),
                end=datetime.combine(end, datetime.min.time()),
            )
            bars = client.get_stock_bars(request)
            close_data: dict[date, float] = {}
            open_data: dict[date, float] = {}
            for bar in bars[symbol]:
                bar_date = bar.timestamp.date()
                close_data[bar_date] = bar.close
                open_data[bar_date] = bar.open

            logger.info("Fetched %d bars for %s from Alpaca", len(close_data), symbol)
            return close_data, open_data

        except Exception as e:
            logger.error("Failed to fetch Alpaca bars for %s: %s", symbol, e)
            return {}, {}

    # --- Private: FMP ---

    def _fetch_fmp_historical(
        self, symbol: str, start: date, end: date,
    ) -> tuple[dict[date, float], dict[date, float]]:
        """Fetch historical daily data from FMP. Returns (close_prices, open_prices)."""
        if not self._fmp:
            return {}, {}

        try:
            encoded = urllib.parse.quote(symbol, safe="")
            url = (
                f"{self._fmp.base_url.rstrip('/')}/historical-price-full/{encoded}"
                f"?from={start.isoformat()}&to={end.isoformat()}"
                f"&apikey={self._fmp.api_key}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "trading-backtest"})
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())

            historical = data.get("historical", [])
            close_data: dict[date, float] = {}
            open_data: dict[date, float] = {}
            for item in historical:
                d = date.fromisoformat(item["date"])
                close_data[d] = item["close"]
                if "open" in item:
                    open_data[d] = item["open"]

            logger.info("Fetched %d data points for %s from FMP", len(close_data), symbol)
            return close_data, open_data

        except Exception as e:
            logger.error("Failed to fetch FMP data for %s: %s", symbol, e)
            return {}, {}

    # --- Private: Cache ---

    def _get_with_ffill(
        self, data: dict[date, float], d: date, max_gap: int = 3,
    ) -> Optional[float]:
        """Get value for date with forward-fill up to max_gap days."""
        if d in data:
            return data[d]
        for i in range(1, max_gap + 1):
            prev = d - timedelta(days=i)
            if prev in data:
                return data[prev]
        return None

    def _get_fmp_value(self, key: str, d: date) -> Optional[float]:
        """Get FMP value with forward-fill."""
        if key not in self._fmp_cache:
            return None
        return self._get_with_ffill(self._fmp_cache[key], d)

    def _cache_path(self, name: str) -> Optional[Path]:
        if not self._cache_dir:
            return None
        return self._cache_dir / f"{name}.json"

    def _load_disk_cache(self, name: str) -> Optional[dict[date, float]]:
        """Load cached data from disk."""
        path = self._cache_path(name)
        if not path or not path.exists():
            return None
        try:
            raw = json.loads(path.read_text())
            return {date.fromisoformat(k): v for k, v in raw.items()}
        except Exception as e:
            logger.warning("Cache load failed for %s: %s", name, e)
            return None

    def _save_disk_cache(self, name: str, data: dict[date, float]) -> None:
        """Save data to disk cache."""
        path = self._cache_path(name)
        if not path:
            return
        try:
            raw = {k.isoformat(): v for k, v in sorted(data.items())}
            path.write_text(json.dumps(raw, indent=2))
        except Exception as e:
            logger.warning("Cache save failed for %s: %s", name, e)

    # --- Injection for testing ---

    def inject_etf_data(self, symbol: str, data: dict[date, float]) -> None:
        """Inject ETF close data directly (for testing)."""
        self._etf_cache[symbol] = data

    def inject_etf_open_data(self, symbol: str, data: dict[date, float]) -> None:
        """Inject ETF open data directly (for testing)."""
        self._etf_open_cache[symbol] = data

    def inject_fmp_data(self, key: str, data: dict[date, float]) -> None:
        """Inject FMP data directly (for testing)."""
        self._fmp_cache[key] = data

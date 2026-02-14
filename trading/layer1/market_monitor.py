"""Market data fetcher with validation and API failure tracking."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from trading.config import TradingConfig
from trading.core.constants import FMP_SYMBOLS, INDEX_ETF_PAIRS
from trading.data.database import Database
from trading.data.models import MarketData, Portfolio
from trading.services.fmp_client import FMPClient
from trading.services.alpaca_client import AlpacaClient
from trading.services.data_validator import MarketDataValidator

logger = logging.getLogger(__name__)


class MarketMonitor:
    """Fetch and validate market data from FMP and Alpaca."""

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db
        self._fmp = FMPClient(config.fmp)
        self._alpaca = AlpacaClient(config.alpaca)
        self._validator = MarketDataValidator(config)

    def fetch_market_data(self) -> MarketData:
        """Fetch market data from FMP (indices/commodities) and Alpaca (ETFs).

        On API failure: increment failure counter, fall back to previous values.
        On success: reset failure counter to 0.
        """
        now = datetime.now(timezone.utc)
        md = MarketData(timestamp=now)

        # --- FMP: indices, VIX, commodities ---
        fmp_ok = self._fetch_fmp_data(md)

        # --- FMP: US 10Y yield ---
        if fmp_ok:
            self._fetch_treasury(md)

        # --- Alpaca: ETF prices ---
        alpaca_ok = self._fetch_alpaca_etf_prices(md)

        # --- Track API failures (weighted: both fail = +2) ---
        if fmp_ok and alpaca_ok:
            self._db.set_state("consecutive_api_failures", "0")
        else:
            prev = int(self._db.get_state("consecutive_api_failures", "0"))
            increment = (0 if fmp_ok else 1) + (0 if alpaca_ok else 1)
            new_count = prev + increment
            self._db.set_state("consecutive_api_failures", str(new_count))
            logger.warning(
                "API failure detected: FMP=%s Alpaca=%s (increment=+%d, consecutive=%d)",
                "OK" if fmp_ok else "FAIL",
                "OK" if alpaca_ok else "FAIL",
                increment, new_count,
            )

        # --- Validate ranges ---
        for attr in ("vix", "us10y", "sp500", "nasdaq", "dow", "gold", "oil", "copper"):
            val = getattr(md, attr, None)
            if val is not None and not self._validator.validate(attr, val):
                logger.warning("Value out of range: %s=%.4f, using previous", attr, val)
                prev = self._db.get_previous_market_state(attr)
                if prev is not None:
                    setattr(md, attr, prev)

        # --- Persist market state ---
        self._db.save_market_state(
            timestamp=now.isoformat(),
            vix=md.vix,
            us10y=md.us10y,
            sp500=md.sp500,
            nasdaq=md.nasdaq,
            dow=md.dow,
            gold=md.gold,
            oil=md.oil,
            copper=md.copper,
        )

        return md

    def fetch_portfolio(self) -> Optional[Portfolio]:
        """Get current account and positions from Alpaca."""
        return self._alpaca.get_portfolio()

    def calibrate_index_etf_ratios(self, market_data: MarketData) -> dict[str, float]:
        """Calibrate index-to-ETF conversion ratios and save to DB.

        For each (ETF, INDEX) pair in INDEX_ETF_PAIRS, compute:
          ratio = index_price / etf_price

        Returns a dict like {"SPY": 10.5, "QQQ": 78.3, "DIA": 88.1}.
        """
        today = date.today()
        ratios: dict[str, float] = {}

        for etf_symbol, index_symbol in INDEX_ETF_PAIRS:
            index_price = self._get_index_price(index_symbol, market_data)
            etf_price = market_data.etf_prices.get(etf_symbol)

            if index_price is None or etf_price is None or etf_price == 0:
                # Try cached calibration
                cached = self._db.get_calibration(today, etf_symbol)
                if cached is not None:
                    ratios[etf_symbol] = cached
                    logger.warning(
                        "Using cached calibration for %s: %.4f", etf_symbol, cached
                    )
                continue

            ratio = index_price / etf_price
            ratios[etf_symbol] = ratio
            self._db.save_calibration(today, etf_symbol, index_symbol, ratio)
            logger.info(
                "Calibrated %s/%s ratio=%.4f (index=%.2f etf=%.2f)",
                etf_symbol, index_symbol, ratio, index_price, etf_price,
            )

        return ratios

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_fmp_data(self, md: MarketData) -> bool:
        """Fetch FMP quotes and populate MarketData. Return True on success."""
        symbols = list(FMP_SYMBOLS.values())
        quotes = self._fmp.fetch_quotes(symbols)
        if quotes is None:
            logger.error("FMP quote fetch failed, using previous values")
            self._fill_from_previous(md)
            return False

        # Map FMP symbols back to MarketData fields
        field_map = {
            FMP_SYMBOLS["vix"]: "vix",
            FMP_SYMBOLS["sp500"]: "sp500",
            FMP_SYMBOLS["nasdaq"]: "nasdaq",
            FMP_SYMBOLS["dow"]: "dow",
            FMP_SYMBOLS["gold"]: "gold",
            FMP_SYMBOLS["oil"]: "oil",
            FMP_SYMBOLS["copper"]: "copper",
        }

        for fmp_sym, attr in field_map.items():
            if fmp_sym in quotes:
                price = quotes[fmp_sym].get("price")
                if price is not None:
                    setattr(md, attr, float(price))

        return True

    def _fetch_treasury(self, md: MarketData) -> None:
        """Fetch 10Y yield from FMP treasury endpoint."""
        treasury = self._fmp.fetch_treasury()
        if treasury is None:
            prev = self._db.get_previous_market_state("us10y")
            if prev is not None:
                md.us10y = prev
            return

        # FMP treasury keys: "year10", "year2", etc.
        if "year10" in treasury:
            md.us10y = treasury["year10"]

    def _fetch_alpaca_etf_prices(self, md: MarketData) -> bool:
        """Fetch ETF latest prices from Alpaca. Return True on success."""
        from trading.core.constants import ALLOWED_SYMBOLS
        try:
            prices = self._alpaca.get_quotes(list(ALLOWED_SYMBOLS))
            if prices:
                md.etf_prices = prices
                return True
            logger.error("Alpaca returned empty price data")
            return False
        except Exception:
            logger.exception("Alpaca ETF price fetch failed")
            return False

    def _fill_from_previous(self, md: MarketData) -> None:
        """Fill MarketData from last known DB values as fallback."""
        for attr in ("vix", "us10y", "sp500", "nasdaq", "dow", "gold", "oil", "copper"):
            prev = self._db.get_previous_market_state(attr)
            if prev is not None:
                setattr(md, attr, prev)

    @staticmethod
    def _get_index_price(index_symbol: str, md: MarketData) -> Optional[float]:
        """Resolve an FMP index symbol to a MarketData value."""
        mapping = {
            "^GSPC": md.sp500,
            "^NDX": md.nasdaq,
            "^DJI": md.dow,
        }
        return mapping.get(index_symbol)

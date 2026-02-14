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

        Uses MarketDataValidator.resolve_conflict() to merge data from
        multiple sources, and is_fresh() to check fallback data staleness.
        On API failure: increment failure counter, fall back to previous values.
        On success: reset failure counter to 0.
        """
        now = datetime.now(timezone.utc)

        # --- Fetch raw data as dicts ---
        fmp_data = self._fetch_fmp_raw()
        if fmp_data is not None:
            self._fetch_treasury_into(fmp_data)

        alpaca_data = self._fetch_alpaca_raw()

        # --- Get previous state for fallback ---
        previous = self._get_previous_as_dict()

        # --- Merge using resolve_conflict ---
        merged = self._validator.resolve_conflict(fmp_data, alpaca_data, previous)

        # --- Build MarketData from merged dict ---
        md = MarketData(timestamp=now)
        md.vix = merged.get("vix")
        md.us10y = merged.get("us10y")
        md.sp500 = merged.get("sp500")
        md.nasdaq = merged.get("nasdaq")
        md.dow = merged.get("dow")
        md.gold = merged.get("gold")
        md.oil = merged.get("oil")
        md.copper = merged.get("copper")
        if alpaca_data is not None:
            md.etf_prices = alpaca_data.get("_etf_prices", {})
        elif previous.get("_etf_prices"):
            md.etf_prices = previous["_etf_prices"]

        # --- Freshness check on fallback data ---
        fmp_ok = fmp_data is not None
        alpaca_ok = alpaca_data is not None

        # Check staleness whenever ANY source fails and fallback is used,
        # not just when both fail (_stale=True).
        if (not fmp_ok or not alpaca_ok) and previous:
            prev_ts = self._db.get_previous_market_state_timestamp()
            if prev_ts is not None:
                if not fmp_ok and not self._validator.is_fresh("fmp_quote", prev_ts):
                    logger.error(
                        "FMP fallback data is STALE (age exceeds %ds)",
                        self._config.fmp_quote_max_staleness,
                    )
                if not alpaca_ok and not self._validator.is_fresh("alpaca_quote", prev_ts):
                    logger.error(
                        "Alpaca fallback data is STALE (age exceeds %ds)",
                        self._config.alpaca_quote_max_staleness,
                    )

        # --- Track API failures in DB (weighted: both fail = +2) ---
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
                prev_val = self._db.get_previous_market_state(attr)
                if prev_val is not None:
                    setattr(md, attr, prev_val)

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

    def _fetch_fmp_raw(self) -> Optional[dict]:
        """Fetch FMP quotes and return as a flat dict, or None on failure."""
        symbols = list(FMP_SYMBOLS.values())
        quotes = self._fmp.fetch_quotes(symbols)
        if quotes is None:
            logger.error("FMP quote fetch failed")
            return None

        field_map = {
            FMP_SYMBOLS["vix"]: "vix",
            FMP_SYMBOLS["sp500"]: "sp500",
            FMP_SYMBOLS["nasdaq"]: "nasdaq",
            FMP_SYMBOLS["dow"]: "dow",
            FMP_SYMBOLS["gold"]: "gold",
            FMP_SYMBOLS["oil"]: "oil",
            FMP_SYMBOLS["copper"]: "copper",
        }

        data: dict = {}
        for fmp_sym, attr in field_map.items():
            if fmp_sym in quotes:
                price = quotes[fmp_sym].get("price")
                if price is not None:
                    data[attr] = float(price)
        return data

    def _fetch_treasury_into(self, data: dict) -> None:
        """Fetch 10Y yield from FMP and add to data dict."""
        treasury = self._fmp.fetch_treasury()
        if treasury is None:
            return
        if "year10" in treasury:
            data["us10y"] = treasury["year10"]

    def _fetch_alpaca_raw(self) -> Optional[dict]:
        """Fetch ETF prices from Alpaca and return as a dict, or None on failure."""
        from trading.core.constants import ALLOWED_SYMBOLS
        try:
            prices = self._alpaca.get_quotes(list(ALLOWED_SYMBOLS))
            if prices:
                return {"_etf_prices": prices}
            logger.error("Alpaca returned empty price data")
            return None
        except Exception:
            logger.exception("Alpaca ETF price fetch failed")
            return None

    def _get_previous_as_dict(self) -> dict:
        """Build a dict of previous market state values from DB."""
        previous: dict = {}
        for attr in ("vix", "us10y", "sp500", "nasdaq", "dow", "gold", "oil", "copper"):
            val = self._db.get_previous_market_state(attr)
            if val is not None:
                previous[attr] = val
        return previous

    @staticmethod
    def _get_index_price(index_symbol: str, md: MarketData) -> Optional[float]:
        """Resolve an FMP index symbol to a MarketData value."""
        mapping = {
            "^GSPC": md.sp500,
            "^NDX": md.nasdaq,
            "^DJI": md.dow,
        }
        return mapping.get(index_symbol)

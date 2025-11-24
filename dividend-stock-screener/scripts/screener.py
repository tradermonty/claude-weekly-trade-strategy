"""
Dividend stock screener module.

Provides screening functions for:
1. Dividend Growth Pullback: High dividend growth stocks with RSI <= 40
2. Value Dividend: Value stocks with attractive yields and RSI <= 40
"""
import os
import time
import requests
from typing import Optional


# Screening thresholds
RSI_OVERSOLD_THRESHOLD = 40
DIVIDEND_GROWTH_MIN_YIELD = 1.5
DIVIDEND_GROWTH_MIN_CAGR = 12.0
DIVIDEND_GROWTH_MIN_MARKET_CAP = 2_000_000_000
VALUE_DIVIDEND_MIN_YIELD = 3.0
VALUE_DIVIDEND_MAX_PE = 20
VALUE_DIVIDEND_MAX_PB = 2
VALUE_DIVIDEND_MIN_DIV_GROWTH = 5.0


def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """
    Calculate RSI (Relative Strength Index) from price data.

    Parameters
    ----------
    prices : list[float]
        List of closing prices (oldest to newest)
    period : int
        RSI period (default 14)

    Returns
    -------
    Optional[float]
        RSI value (0-100) or None if insufficient data
    """
    if len(prices) < period + 1:
        return None

    # Calculate price changes
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Separate gains and losses
    gains = [max(0, change) for change in changes]
    losses = [abs(min(0, change)) for change in changes]

    # Calculate initial average gain/loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Smooth using Wilder's method for remaining periods
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    # Calculate RSI
    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def is_oversold(rsi: float) -> bool:
    """
    Check if RSI indicates oversold condition.

    Parameters
    ----------
    rsi : float
        RSI value

    Returns
    -------
    bool
        True if RSI <= 40 (oversold threshold)
    """
    return rsi <= RSI_OVERSOLD_THRESHOLD


def qualifies_dividend_growth_pullback(stock: dict) -> bool:
    """
    Check if stock qualifies for dividend growth pullback screening.

    Criteria:
    - Dividend CAGR (3Y) >= 12%
    - Dividend Yield >= 1.5%
    - RSI <= 40
    - Market Cap >= $2B
    - Positive revenue/EPS growth
    - D/E < 2.0

    Parameters
    ----------
    stock : dict
        Stock data dictionary

    Returns
    -------
    bool
        True if stock meets all criteria
    """
    # Check dividend growth
    if stock.get('dividend_cagr_3y', 0) < DIVIDEND_GROWTH_MIN_CAGR:
        return False

    # Check dividend yield
    if stock.get('dividend_yield', 0) < DIVIDEND_GROWTH_MIN_YIELD:
        return False

    # Check RSI (oversold condition)
    rsi = stock.get('rsi')
    if rsi is None or rsi > RSI_OVERSOLD_THRESHOLD:
        return False

    # Check market cap
    if stock.get('market_cap', 0) < DIVIDEND_GROWTH_MIN_MARKET_CAP:
        return False

    # Check growth trends
    if not stock.get('revenue_growth_positive', False):
        return False
    if not stock.get('eps_growth_positive', False):
        return False

    # Check debt level
    if stock.get('debt_to_equity', float('inf')) >= 2.0:
        return False

    return True


def qualifies_value_dividend(stock: dict) -> bool:
    """
    Check if stock qualifies for value dividend screening.

    Criteria:
    - P/E <= 20
    - P/B <= 2
    - Dividend Yield >= 3%
    - RSI <= 40
    - Dividend Growth (3Y) >= 5%
    - Positive revenue/EPS growth

    Parameters
    ----------
    stock : dict
        Stock data dictionary

    Returns
    -------
    bool
        True if stock meets all criteria
    """
    # Check P/E ratio
    pe = stock.get('pe_ratio')
    if pe is None or pe > VALUE_DIVIDEND_MAX_PE or pe <= 0:
        return False

    # Check P/B ratio
    pb = stock.get('pb_ratio')
    if pb is None or pb > VALUE_DIVIDEND_MAX_PB or pb <= 0:
        return False

    # Check dividend yield
    if stock.get('dividend_yield', 0) < VALUE_DIVIDEND_MIN_YIELD:
        return False

    # Check RSI (oversold condition)
    rsi = stock.get('rsi')
    if rsi is None or rsi > RSI_OVERSOLD_THRESHOLD:
        return False

    # Check dividend growth
    if stock.get('dividend_cagr_3y', 0) < VALUE_DIVIDEND_MIN_DIV_GROWTH:
        return False

    # Check growth trends
    if not stock.get('revenue_growth_positive', False):
        return False
    if not stock.get('eps_growth_positive', False):
        return False

    return True


def fetch_dividend_growth_candidates() -> list[dict]:
    """
    Fetch dividend growth candidates from FINVIZ and FMP APIs.

    Returns
    -------
    list[dict]
        List of stock dictionaries with all required metrics
    """
    # This will be implemented with actual API calls
    # For now, return empty list (will be mocked in tests)
    return []


def fetch_value_dividend_candidates() -> list[dict]:
    """
    Fetch value dividend candidates from FINVIZ and FMP APIs.

    Returns
    -------
    list[dict]
        List of stock dictionaries with all required metrics
    """
    # This will be implemented with actual API calls
    # For now, return empty list (will be mocked in tests)
    return []


def run_screening() -> dict:
    """
    Run both screening strategies and return results.

    Returns
    -------
    dict
        Dictionary with 'dividend_growth_pullback' and 'value_dividend' keys
    """
    # Fetch candidates for each strategy
    growth_candidates = fetch_dividend_growth_candidates()
    value_candidates = fetch_value_dividend_candidates()

    # Filter candidates that meet all criteria
    growth_qualified = [
        stock for stock in growth_candidates
        if qualifies_dividend_growth_pullback(stock)
    ]

    value_qualified = [
        stock for stock in value_candidates
        if qualifies_value_dividend(stock)
    ]

    return {
        'dividend_growth_pullback': growth_qualified,
        'value_dividend': value_qualified,
    }

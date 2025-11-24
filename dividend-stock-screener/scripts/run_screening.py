#!/usr/bin/env python3
"""
Main screening orchestrator for dividend stock screener.

Runs both screening strategies and generates HTML report:
1. Dividend Growth Pullback Screening
2. Value Dividend Screening

Usage:
    python3 scripts/run_screening.py
"""
import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from screener import (
    calculate_rsi,
    qualifies_dividend_growth_pullback,
    qualifies_value_dividend,
)
from report_generator import generate_html_report, save_report

# Import API clients from existing skill scripts
skills_path = os.path.join(
    os.path.dirname(__file__), '..', '.claude', 'skills',
    'dividend-growth-pullback-screener', 'scripts'
)
sys.path.insert(0, skills_path)

try:
    from screen_dividend_growth_rsi import FMPClient, FINVIZClient, RSICalculator, StockAnalyzer
except ImportError as e:
    print(f"Warning: Could not import from skill scripts: {e}")
    print("Using simplified implementation.")
    FMPClient = None
    FINVIZClient = None


def fetch_dividend_growth_candidates(fmp_key: str, finviz_key: str = None) -> list:
    """
    Fetch dividend growth candidates using FINVIZ + FMP APIs.

    Returns list of stocks with all required metrics for screening.
    """
    if FMPClient is None:
        print("API clients not available. Returning empty results.")
        return []

    client = FMPClient(fmp_key)
    analyzer = StockAnalyzer()
    rsi_calc = RSICalculator()

    candidates = []

    # Use FINVIZ pre-screening if available
    finviz_symbols = None
    if finviz_key:
        try:
            finviz_client = FINVIZClient(finviz_key)
            finviz_symbols = finviz_client.screen_stocks()
            print(f"FINVIZ pre-screening found {len(finviz_symbols)} symbols")
        except Exception as e:
            print(f"FINVIZ pre-screening failed: {e}")

    # Get candidate list
    if finviz_symbols:
        print("Fetching quote data for FINVIZ candidates...")
        stock_list = []
        for symbol in finviz_symbols:
            stock_data = client.get_quote_with_profile(symbol)
            if stock_data:
                stock_list.append(stock_data)
            if client.rate_limit_reached:
                break
    else:
        print("Using FMP screener for initial candidates...")
        stock_list = client.screen_stocks(min_market_cap=2_000_000_000)

    print(f"Analyzing {len(stock_list)} candidates for dividend growth...")

    for stock in stock_list:
        if client.rate_limit_reached:
            print("API rate limit reached. Stopping analysis.")
            break

        symbol = stock.get('symbol', '')
        current_price = stock.get('price', 0)

        if current_price <= 0:
            continue

        # Get dividend history
        dividend_history = client.get_dividend_history(symbol)
        if not dividend_history:
            continue

        # Analyze dividend growth
        div_cagr, div_consistent, annual_dividend = analyzer.analyze_dividend_growth(dividend_history)
        if not div_cagr or div_cagr < 12.0:
            continue

        if not annual_dividend:
            continue

        # Calculate yield
        dividend_yield = (annual_dividend / current_price) * 100
        if dividend_yield < 1.5:
            continue

        # Get historical prices for RSI
        historical_prices = client.get_historical_prices(symbol, days=30)
        if not historical_prices or len(historical_prices) < 20:
            continue

        prices = [p['close'] for p in reversed(historical_prices)]
        rsi = rsi_calc.calculate_rsi(prices, period=14)

        if rsi is None or rsi > 40:
            continue

        # Get fundamental data
        income_stmts = client.get_income_statement(symbol, limit=5)
        balance_sheet = client.get_balance_sheet(symbol, limit=5)
        key_metrics = client.get_key_metrics(symbol, limit=1)

        # Analyze growth
        growth_metrics = analyzer.analyze_growth_metrics(income_stmts or [])
        revenue_cagr = growth_metrics.get('revenue_cagr_3y')
        eps_cagr = growth_metrics.get('eps_cagr_3y')

        # Analyze financial health
        health_metrics = analyzer.analyze_financial_health(balance_sheet or [])

        latest_metrics = key_metrics[0] if key_metrics else {}

        candidate = {
            'symbol': symbol,
            'company_name': stock.get('companyName', stock.get('name', '')),
            'sector': stock.get('sector', 'Unknown'),
            'market_cap': stock.get('marketCap', 0),
            'price': current_price,
            'dividend_yield': round(dividend_yield, 2),
            'dividend_cagr_3y': div_cagr,
            'dividend_consistent': div_consistent,
            'rsi': rsi,
            'pe_ratio': latest_metrics.get('peRatio', 0),
            'pb_ratio': latest_metrics.get('pbRatio', 0),
            'revenue_cagr_3y': revenue_cagr,
            'eps_cagr_3y': eps_cagr,
            'revenue_growth_positive': revenue_cagr is None or revenue_cagr >= 0,
            'eps_growth_positive': eps_cagr is None or eps_cagr >= 0,
            'debt_to_equity': health_metrics.get('debt_to_equity'),
            'current_ratio': health_metrics.get('current_ratio'),
            'financially_healthy': health_metrics.get('financially_healthy', False),
        }

        if qualifies_dividend_growth_pullback(candidate):
            candidates.append(candidate)
            print(f"  ✅ {symbol}: Yield={dividend_yield:.1f}%, CAGR={div_cagr:.1f}%, RSI={rsi:.0f}")

    return candidates


def fetch_value_dividend_candidates(fmp_key: str, finviz_key: str = None) -> list:
    """
    Fetch value dividend candidates using FINVIZ + FMP APIs.

    Returns list of stocks with all required metrics for screening.
    """
    if FMPClient is None:
        print("API clients not available. Returning empty results.")
        return []

    client = FMPClient(fmp_key)
    analyzer = StockAnalyzer()
    rsi_calc = RSICalculator()

    candidates = []

    # Use FINVIZ for value dividend pre-screening
    finviz_symbols = None
    if finviz_key:
        try:
            finviz_client = FINVIZClient(finviz_key)
            # Modify filters for value criteria
            finviz_client.BASE_URL = "https://elite.finviz.com/export.ashx"
            # Value criteria: P/E < 20, P/B < 2, Div yield > 3%, RSI < 40
            params = {
                'v': '151',
                'f': 'cap_midover,fa_div_o3,fa_pe_u20,fa_pb_u2,ta_rsi_os40,geo_usa',
                'ft': '4',
                'auth': finviz_key
            }
            import requests
            import csv
            import io
            response = requests.get(finviz_client.BASE_URL, params=params, timeout=30)
            if response.status_code == 200:
                csv_content = response.content.decode('utf-8')
                reader = csv.DictReader(io.StringIO(csv_content))
                finviz_symbols = set()
                for row in reader:
                    ticker = row.get('Ticker', '').strip()
                    if ticker:
                        finviz_symbols.add(ticker)
                print(f"FINVIZ value screening found {len(finviz_symbols)} symbols")
        except Exception as e:
            print(f"FINVIZ value screening failed: {e}")

    # Get candidate list
    if finviz_symbols:
        print("Fetching quote data for FINVIZ value candidates...")
        stock_list = []
        for symbol in finviz_symbols:
            stock_data = client.get_quote_with_profile(symbol)
            if stock_data:
                stock_list.append(stock_data)
            if client.rate_limit_reached:
                break
    else:
        print("Using FMP screener for value candidates...")
        stock_list = client.screen_stocks(min_market_cap=2_000_000_000)

    print(f"Analyzing {len(stock_list)} candidates for value dividend...")

    for stock in stock_list:
        if client.rate_limit_reached:
            print("API rate limit reached. Stopping analysis.")
            break

        symbol = stock.get('symbol', '')
        current_price = stock.get('price', 0)

        if current_price <= 0:
            continue

        # Get dividend history
        dividend_history = client.get_dividend_history(symbol)
        if not dividend_history:
            continue

        # Analyze dividend growth
        div_cagr, div_consistent, annual_dividend = analyzer.analyze_dividend_growth(dividend_history)
        if not div_cagr or div_cagr < 5.0:  # Lower threshold for value
            continue

        if not annual_dividend:
            continue

        # Calculate yield
        dividend_yield = (annual_dividend / current_price) * 100
        if dividend_yield < 3.0:
            continue

        # Get historical prices for RSI
        historical_prices = client.get_historical_prices(symbol, days=30)
        if not historical_prices or len(historical_prices) < 20:
            continue

        prices = [p['close'] for p in reversed(historical_prices)]
        rsi = rsi_calc.calculate_rsi(prices, period=14)

        if rsi is None or rsi > 40:
            continue

        # Get fundamental data
        income_stmts = client.get_income_statement(symbol, limit=5)
        balance_sheet = client.get_balance_sheet(symbol, limit=5)
        key_metrics = client.get_key_metrics(symbol, limit=1)

        latest_metrics = key_metrics[0] if key_metrics else {}

        pe_ratio = latest_metrics.get('peRatio', 0)
        pb_ratio = latest_metrics.get('pbRatio', 0)

        # Check value criteria
        if pe_ratio is None or pe_ratio <= 0 or pe_ratio > 20:
            continue
        if pb_ratio is None or pb_ratio <= 0 or pb_ratio > 2:
            continue

        # Analyze growth
        growth_metrics = analyzer.analyze_growth_metrics(income_stmts or [])
        revenue_cagr = growth_metrics.get('revenue_cagr_3y')
        eps_cagr = growth_metrics.get('eps_cagr_3y')

        # Analyze financial health
        health_metrics = analyzer.analyze_financial_health(balance_sheet or [])

        candidate = {
            'symbol': symbol,
            'company_name': stock.get('companyName', stock.get('name', '')),
            'sector': stock.get('sector', 'Unknown'),
            'market_cap': stock.get('marketCap', 0),
            'price': current_price,
            'dividend_yield': round(dividend_yield, 2),
            'dividend_cagr_3y': div_cagr,
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'rsi': rsi,
            'revenue_cagr_3y': revenue_cagr,
            'eps_cagr_3y': eps_cagr,
            'revenue_growth_positive': revenue_cagr is None or revenue_cagr >= 0,
            'eps_growth_positive': eps_cagr is None or eps_cagr >= 0,
            'debt_to_equity': health_metrics.get('debt_to_equity'),
            'current_ratio': health_metrics.get('current_ratio'),
        }

        if qualifies_value_dividend(candidate):
            candidates.append(candidate)
            print(f"  ✅ {symbol}: Yield={dividend_yield:.1f}%, P/E={pe_ratio:.1f}, RSI={rsi:.0f}")

    return candidates


def main():
    """Main function to run screening and generate report."""
    # Get API keys from environment
    fmp_key = os.environ.get('FMP_API_KEY')
    finviz_key = os.environ.get('FINVIZ_API_KEY')

    if not fmp_key:
        print("ERROR: FMP_API_KEY environment variable not set")
        sys.exit(1)

    print("=" * 80)
    print("DIVIDEND STOCK SCREENER - Daily Report")
    print("=" * 80)
    print()

    # Run dividend growth pullback screening
    print("\n--- Section 1: Dividend Growth Pullback Screening ---\n")
    growth_candidates = fetch_dividend_growth_candidates(fmp_key, finviz_key)
    print(f"\nFound {len(growth_candidates)} dividend growth pullback candidates")

    # Run value dividend screening
    print("\n--- Section 2: Value Dividend Screening ---\n")
    value_candidates = fetch_value_dividend_candidates(fmp_key, finviz_key)
    print(f"\nFound {len(value_candidates)} value dividend candidates")

    # Generate HTML report
    print("\n--- Generating HTML Report ---\n")
    screening_results = {
        'dividend_growth_pullback': growth_candidates,
        'value_dividend': value_candidates,
    }

    html_report = generate_html_report(screening_results)

    # Save report
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    today = date.today().strftime('%Y-%m-%d')
    report_path = save_report(html_report, today, reports_dir)

    print(f"Report saved to: {report_path}")
    print()
    print("=" * 80)
    print("Screening Complete!")
    print(f"  Dividend Growth Pullback: {len(growth_candidates)} stocks")
    print(f"  Value Dividend: {len(value_candidates)} stocks")
    print("=" * 80)

    return report_path


if __name__ == '__main__':
    main()

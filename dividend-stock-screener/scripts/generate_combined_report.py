#!/usr/bin/env python3
"""
Generate combined HTML report from skill screening results.

Reads JSON output from both skills and generates a unified HTML report.
"""
import os
import sys
import json
import glob
from datetime import date
from typing import Optional, List

sys.path.insert(0, os.path.dirname(__file__))
from report_generator import generate_html_report, save_report


def find_latest_json(pattern: str, search_dirs: List[str]) -> Optional[str]:
    """Find the most recent JSON file matching pattern in search directories."""
    all_files = []
    for directory in search_dirs:
        files = glob.glob(os.path.join(directory, pattern))
        all_files.extend(files)

    if not all_files:
        return None

    # Sort by modification time, newest first
    all_files.sort(key=os.path.getmtime, reverse=True)
    return all_files[0]


def load_dividend_growth_results(search_dirs: List[str]) -> List[dict]:
    """Load results from dividend-growth-pullback-screener skill."""
    json_path = find_latest_json('dividend_growth_pullback_results_*.json', search_dirs)

    if not json_path:
        print("Warning: No dividend growth pullback results found")
        return []

    print(f"Loading dividend growth results from: {json_path}")
    with open(json_path, 'r') as f:
        data = json.load(f)

    stocks = data.get('stocks', [])

    # Transform to common format - include all fields needed for report
    results = []
    for stock in stocks:
        results.append({
            'symbol': stock.get('symbol', ''),
            'company_name': stock.get('company_name', ''),
            'sector': stock.get('sector', 'Unknown'),
            'price': stock.get('price', 0),
            'dividend_yield': stock.get('dividend_yield', 0),
            'dividend_cagr_3y': stock.get('dividend_cagr_3y', 0),
            'rsi': stock.get('rsi', 0),
            'pe_ratio': stock.get('pe_ratio', 0),
            'pb_ratio': stock.get('pb_ratio', 0),
            'composite_score': stock.get('composite_score', 0),
            # Payout ratio and sustainability fields
            'payout_ratio': stock.get('payout_ratio'),
            'fcf_payout_ratio': stock.get('fcf_payout_ratio'),
            'dividend_sustainable': stock.get('dividend_sustainable', False),
            'dividend_consistent': stock.get('dividend_consistent', False),
            'dividend_years_of_growth': stock.get('dividend_years_of_growth', 0),
            'financially_healthy': stock.get('financially_healthy', False),
        })

    return results


def load_value_dividend_results(search_dirs: List[str]) -> List[dict]:
    """Load results from value-dividend-screener skill."""
    # Try multiple possible filenames
    patterns = [
        'dividend_screener_results.json',
        'dividend_screener_results_*.json',
        'value_dividend_*.json',
    ]

    json_path = None
    for pattern in patterns:
        json_path = find_latest_json(pattern, search_dirs)
        if json_path:
            break

    if not json_path:
        print("Warning: No value dividend results found")
        return []

    print(f"Loading value dividend results from: {json_path}")
    with open(json_path, 'r') as f:
        data = json.load(f)

    stocks = data.get('stocks', [])

    # Transform to common format - include all fields needed for report
    results = []
    for stock in stocks:
        results.append({
            'symbol': stock.get('symbol', ''),
            'company_name': stock.get('company_name', ''),
            'sector': stock.get('sector', 'Unknown'),
            'price': stock.get('price', 0),
            'dividend_yield': stock.get('dividend_yield', 0),
            'dividend_cagr_3y': stock.get('dividend_cagr_3y', 0),
            'pe_ratio': stock.get('pe_ratio', 0),
            'pb_ratio': stock.get('pb_ratio', 0),
            'rsi': stock.get('rsi', 0),
            'composite_score': stock.get('composite_score', 0),
            # Payout ratio and sustainability fields
            'payout_ratio': stock.get('payout_ratio'),
            'fcf_payout_ratio': stock.get('fcf_payout_ratio'),
            'dividend_sustainable': stock.get('dividend_sustainable', False),
            'dividend_consistent': stock.get('dividend_consistent', False),
            'dividend_years_of_growth': stock.get('dividend_years_of_growth', 0),
            'financially_healthy': stock.get('financially_healthy', False),
        })

    return results


def main():
    """Main function to generate combined report."""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Primary search directory: logs/ folder
    # Skills output their results to project_root/logs/
    search_dirs = [
        os.path.join(project_dir, 'logs'),  # Primary location for screening results
        project_dir,  # Project root (legacy fallback)
    ]

    print("=" * 60)
    print("Generating Combined Dividend Screening Report")
    print("=" * 60)

    # Load results from both skills
    growth_results = load_dividend_growth_results(search_dirs)
    value_results = load_value_dividend_results(search_dirs)

    print(f"\nDividend Growth Pullback: {len(growth_results)} stocks")
    print(f"Value Dividend: {len(value_results)} stocks")

    # Generate combined HTML report
    screening_results = {
        'dividend_growth_pullback': growth_results,
        'value_dividend': value_results,
    }

    html_report = generate_html_report(screening_results)

    # Save report
    reports_dir = os.path.join(project_dir, 'reports')
    today = date.today().strftime('%Y-%m-%d')
    report_path = save_report(html_report, today, reports_dir)

    print(f"\nReport saved to: {report_path}")
    print("=" * 60)

    return report_path


if __name__ == '__main__':
    main()

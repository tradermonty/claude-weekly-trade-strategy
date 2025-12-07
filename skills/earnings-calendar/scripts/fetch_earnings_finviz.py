#!/usr/bin/env python3
"""
Finviz Earnings Calendar Fetcher

Fetches earnings calendar using Finviz's "This Week" or "Next Week" option.
This avoids date specification errors that can occur with date-based APIs.

Usage:
    python fetch_earnings_finviz.py [--period THIS_WEEK|NEXT_WEEK] [--min-cap 2e9] [--output FILE]
"""

import argparse
import sys
from datetime import datetime

try:
    from finvizfinance.earnings import Earnings
    import pandas as pd
except ImportError:
    print("Error: Required packages not installed. Run: pip install finvizfinance pandas")
    sys.exit(1)


def fetch_earnings(period: str = "Next Week", min_market_cap: float = 2e9) -> pd.DataFrame:
    """
    Fetch earnings calendar from Finviz.

    Args:
        period: "This Week" or "Next Week"
        min_market_cap: Minimum market cap filter (default $2B)

    Returns:
        DataFrame with earnings data filtered by market cap
    """
    e = Earnings()
    e._set_period(period)

    df = e.df
    if df is None or df.empty:
        return pd.DataFrame()

    # Filter by market cap
    df_filtered = df[df['Market Cap'] >= min_market_cap].copy()

    # Sort by market cap descending
    df_filtered = df_filtered.sort_values('Market Cap', ascending=False)

    return df_filtered


def format_market_cap(value: float) -> str:
    """Format market cap as human-readable string."""
    if value >= 1e12:
        return f"${value/1e12:.1f}T"
    elif value >= 1e9:
        return f"${value/1e9:.1f}B"
    elif value >= 1e6:
        return f"${value/1e6:.1f}M"
    else:
        return f"${value:.0f}"


def parse_earnings_timing(earnings_str: str) -> tuple:
    """
    Parse Finviz earnings timing string.

    Args:
        earnings_str: e.g., "Dec 10/a" or "Dec 11/b"

    Returns:
        (date_str, timing) where timing is "AMC" or "BMO"
    """
    parts = earnings_str.split('/')
    date_str = parts[0].strip()
    timing = "AMC" if len(parts) > 1 and parts[1] == 'a' else "BMO"
    return date_str, timing


def generate_markdown_report(df: pd.DataFrame, period: str) -> str:
    """Generate markdown report from earnings DataFrame."""

    now = datetime.now()

    lines = [
        f"# Earnings Calendar Report",
        f"",
        f"**Generated**: {now.strftime('%Y-%m-%d %H:%M')}",
        f"**Period**: {period}",
        f"**Filter**: Market Cap >= $2B",
        f"**Source**: Finviz",
        f"",
    ]

    if df.empty:
        lines.append("No earnings found for the specified period.")
        return "\n".join(lines)

    # Group by date
    lines.append("## Earnings by Date")
    lines.append("")

    # Get unique dates in order
    dates = df['Earnings'].apply(lambda x: x.split('/')[0]).unique()

    for date in dates:
        date_df = df[df['Earnings'].str.startswith(date)]

        lines.append(f"### {date}")
        lines.append("")
        lines.append("| Ticker | Company | Market Cap | Timing |")
        lines.append("|--------|---------|------------|--------|")

        for _, row in date_df.iterrows():
            ticker = row['Ticker']
            market_cap = format_market_cap(row['Market Cap'])
            _, timing = parse_earnings_timing(row['Earnings'])

            lines.append(f"| **{ticker}** | - | {market_cap} | {timing} |")

        lines.append("")

    # Summary table
    lines.append("## Summary (Top 20 by Market Cap)")
    lines.append("")
    lines.append("| Rank | Ticker | Market Cap | Earnings Date | Timing |")
    lines.append("|------|--------|------------|---------------|--------|")

    for i, (_, row) in enumerate(df.head(20).iterrows(), 1):
        ticker = row['Ticker']
        market_cap = format_market_cap(row['Market Cap'])
        date_str, timing = parse_earnings_timing(row['Earnings'])
        lines.append(f"| {i} | **{ticker}** | {market_cap} | {date_str} | {timing} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Note**: AMC = After Market Close, BMO = Before Market Open")
    lines.append("")
    lines.append("**Important**: This data is from Finviz using relative period selection ")
    lines.append("('This Week' or 'Next Week') to avoid date specification errors.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch earnings calendar from Finviz")
    parser.add_argument(
        "--period",
        choices=["This Week", "Next Week"],
        default="Next Week",
        help="Earnings period (default: Next Week)"
    )
    parser.add_argument(
        "--min-cap",
        type=float,
        default=2e9,
        help="Minimum market cap filter (default: 2e9 = $2B)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "csv", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )

    args = parser.parse_args()

    print(f"Fetching earnings for: {args.period}", file=sys.stderr)
    print(f"Minimum market cap: {format_market_cap(args.min_cap)}", file=sys.stderr)

    df = fetch_earnings(period=args.period, min_market_cap=args.min_cap)

    print(f"Found {len(df)} companies", file=sys.stderr)

    if args.format == "markdown":
        output = generate_markdown_report(df, args.period)
    elif args.format == "csv":
        output = df.to_csv(index=False)
    elif args.format == "json":
        output = df.to_json(orient="records", indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()

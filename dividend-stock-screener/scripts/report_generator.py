"""
HTML report generator for dividend stock screening results.

Generates styled HTML reports with two sections:
1. Dividend Growth Pullback Candidates
2. Value Dividend Candidates
"""
import os
from datetime import date


def format_stability_badge(stock: dict) -> str:
    """Format dividend stability as a badge."""
    if stock.get('dividend_sustainable'):
        return '<span style="background:#27ae60;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">Sustainable</span>'
    elif stock.get('dividend_consistent'):
        return '<span style="background:#f39c12;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">Consistent</span>'
    else:
        return '<span style="background:#95a5a6;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">Variable</span>'


def format_rsi_cell(rsi: float) -> str:
    """Format RSI with color coding."""
    if rsi <= 30:
        return f'<td style="color:#27ae60;font-weight:bold;">{rsi:.0f}</td>'
    elif rsi <= 40:
        return f'<td style="color:#2980b9;font-weight:bold;">{rsi:.0f}</td>'
    else:
        return f'<td>{rsi:.0f}</td>'


def format_score_cell(score: float) -> str:
    """Format composite score with color coding."""
    if score >= 75:
        return f'<td style="color:#27ae60;font-weight:bold;">{score:.1f}</td>'
    elif score >= 60:
        return f'<td style="color:#2980b9;">{score:.1f}</td>'
    else:
        return f'<td>{score:.1f}</td>'


def format_payout_ratio(payout_ratio: float, fcf_payout_ratio: float) -> str:
    """
    Format payout ratio for display.

    When payout ratio > 100% (common for Yieldcos/REITs/MLPs due to accounting),
    use FCF payout ratio instead as it better reflects actual sustainability.

    Args:
        payout_ratio: Traditional payout ratio (dividends / net income)
        fcf_payout_ratio: FCF-based payout ratio (dividends / free cash flow)

    Returns:
        Formatted string like "45%" or "N/A"
    """
    # If payout ratio > 100%, prefer FCF payout ratio
    if payout_ratio is not None and payout_ratio > 100:
        if fcf_payout_ratio is not None:
            return f"{fcf_payout_ratio:.0f}%"
        else:
            return f"{payout_ratio:.0f}%"

    # Normal case: use payout ratio if available
    if payout_ratio is not None:
        return f"{payout_ratio:.0f}%"

    # Fallback to FCF payout if payout ratio not available
    if fcf_payout_ratio is not None:
        return f"{fcf_payout_ratio:.0f}%"

    return "N/A"


def format_growth_stock_row(stock: dict) -> str:
    """
    Format a dividend growth stock as an HTML table row.
    """
    payout = stock.get('payout_ratio')
    fcf_payout = stock.get('fcf_payout_ratio')
    payout_str = format_payout_ratio(payout, fcf_payout)

    years_growth = stock.get('dividend_years_of_growth', 0)
    stability = format_stability_badge(stock)
    rsi_cell = format_rsi_cell(stock.get('rsi', 0))
    score = stock.get('composite_score', 0)
    score_cell = format_score_cell(score)

    return f"""<tr>
        <td><strong>{stock.get('symbol', 'N/A')}</strong></td>
        <td>{stock.get('company_name', 'N/A')}</td>
        <td>{stock.get('sector', 'N/A')}</td>
        <td>${stock.get('price', 0):.2f}</td>
        <td>{stock.get('dividend_yield', 0):.2f}%</td>
        <td>{stock.get('dividend_cagr_3y', 0):.1f}%</td>
        <td>{payout_str}</td>
        <td>{years_growth}Y {stability}</td>
        {rsi_cell}
        {score_cell}
    </tr>"""


def format_value_stock_row(stock: dict) -> str:
    """
    Format a value dividend stock as an HTML table row.
    """
    payout = stock.get('payout_ratio')
    fcf_payout = stock.get('fcf_payout_ratio')
    payout_str = format_payout_ratio(payout, fcf_payout)

    years_growth = stock.get('dividend_years_of_growth', 0)
    stability = format_stability_badge(stock)
    rsi_cell = format_rsi_cell(stock.get('rsi', 0))
    score = stock.get('composite_score', 0)
    score_cell = format_score_cell(score)

    return f"""<tr>
        <td><strong>{stock.get('symbol', 'N/A')}</strong></td>
        <td>{stock.get('company_name', 'N/A')}</td>
        <td>{stock.get('sector', 'N/A')}</td>
        <td>${stock.get('price', 0):.2f}</td>
        <td>{stock.get('dividend_yield', 0):.2f}%</td>
        <td>{stock.get('pe_ratio', 0):.1f}</td>
        <td>{payout_str}</td>
        <td>{years_growth}Y {stability}</td>
        {rsi_cell}
        {score_cell}
    </tr>"""


def generate_html_report(screening_results: dict) -> str:
    """
    Generate a complete HTML report from screening results.
    """
    today = date.today().strftime('%Y-%m-%d')

    growth_stocks = screening_results.get('dividend_growth_pullback', [])
    value_stocks = screening_results.get('value_dividend', [])

    # Generate growth stocks table rows
    if growth_stocks:
        growth_rows = '\n'.join(format_growth_stock_row(s) for s in growth_stocks)
    else:
        growth_rows = '<tr><td colspan="10" style="text-align: center; color: #666;">No qualifying stocks found matching criteria</td></tr>'

    # Generate value stocks table rows
    if value_stocks:
        value_rows = '\n'.join(format_value_stock_row(s) for s in value_stocks)
    else:
        value_rows = '<tr><td colspan="10" style="text-align: center; color: #666;">No qualifying stocks found matching criteria</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dividend Stock Screening Report - {today}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 10px;
        }}
        .date {{
            color: #666;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }}
        .section-desc {{
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-size: 13px;
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 10px 6px;
            text-align: left;
            font-weight: 600;
            white-space: nowrap;
        }}
        td {{
            padding: 8px 6px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        tr:nth-child(even) {{
            background-color: #fafafa;
        }}
        .criteria {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 13px;
        }}
        .criteria strong {{
            color: #2980b9;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #888;
        }}
        .legend {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 12px;
        }}
        .legend-title {{
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Dividend Stock Screening Report</h1>
        <p class="date">Generated: {today}</p>

        <div class="legend">
            <div class="legend-title">Legend:</div>
            <span class="legend-item"><span style="background:#27ae60;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">Sustainable</span> Payout &lt; 80%, FCF covers dividends</span>
            <span class="legend-item"><span style="background:#f39c12;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">Consistent</span> No dividend cuts</span>
            <span class="legend-item"><span style="background:#95a5a6;color:white;padding:2px 6px;border-radius:3px;font-size:11px;">Variable</span> Volatile dividends</span>
            <span class="legend-item">| <strong>Score</strong>: Composite quality score (0-100)</span>
        </div>

        <!-- Section 1: Dividend Growth Pullback -->
        <h2>Dividend Growth Pullback Screening</h2>
        <div class="criteria">
            <strong>Criteria:</strong> Dividend CAGR (3Y) >= 12% | Yield >= 1.5% | RSI <= 40 | Market Cap >= $2B | Positive Revenue/EPS Growth | D/E < 2.0
        </div>
        <p class="section-desc">High-quality dividend growth stocks experiencing temporary pullbacks (oversold RSI conditions).</p>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Sector</th>
                    <th>Price</th>
                    <th>Yield</th>
                    <th>Div CAGR</th>
                    <th>Payout</th>
                    <th>Stability</th>
                    <th>RSI</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>
                {growth_rows}
            </tbody>
        </table>
        <p style="color: #666; font-size: 13px;">Total: {len(growth_stocks)} stocks</p>

        <!-- Section 2: Value Dividend -->
        <h2>Value Dividend Screening</h2>
        <div class="criteria">
            <strong>Criteria:</strong> P/E <= 20 | P/B <= 2 | Yield >= 3% | RSI <= 40 (or lowest RSI) | Dividend Growth (3Y) >= 5% | Positive Revenue/EPS Growth
        </div>
        <p class="section-desc">Undervalued dividend stocks with attractive yields. Sorted by RSI (lowest first).</p>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Sector</th>
                    <th>Price</th>
                    <th>Yield</th>
                    <th>P/E</th>
                    <th>Payout</th>
                    <th>Stability</th>
                    <th>RSI</th>
                    <th>Score</th>
                </tr>
            </thead>
            <tbody>
                {value_rows}
            </tbody>
        </table>
        <p style="color: #666; font-size: 13px;">Total: {len(value_stocks)} stocks</p>

        <div class="footer">
            <p><strong>Disclaimer:</strong> This report is for informational purposes only. Past performance does not guarantee future results. RSI oversold conditions do not guarantee price reversals. Conduct thorough due diligence before making investment decisions.</p>
            <p style="margin-top: 10px;">Data sources: FINVIZ Elite, Financial Modeling Prep (FMP)</p>
        </div>
    </div>
</body>
</html>"""

    return html


def save_report(html_content: str, report_date: str, reports_dir: str) -> str:
    """
    Save HTML report to file.
    """
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"dividend_screening_{report_date}.html"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return filepath

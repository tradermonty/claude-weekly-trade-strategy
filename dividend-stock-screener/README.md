# Dividend Stock Screener

Daily automated screening system for dividend stocks with email reporting.

## Features

- **Dividend Growth Pullback Screening**: Identifies high-quality dividend growth stocks (12%+ CAGR) experiencing temporary pullbacks (RSI <= 40)
- **Value Dividend Screening**: Finds undervalued dividend stocks (P/E <= 20, P/B <= 2, yield >= 3%) with RSI oversold conditions
- **Automated HTML Reports**: Daily reports saved to `reports/` folder with date stamps
- **Email Delivery**: Automatic email delivery via Gmail SMTP

## Requirements

- Python 3.8+
- FINVIZ Elite API subscription (for RSI pre-screening)
- FMP API key (free tier works)
- Gmail account with App Password

## Installation

```bash
# Clone or navigate to the project
cd /Users/takueisaotome/PycharmProjects/dividend-stock-screener

# Install dependencies
pip install requests python-dotenv

# Set environment variables
export FMP_API_KEY=your_fmp_api_key
export FINVIZ_API_KEY=your_finviz_api_key
export GMAIL_APP_PASSWORD=your_gmail_app_password
export SENDER_EMAIL=your_sender_email@gmail.com
```

## Usage

### Manual Execution

```bash
# Run screening and send email report
python3 scripts/run_screening.py
python3 scripts/send_report.py
```

### Automated Execution (Cron)

```bash
# Make shell script executable
chmod +x run_daily_screening.sh

# Add to crontab for daily execution at 6:00 AM
crontab -e
0 6 * * * /Users/takueisaotome/PycharmProjects/dividend-stock-screener/run_daily_screening.sh
```

### Using Claude Code

```bash
# From project directory, run with Claude Code
claude "Run daily dividend screening and send report"
```

## Screening Criteria

### Dividend Growth Pullback
| Metric | Threshold |
|--------|-----------|
| Dividend CAGR (3Y) | >= 12% |
| Dividend Yield | >= 1.5% |
| RSI (14-day) | <= 40 |
| Market Cap | >= $2B |

### Value Dividend
| Metric | Threshold |
|--------|-----------|
| P/E Ratio | <= 20 |
| P/B Ratio | <= 2 |
| Dividend Yield | >= 3% |
| RSI (14-day) | <= 40 |
| Dividend Growth (3Y) | >= 5% |

## Project Structure

```
dividend-stock-screener/
├── CLAUDE.md                 # Claude Code workflow instructions
├── README.md                 # This file
├── run_daily_screening.sh    # Shell script for cron
├── scripts/
│   ├── run_screening.py      # Main screening orchestrator
│   ├── screener.py           # Screening logic
│   ├── report_generator.py   # HTML report generation
│   └── send_report.py        # Email sender
├── reports/                  # Generated reports (YYYY-MM-DD.html)
└── tests/                    # Unit tests
```

## Output

Reports are saved as:
- `reports/dividend_screening_YYYY-MM-DD.html`

Email sent to: taku.saotome@gmail.com

## Data Sources

- **FINVIZ Elite**: Technical screening (RSI, price action)
- **Financial Modeling Prep (FMP)**: Fundamental data (dividends, financials)

## License

Private project for personal use.

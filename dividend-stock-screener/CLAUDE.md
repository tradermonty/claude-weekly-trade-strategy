# Dividend Stock Screener - Daily Report System

## Project Overview

This project performs daily screening of dividend stocks and sends HTML reports via email. It uses two Claude Code skills for screening:

1. **dividend-growth-pullback-screener**: High dividend growth stocks (12%+ CAGR) with RSI <= 40
2. **value-dividend-screener**: Value stocks with attractive yields (3%+), P/E <= 20, P/B <= 2, and RSI <= 40

## Daily Screening Workflow

When asked to "run daily dividend screening" or "run daily screening and send report", execute this workflow:

### Step 1: Run Dividend Growth Pullback Screening

Invoke the `dividend-growth-pullback-screener` skill:

```bash
cd /Users/takueisaotome/PycharmProjects/dividend-stock-screener/.claude/skills/dividend-growth-pullback-screener/scripts
python3 screen_dividend_growth_rsi.py --use-finviz --rsi-max 40
```

Output files will be generated in the scripts directory:
- `dividend_growth_pullback_results_YYYY-MM-DD.json`
- `dividend_growth_pullback_screening_YYYY-MM-DD.md`

### Step 2: Run Value Dividend Screening

Invoke the `value-dividend-screener` skill:

```bash
cd /Users/takueisaotome/PycharmProjects/dividend-stock-screener/.claude/skills/value-dividend-screener/scripts
python3 screen_dividend_stocks.py --use-finviz
```

Output files will be generated in the scripts directory:
- `dividend_screener_results.json`

### Step 3: Generate Combined HTML Report

Run the Python script to combine results and generate HTML report:

```bash
cd /Users/takueisaotome/PycharmProjects/dividend-stock-screener
python3 scripts/generate_combined_report.py
```

The HTML report will be saved to: `reports/dividend_screening_YYYY-MM-DD.html`

### Step 4: Send Email Report

Run the Python script to send the email:

```bash
python3 scripts/send_report.py
```

Email will be sent to: taku.saotome@gmail.com

## Quick Command

Simply ask:
> "Run daily dividend screening and send report"

Claude Code will:
1. Execute the dividend-growth-pullback-screener skill
2. Execute the value-dividend-screener skill
3. Run `scripts/generate_combined_report.py` to create HTML report
4. Run `scripts/send_report.py` to email the report

## Skills Used

### dividend-growth-pullback-screener
- **Location**: `.claude/skills/dividend-growth-pullback-screener/`
- **Purpose**: Find high-quality dividend growth stocks (12%+ CAGR) experiencing temporary pullbacks (RSI <= 40)
- **Knowledge**: `references/` contains methodology documentation

### value-dividend-screener
- **Location**: `.claude/skills/value-dividend-screener/`
- **Purpose**: Find undervalued dividend stocks (P/E <= 20, P/B <= 2, yield >= 3%)
- **Knowledge**: `references/` contains methodology documentation

## Environment Variables Required

```bash
export FMP_API_KEY=your_fmp_api_key
export FINVIZ_API_KEY=your_finviz_api_key
export GMAIL_APP_PASSWORD=your_gmail_app_password
```

## Project Structure

```
dividend-stock-screener/
├── CLAUDE.md                     # This file - workflow for Claude Code
├── README.md                     # Project documentation
├── run_daily_screening.sh        # Shell script for cron (calls Claude Code)
├── .claude/skills/               # Claude Code skills
│   ├── dividend-growth-pullback-screener/
│   │   ├── SKILL.md              # Skill definition & knowledge
│   │   ├── scripts/              # Screening scripts
│   │   └── references/           # Methodology documentation
│   └── value-dividend-screener/
│       ├── SKILL.md              # Skill definition & knowledge
│       ├── scripts/              # Screening scripts
│       └── references/           # Methodology documentation
├── scripts/
│   ├── generate_combined_report.py  # Combines skill results into HTML
│   ├── report_generator.py          # HTML generation module
│   ├── send_report.py               # Email sender
│   └── screener.py                  # Screening criteria module
├── reports/                      # Generated HTML reports
├── tests/                        # Unit tests
└── logs/                         # Execution logs
```

## Cron Execution

The shell script `run_daily_screening.sh` calls Claude Code to execute the workflow:

```bash
# Make executable
chmod +x run_daily_screening.sh

# Cron entry (6:00 AM daily)
0 6 * * * /Users/takueisaotome/PycharmProjects/dividend-stock-screener/run_daily_screening.sh
```

## Manual Testing

To test the complete workflow manually:

```bash
# From project directory
cd /Users/takueisaotome/PycharmProjects/dividend-stock-screener

# Run via Claude Code
claude "Run daily dividend screening and send report"

# Or run the shell script directly
./run_daily_screening.sh
```

## Development Guidelines

- Use TDD approach for new code
- Run tests: `python3 -m pytest tests/ -v`
- Skills contain their own knowledge in `references/` folders
- Refer to skill SKILL.md for detailed screening methodology

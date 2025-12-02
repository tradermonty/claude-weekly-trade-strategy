# Trade Analysis

An automated US stock market analysis and report generation system powered by Claude Code and MCP (Model Context Protocol) servers.

## Overview

This project provides automated trading analysis workflows using Claude Code's agent system. It generates comprehensive market reports, earnings trade analysis, and social media content through scheduled cron jobs or manual execution.

## Features

### Automated Agents

| Agent | Description |
|-------|-------------|
| `earnings-trade-analyst` | Analyzes post-earnings momentum plays with scoring system |
| `after-market-reporter` | Generates daily market summary after US market close |
| `market-environment-strategist` | Comprehensive market environment and regime analysis |
| `fmp-stock-analyzer` | Individual stock fundamental and technical analysis |
| `earnings-analysis-reporter` | Detailed earnings report analysis |
| `report-video-generator` | Creates vertical videos from reports using Remotion |

### MCP Server Integrations

- **Alpaca** - Real-time and historical stock market data
- **Finviz** - Stock screening, fundamentals, and market overview
- **FMP (Financial Modeling Prep)** - Financial statements, estimates, analyst ratings
- **Puppeteer** - Web automation and screenshot capture
- **Remotion** - Programmatic video generation

## Project Structure

```
trade-analysis/
├── .claude/
│   ├── agents/           # Agent definitions
│   └── settings.local.json  # Permission configurations
├── prompts/              # Detailed prompt instructions for each agent
├── reports/              # Generated HTML reports and social media posts
├── scripts/              # Cron automation scripts
├── slides-video/         # Remotion video project
├── logs/                 # Execution logs
├── CLAUDE.md             # Claude Code project configuration
└── .mcp.json             # MCP server configurations
```

## Installation

### Prerequisites

- Claude Code CLI installed (`claude`)
- Node.js 18+ (for Remotion and Puppeteer)
- Python 3.10+ (for MCP servers)
- API keys for:
  - Alpaca (trading data)
  - Finviz Elite (screening)
  - Financial Modeling Prep (fundamentals)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd trade-analysis
```

2. Configure MCP servers in `.mcp.json` with your API keys

3. Install Remotion dependencies (for video generation):
```bash
cd slides-video
npm install
```

## Usage

### Manual Execution

Run agents directly with Claude Code:

```bash
# Earnings Trade Analysis
claude -p "Run the earnings trade analysis using the earnings-trade-analyst agent"

# After Market Report
claude -p "Generate today's after-market report using the after-market-reporter agent"

# Market Environment Analysis
claude -p "Analyze current market environment using the market-environment-strategist agent"
```

### Automated Cron Jobs

Schedule automatic report generation:

```bash
# Edit crontab
crontab -e

# Add entries (US Pacific Time)
# Earnings Trade Report - 6:00 AM PT (Mon-Fri)
0 6 * * 1-5 /path/to/trade-analysis/scripts/run_earnings_trade_report.sh

# After Market Report - 1:10 PM PT (Mon-Fri)
10 13 * * 1-5 /path/to/trade-analysis/scripts/run_after_market_report.sh
```

See `scripts/README.md` for detailed cron setup instructions.

## Output

### Reports Directory

Generated files are saved to `reports/`:

| File Pattern | Description |
|--------------|-------------|
| `earnings_trade_analysis_YYYY-MM-DD.html` | Earnings trade analysis infographic |
| `earnings_trade_X_message_YYYY-MM-DD.md` | Twitter/X post for earnings trades |
| `after_market_report_YYYY_MM_DD.html` | Daily market summary infographic |
| `after_market_report_x_post_YYYY-MM-DD.md` | Twitter/X post for market summary |

### Log Files

Execution logs are saved to `logs/`:
- `earnings_trade_YYYY-MM-DD.log`
- `after_market_YYYY-MM-DD.log`

## Configuration

### CLAUDE.md

Project-level Claude Code configuration for pre-approved tools and permissions.

### settings.local.json

Local permission settings including:
- Allowed tools and MCP server functions
- File read/write permissions
- Bash command allowlist

## Market Hours Reference

| Event | Eastern Time | Pacific Time |
|-------|--------------|--------------|
| Pre-market Open | 4:00 AM | 1:00 AM |
| Market Open | 9:30 AM | 6:30 AM |
| Market Close | 4:00 PM | 1:00 PM |
| After-hours Close | 8:00 PM | 5:00 PM |

## Troubleshooting

### Permission Errors

If Claude Code reports permission errors:
1. Check `settings.local.json` has necessary permissions
2. Use `--dangerously-skip-permissions` flag for automated runs
3. Verify MCP servers are running

### No Output Generated

1. Check log files in `logs/` directory
2. Verify API keys are valid and have sufficient quota
3. Ensure market data is available (weekdays only)

### MCP Server Issues

```bash
# Test MCP server connectivity
claude -p "Test connection to Finviz MCP server by running get_market_overview"
```

## License

Private project - All rights reserved

## Contributing

Internal use only. Contact the repository owner for contribution guidelines.

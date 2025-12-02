# Cron Job Setup for Trade Analysis Reports

## Scripts Overview

| Script | Description | Schedule |
|--------|-------------|----------|
| `run_earnings_trade_report.sh` | Earnings Trade Analysis Report | 6:00 AM PT (Mon-Fri) |
| `run_after_market_report.sh` | After Market Summary Report | 1:10 PM PT (Mon-Fri) |

## Cron Setup Instructions

### 1. Open crontab editor
```bash
crontab -e
```

### 2. Add the following entries

```cron
# Trade Analysis Reports - US Pacific Time
# Note: Adjust for your system timezone if different

# Earnings Trade Report - 6:00 AM PT (Mon-Fri)
# PT = UTC-8 (PST) or UTC-7 (PDT)
# During PST: 14:00 UTC
# During PDT: 13:00 UTC
0 6 * * 1-5 /Users/takueisaotome/PycharmProjects/trade-analysis/scripts/run_earnings_trade_report.sh

# After Market Report - 1:10 PM PT (Mon-Fri)
# PT = UTC-8 (PST) or UTC-7 (PDT)
# During PST: 21:10 UTC
# During PDT: 20:10 UTC
10 13 * * 1-5 /Users/takueisaotome/PycharmProjects/trade-analysis/scripts/run_after_market_report.sh
```

### 3. Save and exit
- In vim: Press `ESC`, then type `:wq` and press Enter
- In nano: Press `Ctrl+O` to save, then `Ctrl+X` to exit

### 4. Verify crontab was saved
```bash
crontab -l
```

## Important Notes

### Timezone Configuration
Your Mac should be set to US Pacific Time. To verify:
```bash
date
```

If your system uses a different timezone, adjust the cron times accordingly.

### Claude CLI Path
The scripts assume Claude CLI is installed at `/opt/homebrew/bin/claude`.
To verify your installation path:
```bash
which claude
```

Update the scripts if your path differs.

### Log Files
Logs are saved to:
- `logs/earnings_trade_YYYY-MM-DD.log`
- `logs/after_market_YYYY-MM-DD.log`

### Permissions Required
The `--dangerously-skip-permissions` flag is used to run without interactive prompts.
This requires that `settings.local.json` has all necessary permissions pre-approved.

### Market Hours Reference
- US Market Open: 9:30 AM ET = 6:30 AM PT
- US Market Close: 4:00 PM ET = 1:00 PM PT

## Troubleshooting

### Script doesn't run
1. Check crontab is active: `crontab -l`
2. Check script permissions: `ls -la scripts/`
3. Run script manually: `./scripts/run_earnings_trade_report.sh`

### No output files generated
1. Check log files in `logs/` folder
2. Verify Claude CLI authentication: `claude --version`
3. Ensure all MCP servers are running

### Permission errors
1. Verify `settings.local.json` has `Write(/Users/takueisaotome/PycharmProjects/trade-analysis/**)`
2. Check file permissions on the project directory

## Manual Execution

To run the reports manually:
```bash
# Earnings Trade Report
./scripts/run_earnings_trade_report.sh

# After Market Report
./scripts/run_after_market_report.sh
```

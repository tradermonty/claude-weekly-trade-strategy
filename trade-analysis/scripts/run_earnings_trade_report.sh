#!/bin/bash
# Earnings Trade Report - Cron Script
# Schedule: Daily at 6:00 AM US Pacific Time
# Cron entry: 0 6 * * 1-5 /path/to/run_earnings_trade_report.sh

# Set PATH for cron environment (node, npm, homebrew, etc.)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/Users/takueisaotome/.npm-global/bin:/Users/takueisaotome/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Configuration
PROJECT_DIR="/Users/takueisaotome/PycharmProjects/trade-analysis"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/earnings_trade_$(date +%Y-%m-%d).log"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Set working directory
cd "${PROJECT_DIR}" || exit 1

# Log start time
echo "=======================================" >> "${LOG_FILE}"
echo "Earnings Trade Report - Started: $(date)" >> "${LOG_FILE}"
echo "=======================================" >> "${LOG_FILE}"

# Run Claude Code with the earnings trade analyst agent
# Using --dangerously-skip-permissions to run without interactive prompts
/Users/takueisaotome/.npm-global/bin/claude -p "Run the earnings trade analysis using the earnings-trade-analyst agent. Follow the instructions in prompts/earnings-trade.md. IMPORTANT: Save all output files directly in the reports/ folder (NOT in date subfolders). Use filenames like earnings_trade_analysis_YYYY-MM-DD.html and earnings_trade_X_message_YYYY-MM-DD.md." \
  --dangerously-skip-permissions \
  >> "${LOG_FILE}" 2>&1

# Capture exit status
EXIT_STATUS=$?

# Log completion
echo "" >> "${LOG_FILE}"
echo "Completed: $(date)" >> "${LOG_FILE}"
echo "Exit Status: ${EXIT_STATUS}" >> "${LOG_FILE}"
echo "=======================================" >> "${LOG_FILE}"

exit ${EXIT_STATUS}

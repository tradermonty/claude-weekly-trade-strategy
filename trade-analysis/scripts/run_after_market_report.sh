#!/bin/bash
# After Market Report - Cron Script
# Schedule: Daily at 1:10 PM US Pacific Time (after market close at 1:00 PM PT)
# Cron entry: 10 13 * * 1-5 /path/to/run_after_market_report.sh

# Set PATH for cron environment (node, npm, homebrew, etc.)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/Users/takueisaotome/.npm-global/bin:/Users/takueisaotome/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Configuration
PROJECT_DIR="/Users/takueisaotome/PycharmProjects/trade-analysis"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/after_market_$(date +%Y-%m-%d).log"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Set working directory
cd "${PROJECT_DIR}" || exit 1

# Log start time
echo "=======================================" >> "${LOG_FILE}"
echo "After Market Report - Started: $(date)" >> "${LOG_FILE}"
echo "=======================================" >> "${LOG_FILE}"

# Run Claude Code with the after-market-reporter agent
# Using --dangerously-skip-permissions to run without interactive prompts
/Users/takueisaotome/.npm-global/bin/claude -p "Generate today's after-market report using the after-market-reporter agent. Follow the instructions in prompts/after-market-report.md and generate the HTML report and X post message in the reports folder." \
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

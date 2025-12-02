#!/bin/bash
# Earnings Analysis Reporter - Command Line Script
# Usage: ./run_earnings_analysis_reporter.sh <TICKER>
# Example: ./run_earnings_analysis_reporter.sh NVDA

# Configuration
PROJECT_DIR="/Users/takueisaotome/PycharmProjects/trade-analysis"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/earnings_analysis_$(date +%Y-%m-%d).log"

# Check if ticker symbol is provided
if [ -z "$1" ]; then
    echo "Error: Ticker symbol is required"
    echo "Usage: $0 <TICKER>"
    echo "Example: $0 NVDA"
    exit 1
fi

TICKER=$(echo "$1" | tr '[:lower:]' '[:upper:]')

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Set working directory
cd "${PROJECT_DIR}" || exit 1

# Log start time
echo "=======================================" >> "${LOG_FILE}"
echo "Earnings Analysis Reporter - Started: $(date)" >> "${LOG_FILE}"
echo "Ticker: ${TICKER}" >> "${LOG_FILE}"
echo "=======================================" >> "${LOG_FILE}"

# Run Claude Code with the earnings-analysis-reporter agent
/Users/takueisaotome/.npm-global/bin/claude -p "Analyze the latest earnings for ${TICKER} using the earnings-analysis-reporter agent. Research the company's IR page for the latest earnings release, analyze market reactions, compare results against consensus estimates, and generate a comprehensive HTML report saved to /reports/ directory with the filename format: ${TICKER}_earnings_analysis_$(date +%Y-%m-%d).html" \
  --dangerously-skip-permissions \
  >> "${LOG_FILE}" 2>&1

# Capture exit status
EXIT_STATUS=$?

# Log completion
echo "" >> "${LOG_FILE}"
echo "Completed: $(date)" >> "${LOG_FILE}"
echo "Exit Status: ${EXIT_STATUS}" >> "${LOG_FILE}"
echo "=======================================" >> "${LOG_FILE}"

# Display result
if [ ${EXIT_STATUS} -eq 0 ]; then
    echo "Earnings analysis complete for ${TICKER}. Check /reports/ for the HTML report."
else
    echo "Analysis failed. Check log: ${LOG_FILE}"
fi

exit ${EXIT_STATUS}

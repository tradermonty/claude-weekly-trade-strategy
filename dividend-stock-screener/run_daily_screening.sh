#!/bin/bash
#
# Daily Dividend Stock Screening Script
#
# This script:
# 1. Calls Claude Code to execute both screening skills
# 2. Runs Python scripts to generate HTML report and send email
#
# Usage:
#   ./run_daily_screening.sh
#
# Cron example (6:00 AM daily):
#   0 6 * * * /Users/takueisaotome/PycharmProjects/dividend-stock-screener/run_daily_screening.sh
#

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Log file
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/screening_$(date +%Y-%m-%d).log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Starting Daily Dividend Stock Screening"
log "=========================================="

# Load environment variables from .env file if exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    log "Loading environment variables from .env"
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        # Remove quotes from value if present
        value="${value%\"}"
        value="${value#\"}"
        export "$key=$value"
    done < "$SCRIPT_DIR/.env"
fi

# Check required environment variables
if [ -z "$FMP_API_KEY" ]; then
    log "ERROR: FMP_API_KEY environment variable not set"
    exit 1
fi

if [ -z "$GMAIL_APP_PASSWORD" ]; then
    log "ERROR: GMAIL_APP_PASSWORD environment variable not set"
    exit 1
fi

# ============================================
# Step 1: Run Dividend Growth Pullback Screening via Claude Code
# ============================================
log "Step 1: Running Dividend Growth Pullback Screening..."

claude --print "Use the dividend-growth-pullback-screener skill to screen for dividend growth stocks with RSI <= 40. Execute the screening script with --use-finviz --rsi-max 40 flag." 2>&1 | tee -a "$LOG_FILE"

# ============================================
# Step 2: Run Value Dividend Screening via Claude Code
# ============================================
log "Step 2: Running Value Dividend Screening..."

claude --print "Use the value-dividend-screener skill to screen for value dividend stocks. Execute the screening script with --use-finviz flag." 2>&1 | tee -a "$LOG_FILE"

# ============================================
# Step 3: Generate Combined HTML Report (Python)
# ============================================
log "Step 3: Generating combined HTML report..."

python3 "$SCRIPT_DIR/scripts/generate_combined_report.py" 2>&1 | tee -a "$LOG_FILE"
REPORT_EXIT_CODE=${PIPESTATUS[0]}

if [ $REPORT_EXIT_CODE -ne 0 ]; then
    log "ERROR: Report generation failed with exit code $REPORT_EXIT_CODE"
    exit $REPORT_EXIT_CODE
fi

# ============================================
# Step 4: Send Email Report (Python)
# ============================================
log "Step 4: Sending email report..."

python3 "$SCRIPT_DIR/scripts/send_report.py" 2>&1 | tee -a "$LOG_FILE"
EMAIL_EXIT_CODE=${PIPESTATUS[0]}

if [ $EMAIL_EXIT_CODE -ne 0 ]; then
    log "ERROR: Email sending failed with exit code $EMAIL_EXIT_CODE"
    exit $EMAIL_EXIT_CODE
fi

log "=========================================="
log "Daily Screening Complete!"
log "=========================================="

exit 0

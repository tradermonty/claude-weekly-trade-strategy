#!/bin/bash
# Run the daily-action-plan skill via Claude Code CLI.
#
# Usage:
#   ./scripts/run_daily_action_plan.sh pre-market
#   ./scripts/run_daily_action_plan.sh post-market
#   ./scripts/run_daily_action_plan.sh           # auto-detect timing
#
# Designed to be invoked by macOS launchd or crontab.
# Requires: claude CLI, FMP_API_KEY in .env or environment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y-%m-%d)
TIMING="${1:-auto}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/dap-${DATE}-${TIMING}.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== Daily Action Plan: timing=$TIMING ==="

# --- Auto-detect timing based on ET ---
if [ "$TIMING" = "auto" ]; then
    # Get current hour in America/New_York
    ET_HOUR=$(TZ="America/New_York" date +%H)
    if [ "$ET_HOUR" -lt 10 ]; then
        TIMING="pre-market"
    else
        TIMING="post-market"
    fi
    log "Auto-detected timing: $TIMING (ET hour=$ET_HOUR)"
fi

# --- Validate timing ---
if [ "$TIMING" != "pre-market" ] && [ "$TIMING" != "post-market" ]; then
    log "ERROR: Invalid timing '$TIMING'. Use 'pre-market' or 'post-market'."
    exit 1
fi

# --- Check working directory ---
cd "$PROJECT_ROOT"
log "Working directory: $(pwd)"

# --- Load .env if exists ---
if [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep '=' | xargs)
    log "Loaded .env"
fi

# --- Check FMP API key ---
if [ -z "${FMP_API_KEY:-}" ]; then
    log "ERROR: FMP_API_KEY not set. Add to .env or export."
    exit 1
fi

# --- Check claude CLI ---
CLAUDE_BIN="${CLAUDE_BIN:-$(which claude 2>/dev/null || echo "")}"
if [ -z "$CLAUDE_BIN" ]; then
    # Common install locations
    for candidate in \
        "$HOME/.local/bin/claude" \
        "$HOME/.claude/bin/claude" \
        "/usr/local/bin/claude"; do
        if [ -x "$candidate" ]; then
            CLAUDE_BIN="$candidate"
            break
        fi
    done
fi

if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then
    log "ERROR: claude CLI not found. Install Claude Code or set CLAUDE_BIN."
    exit 1
fi
log "Using claude: $CLAUDE_BIN"

# --- Check if market is open today ---
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="python3"
fi

MARKET_STATUS=$($PYTHON "$PROJECT_ROOT/.claude/skills/daily-action-plan/scripts/build_plan_state.py" --check-only 2>/dev/null || echo "UNKNOWN")
log "Market status: $MARKET_STATUS"

if [ "$MARKET_STATUS" = "CLOSED" ]; then
    log "Market closed today. Skipping."
    exit 0
fi

# --- Run Claude with the daily-action-plan skill ---
PROMPT="Run daily-action-plan --timing $TIMING"

log "Invoking: claude -p '$PROMPT'"
log "--- Claude output start ---"

"$CLAUDE_BIN" -p "$PROMPT" \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Skill,Agent,WebSearch,WebFetch" \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
log "--- Claude output end (exit=$EXIT_CODE) ---"

# --- Verify output was created ---
REPORT_DIR="$PROJECT_ROOT/reports/$DATE"
if [ "$TIMING" = "pre-market" ]; then
    EXPECTED="$REPORT_DIR/daily-action-plan-pre.md"
else
    EXPECTED="$REPORT_DIR/daily-action-plan-post.md"
fi

if [ -f "$EXPECTED" ]; then
    log "Output created: $EXPECTED"
else
    log "WARNING: Expected output not found: $EXPECTED"
fi

log "=== Done ==="
exit $EXIT_CODE

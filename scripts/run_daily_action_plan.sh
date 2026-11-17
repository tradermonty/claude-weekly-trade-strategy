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
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
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

# The unattended run must not change the repository. It may only write the
# plan (reports/), the pipeline's scratch JSON (/tmp) and its auto memory.
# --setting-sources project keeps user/local allow rules (e.g. a broad
# "Bash(python3:*)") from widening this list, and dontAsk denies anything
# not listed. Only Edit(path) rules gate file writes (they cover Write too).
MEMORY_DIR="$HOME/.claude/projects/$(echo "$PROJECT_ROOT" | sed 's|/|-|g')/memory"
ALLOWED_TOOLS=(
    "Read" "Glob" "Grep" "Skill" "WebSearch" "WebFetch"
    # Read-only FMP market data (daily historical is canonical for WTI / GC)
    "mcp__claude_ai_FMP"
    "Edit(reports/**)" "Edit(//tmp/**)" "Edit(//private/tmp/**)"
    "Edit(/${MEMORY_DIR}/**)"   # "//abs/path" = absolute path in rule syntax
    "Bash(python3 scripts/fetch_market_close.py:*)"
    "Bash(python3 .claude/skills/breadth-chart-analyst/scripts/fetch_breadth_csv.py:*)"
    "Bash(python3 .claude/skills/daily-action-plan/scripts/build_plan_state.py:*)"
    "Bash(python3 .claude/skills/daily-action-plan/scripts/verify_plan.py:*)"
    "Bash(mkdir -p reports/:*)"
    "Bash(date:*)" "Bash(cal:*)" "Bash(ls:*)"
    "Bash(TZ=Asia/Tokyo date:*)" "Bash(TZ=America/New_York date:*)"
)
DISALLOWED_TOOLS=(
    "Bash(git add:*)" "Bash(git commit:*)" "Bash(git push:*)"
    "Bash(git checkout:*)" "Bash(git reset:*)" "Bash(git stash:*)"
    "Edit(trading/**)" "Edit(scripts/**)" "Edit(.claude/**)"
    "Edit(blogs/**)" "Edit(CLAUDE.md)"
)

# build_plan_state.py is allowed to run and takes --output; this confines it.
export DAP_ALLOWED_OUTPUT_DIRS="/tmp:/private/tmp:$PROJECT_ROOT/reports"
# Importing the allowed scripts would otherwise write __pycache__/*.pyc into
# the repository.
export PYTHONDONTWRITEBYTECODE=1

# Anything outside reports/ and logs/ that changes during the run is a
# repository change the run was not allowed to make. Hash every file git
# reports as changed or untracked, plus the ignored files that matter, so a
# file already dirty before the run is still caught if it changes again.
WATCHED_IGNORED=(".env" ".claude/settings.local.json")
repo_state() {
    local f
    {
        git -C "$PROJECT_ROOT" status --porcelain -z --no-renames \
            --untracked-files=all -- . ':(exclude)reports' ':(exclude)logs' \
            2>/dev/null | tr '\0' '\n' | cut -c4- || true
        printf '%s\n' "${WATCHED_IGNORED[@]}"
    } | sort -u | while IFS= read -r f; do
        [ -n "$f" ] || continue
        if [ -f "$PROJECT_ROOT/$f" ]; then
            echo "$(shasum "$PROJECT_ROOT/$f" | cut -d' ' -f1)  $f"
        else
            echo "absent  $f"
        fi
    done
}
if command -v git >/dev/null 2>&1; then
    REPO_DETECT="on"
    REPO_BEFORE="$(repo_state)"
else
    REPO_DETECT="off"
    log "WARNING: git not found; repository change detection is disabled"
fi

log "Invoking: claude -p '$PROMPT' (restricted tools)"
log "--- Claude output start ---"

"$CLAUDE_BIN" -p "$PROMPT" \
    --setting-sources project \
    --permission-mode dontAsk \
    --allowedTools "${ALLOWED_TOOLS[@]}" \
    --disallowedTools "${DISALLOWED_TOOLS[@]}" \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
log "--- Claude output end (exit=$EXIT_CODE) ---"

REPO_CHANGED=""
if [ "$REPO_DETECT" = "on" ]; then
    REPO_AFTER="$(repo_state)"
    if [ "$REPO_BEFORE" != "$REPO_AFTER" ]; then
        # Paths whose hash, presence or dirty state differs between the two.
        REPO_CHANGED="$(diff <(echo "$REPO_BEFORE") <(echo "$REPO_AFTER") \
            | grep -E '^[<>] ' | sed -E 's/^[<>] [^ ]+  //' | sort -u || true)"
        log "WARNING: the run changed repository files outside reports/ and logs/:"
        echo "$REPO_CHANGED" | tee -a "$LOG_FILE"
    fi
else
    REPO_CHANGED="(git が見つからず、変更の検知を実行できませんでした)"
fi

# --- Verify output was created ---
REPORT_DIR="$PROJECT_ROOT/reports/$DATE"
if [ "$TIMING" = "pre-market" ]; then
    EXPECTED="$REPORT_DIR/daily-action-plan-pre.md"
else
    EXPECTED="$REPORT_DIR/daily-action-plan-post.md"
fi

if [ -f "$EXPECTED" ]; then
    log "Output created: $EXPECTED"

    # Surface an unexpected repository change in the e-mailed plan itself.
    if [ -n "$REPO_CHANGED" ]; then
        {
            echo ""
            echo "---"
            echo ""
            echo "## 警告: 自動実行がリポジトリのファイルを変更しました"
            echo ""
            echo "自動実行はコードを変更しない設定です。以下の変更を確認してください。"
            echo ""
            echo '```'
            echo "$REPO_CHANGED"
            echo '```'
        } >> "$EXPECTED"
    fi

    # --- Send email notification (non-blocking) ---
    log "Sending email notification..."
    $PYTHON "$PROJECT_ROOT/scripts/send_dap_email.py" "$EXPECTED" 2>&1 | tee -a "$LOG_FILE" || true
else
    log "WARNING: Expected output not found: $EXPECTED"
fi

log "=== Done ==="
exit $EXIT_CODE

#!/bin/bash
# Install or uninstall macOS launchd jobs for daily action plan automation.
#
# Usage:
#   ./scripts/setup_schedule.sh install    # Install and start jobs
#   ./scripts/setup_schedule.sh uninstall  # Stop and remove jobs
#   ./scripts/setup_schedule.sh status     # Show job status
#   ./scripts/setup_schedule.sh test       # Run a one-time test (post-market)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAUNCHD_SRC="$SCRIPT_DIR/launchd"
LAUNCHD_DST="$HOME/Library/LaunchAgents"
ACTION="${1:-status}"

JOBS=(
    "com.weekly-trade-strategy.pre-market"
    "com.weekly-trade-strategy.post-market"
)

case "$ACTION" in
    install)
        echo "Installing launchd jobs..."
        mkdir -p "$LAUNCHD_DST"
        mkdir -p "$PROJECT_ROOT/logs"

        for job in "${JOBS[@]}"; do
            src="$LAUNCHD_SRC/${job}.plist"
            dst="$LAUNCHD_DST/${job}.plist"

            if [ ! -f "$src" ]; then
                echo "ERROR: Source plist not found: $src"
                exit 1
            fi

            # Unload existing job if loaded
            launchctl list "$job" &>/dev/null && launchctl unload "$dst" 2>/dev/null || true

            # Copy and load
            cp "$src" "$dst"
            launchctl load "$dst"
            echo "  Installed: $job"
        done

        echo ""
        echo "Schedule:"
        echo "  Pre-market:  6:13 AM PT (= 9:13 AM ET) — weekdays"
        echo "  Post-market: 1:17 PM PT (= 4:17 PM ET) — weekdays"
        echo ""
        echo "Note: Weekend/holiday runs are skipped automatically (market status check)."
        echo "Logs: $PROJECT_ROOT/logs/"
        ;;

    uninstall)
        echo "Uninstalling launchd jobs..."
        for job in "${JOBS[@]}"; do
            dst="$LAUNCHD_DST/${job}.plist"
            if [ -f "$dst" ]; then
                launchctl unload "$dst" 2>/dev/null || true
                rm "$dst"
                echo "  Removed: $job"
            else
                echo "  Not found: $job (skipped)"
            fi
        done
        echo "Done."
        ;;

    status)
        echo "=== Daily Action Plan Schedule Status ==="
        echo ""
        for job in "${JOBS[@]}"; do
            dst="$LAUNCHD_DST/${job}.plist"
            if launchctl list "$job" &>/dev/null; then
                echo "  [ACTIVE]   $job"
                launchctl list "$job" 2>/dev/null | head -1
            elif [ -f "$dst" ]; then
                echo "  [LOADED]   $job (plist exists but not active)"
            else
                echo "  [MISSING]  $job"
            fi
        done
        echo ""

        # Show recent logs
        LOG_DIR="$PROJECT_ROOT/logs"
        if [ -d "$LOG_DIR" ]; then
            LATEST=$(ls -t "$LOG_DIR"/dap-*.log 2>/dev/null | head -1)
            if [ -n "${LATEST:-}" ]; then
                echo "Latest log: $LATEST"
                echo "Last 5 lines:"
                tail -5 "$LATEST"
            fi
        fi
        ;;

    test)
        echo "Running one-time test (post-market)..."
        "$SCRIPT_DIR/run_daily_action_plan.sh" post-market
        ;;

    *)
        echo "Usage: $0 {install|uninstall|status|test}"
        exit 1
        ;;
esac

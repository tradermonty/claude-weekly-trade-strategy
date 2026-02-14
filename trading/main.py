"""Entry point for the automated trading system.

Orchestrates three layers using APScheduler 3.x:
  - Layer 1: Rule engine runs every 15 minutes during market hours (9:30-16:00 ET)
  - Layer 2: Claude agent triggered on Layer 1 fires, plus daily at 6:30 ET
  - Layer 3: Order validation and execution

Usage::

    python -m trading.main              # default: dry-run mode
    python -m trading.main --dry-run    # explicit dry-run
    python -m trading.main --live       # live trading (submits real orders)
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler

from trading.config import TradingConfig
from trading.core.holidays import USMarketCalendar
from trading.core.scheduler_guard import SchedulerGuard
from trading.data.database import Database
from trading.data.models import CheckResultType, MarketData, Portfolio, StrategySpec
from trading.layer1.loss_calculator import LossCalculator
from trading.layer1.market_monitor import MarketMonitor
from trading.layer1.rule_engine import RuleEngine
from trading.layer1.stop_loss_manager import StopLossManager
from trading.layer2.agent_runner import AgentRunner
from trading.layer2.tools.strategy_parser import find_latest_blog, parse_blog
from trading.layer3.order_executor import OrderExecutor
from trading.layer3.order_generator import OrderGenerator
from trading.layer3.order_validator import OrderValidator
from trading.services.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

# US/Eastern timezone for APScheduler
TZ = "US/Eastern"


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(log_dir: Path) -> None:
    """Configure root logger with both file and console handlers."""
    log_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    log_file = log_dir / f"trading_{today}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


# ---------------------------------------------------------------------------
# Strategy loader
# ---------------------------------------------------------------------------

def _load_strategy(blogs_dir: Path) -> Optional[StrategySpec]:
    """Find and parse the latest weekly strategy blog."""
    blog_path = find_latest_blog(blogs_dir)
    if blog_path is None:
        logger.error("No weekly strategy blog found in %s", blogs_dir)
        return None
    try:
        spec = parse_blog(blog_path)
        logger.info("Loaded strategy from %s (blog_date=%s)", blog_path.name, spec.blog_date)
        return spec
    except Exception:
        logger.exception("Failed to parse strategy blog: %s", blog_path)
        return None


# ---------------------------------------------------------------------------
# TradingSystem: the main orchestrator
# ---------------------------------------------------------------------------

class TradingSystem:
    """Central orchestrator binding all three layers together.

    Holds references to every subsystem and provides the tick methods
    that APScheduler calls on schedule.
    """

    def __init__(self, config: TradingConfig) -> None:
        self._config = config
        self._calendar = USMarketCalendar()
        self._notifier = EmailNotifier(config)

        # Database
        self._db = Database(config.db_path)
        self._db.connect()
        self._db.migrate()

        # Layer 1
        self._monitor = MarketMonitor(config, self._db)
        self._rule_engine = RuleEngine(config, self._db)
        self._loss_calc = LossCalculator(self._db)
        self._stop_mgr = StopLossManager(config, self._db)

        # Layer 2
        self._agent = AgentRunner(config, self._db)

        # Layer 3
        self._validator = OrderValidator(config, self._db)
        self._generator = OrderGenerator(config)
        self._executor = OrderExecutor(config, self._db)

        # Cached strategy (reloaded when blog changes)
        self._strategy: Optional[StrategySpec] = None
        self._strategy_blog_date: Optional[str] = None
        self._blog_just_updated: bool = False

    # ------------------------------------------------------------------
    # Strategy helpers
    # ------------------------------------------------------------------

    def _ensure_strategy(self) -> Optional[StrategySpec]:
        """Return the current StrategySpec, reloading if a newer blog exists.

        Sets ``_blog_just_updated`` flag when a new blog is detected, so
        callers can trigger stop-order sync only on blog changes.
        """
        self._blog_just_updated = False
        latest = find_latest_blog(self._config.blogs_dir)
        if latest is None:
            if self._strategy is not None:
                return self._strategy
            logger.error("No strategy blog available")
            return None

        blog_date = latest.stem[:10]  # "YYYY-MM-DD"
        if blog_date != self._strategy_blog_date:
            spec = _load_strategy(self._config.blogs_dir)
            if spec is not None:
                self._strategy = spec
                self._strategy_blog_date = spec.blog_date
                self._blog_just_updated = True
                logger.info("Strategy updated to blog_date=%s", spec.blog_date)

        return self._strategy

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _handle_snapshots(self, portfolio: Portfolio, now_et: datetime) -> None:
        """Create daily/weekly snapshots at appropriate times.

        Daily snapshot: first 9:30 check of each trading day.
        Weekly snapshot: Monday 9:30 check.
        HWM is updated every tick in _market_tick_inner (not here).
        """
        today = now_et.date()

        # Daily snapshot (idempotent via INSERT OR IGNORE in DB)
        if now_et.hour == 9 and now_et.minute < 45:
            self._loss_calc.create_daily_snapshot(portfolio)

            # Weekly snapshot on Monday
            if today.weekday() == 0:  # Monday
                self._loss_calc.create_weekly_snapshot(portfolio)

    # ------------------------------------------------------------------
    # Missed daily check detection
    # ------------------------------------------------------------------

    def _daily_check_was_missed(self, now_et: datetime) -> bool:
        """Return True if today's 6:30 daily check did not run.

        We track this via a DB state key ``daily_check_YYYY-MM-DD``.
        """
        today_str = now_et.date().isoformat()
        return self._db.get_state(f"daily_check_{today_str}", "0") == "0"

    def _mark_daily_check_done(self, now_et: datetime) -> None:
        today_str = now_et.date().isoformat()
        self._db.set_state(f"daily_check_{today_str}", "1")

    # ------------------------------------------------------------------
    # Layer 2 + 3 pipeline
    # ------------------------------------------------------------------

    def _run_agent_pipeline(
        self,
        trigger_reason: str,
        market_data: MarketData,
        portfolio: Portfolio,
        strategy_spec: StrategySpec,
    ) -> None:
        """Run Layer 2 (Claude agent) then Layer 3 (validate/execute)."""
        logger.info("Running agent pipeline: trigger=%s", trigger_reason)

        # Layer 2: Claude agent
        intent = self._agent.run(trigger_reason, market_data, portfolio, strategy_spec)
        if intent is None:
            logger.info("Agent returned no intent for trigger=%s", trigger_reason)
            self._db.log_decision(
                timestamp=datetime.now(timezone.utc).isoformat(),
                run_id=None,
                trigger_type=trigger_reason,
                result="NO_ACTION",
                rationale="Agent returned no intent",
            )
            return

        # Layer 3: Validate
        validation = self._validator.validate(intent, strategy_spec, portfolio)
        if not validation.is_approved:
            logger.warning(
                "Validation rejected intent (scenario=%s): %s",
                intent.scenario, validation.errors,
            )
            self._db.log_decision(
                timestamp=datetime.now(timezone.utc).isoformat(),
                run_id=intent.run_id,
                trigger_type=trigger_reason,
                result="REJECTED",
                scenario=intent.scenario,
                rationale=f"Validation errors: {validation.errors}",
            )
            self._notifier.alert(
                f"Order rejected: {validation.errors}"
            )
            return

        # Layer 3: Generate orders
        prices = market_data.etf_prices
        orders = self._generator.generate(intent, portfolio, prices)
        if not orders:
            logger.info("No orders generated for scenario=%s", intent.scenario)
            self._db.log_decision(
                timestamp=datetime.now(timezone.utc).isoformat(),
                run_id=intent.run_id,
                trigger_type=trigger_reason,
                result="APPROVED",
                scenario=intent.scenario,
                rationale="Approved but no orders needed (within thresholds)",
            )
            return

        # Layer 3: Execute
        logger.info("Executing %d orders for scenario=%s", len(orders), intent.scenario)
        results = self._executor.execute(orders)

        # Log the decision
        self._db.log_decision(
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=intent.run_id,
            trigger_type=trigger_reason,
            result="APPROVED",
            scenario=intent.scenario,
            rationale=intent.rationale,
        )

        # Wait for fills (skip in dry-run)
        if not self._config.dry_run:
            submitted_ids = [
                r["client_order_id"] for r in results
                if r.get("status") not in ("dry_run", "failed")
            ]
            if submitted_ids:
                fill_results = self._executor.wait_for_fills(submitted_ids)
                logger.info("Fill results: %s", fill_results)

                # Re-sync stop orders after fills
                refreshed_portfolio = self._monitor.fetch_portfolio()
                if refreshed_portfolio is not None:
                    self._stop_mgr.resync_after_fill_or_rebalance(
                        refreshed_portfolio, strategy_spec,
                    )

        # Notify
        order_summary = ", ".join(
            f"{r['client_order_id']}={r['status']}" for r in results
        )
        self._notifier.info(
            f"Orders executed (scenario={intent.scenario}): {order_summary}"
        )

    # ------------------------------------------------------------------
    # Scheduled jobs
    # ------------------------------------------------------------------

    def market_tick(self) -> None:
        """15-minute interval check during market hours (9:30-16:00 ET Mon-Fri).

        This is the main loop that runs Layer 1, and conditionally
        triggers Layer 2 + 3.
        """
        try:
            self._market_tick_inner()
        except Exception:
            logger.exception("Unhandled error in market_tick")
            self._notifier.critical("Unhandled error in market_tick — see logs")

    def _market_tick_inner(self) -> None:
        import pytz
        now_et = datetime.now(pytz.timezone("US/Eastern"))
        today = now_et.date()

        # Skip weekends
        if today.weekday() >= 5:
            logger.debug("Weekend — skipping market tick")
            return

        # Skip market holidays
        if self._calendar.is_market_holiday(today):
            logger.info("Market holiday (%s) — skipping", today)
            return

        # Skip ticks after early close time (M3 fix: half-day trading)
        if self._calendar.is_early_close(today):
            close_time = self._calendar.get_market_close_time(today)
            if now_et.hour > close_time.hour or (
                now_et.hour == close_time.hour and now_et.minute > 0
            ):
                logger.info(
                    "Early close day (%s) — market closed at %s, skipping",
                    today, close_time.strftime("%H:%M"),
                )
                return

        logger.info(
            "Market tick at %s ET", now_et.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Load strategy
        strategy = self._ensure_strategy()
        if strategy is None:
            logger.error("No strategy available — skipping tick")
            self._notifier.alert("No strategy blog found. Skipping market tick.")
            return

        # Fetch market data and portfolio
        market_data = self._monitor.fetch_market_data()
        portfolio = self._monitor.fetch_portfolio()
        if portfolio is None:
            logger.error("Could not fetch portfolio — skipping tick")
            self._notifier.alert("Portfolio fetch failed. Skipping market tick.")
            return

        # Calibrate index-to-ETF ratios
        self._monitor.calibrate_index_etf_ratios(market_data)

        # Update high-water mark every tick (H2 fix)
        self._loss_calc.update_hwm_if_needed(portfolio)

        # Handle snapshots (daily at 9:30, weekly on Monday 9:30)
        self._handle_snapshots(portfolio, now_et)

        # Detect missed daily check — run it now if missed
        if self._daily_check_was_missed(now_et):
            logger.warning("Missed daily 6:30 check — running now")
            self._run_agent_pipeline(
                "daily_check_missed", market_data, portfolio, strategy,
            )
            self._mark_daily_check_done(now_et)

        # Sync stop orders only when strategy blog changes (H1 fix)
        if self._blog_just_updated:
            self._stop_mgr.sync_stop_orders(strategy, portfolio)

        # Layer 1: Rule engine check
        result = self._rule_engine.check(market_data, portfolio, strategy)
        logger.info("Rule engine result: %s (reason=%s)", result.type.value, result.reason)

        if result.type == CheckResultType.NO_ACTION:
            return

        if result.type == CheckResultType.HALT:
            # Log and notify only — do NOT change positions
            logger.critical("HALT: %s", result.reason)
            self._notifier.critical(f"HALT: {result.reason}. No position changes.")
            return

        if result.type == CheckResultType.STOP_TRIGGERED:
            # Notify only — Alpaca server-side already handled the stop
            logger.info("Stop triggered: %s", result.details)
            self._notifier.alert(
                f"Stop order filled: {result.details}. "
                "Alpaca handled execution. Re-syncing stops."
            )
            # Re-sync remaining stop orders after a fill
            refreshed = self._monitor.fetch_portfolio()
            if refreshed is not None:
                self._stop_mgr.resync_after_fill_or_rebalance(refreshed, strategy)
            return

        if result.type == CheckResultType.TRIGGER_FIRED:
            # Run Layer 2 + 3
            self._run_agent_pipeline(
                result.reason, market_data, portfolio, strategy,
            )

    def daily_check(self) -> None:
        """Daily Claude check at 6:30 ET (Mon-Fri).

        Runs the agent with trigger_reason="daily_check" for pre-market
        analysis. This check does NOT require market data to be live;
        it uses the most recent cached values.
        """
        try:
            self._daily_check_inner()
        except Exception:
            logger.exception("Unhandled error in daily_check")
            self._notifier.critical("Unhandled error in daily_check — see logs")

    def _daily_check_inner(self) -> None:
        import pytz
        now_et = datetime.now(pytz.timezone("US/Eastern"))
        today = now_et.date()

        # Skip weekends
        if today.weekday() >= 5:
            logger.debug("Weekend — skipping daily check")
            return

        # Skip market holidays
        if self._calendar.is_market_holiday(today):
            logger.info("Market holiday (%s) — skipping daily check", today)
            return

        logger.info("Daily check at %s ET", now_et.strftime("%Y-%m-%d %H:%M:%S"))

        strategy = self._ensure_strategy()
        if strategy is None:
            logger.error("No strategy available — skipping daily check")
            self._notifier.alert("No strategy blog found. Skipping daily check.")
            return

        # Fetch data (may use cached/stale values for pre-market)
        market_data = self._monitor.fetch_market_data()
        portfolio = self._monitor.fetch_portfolio()
        if portfolio is None:
            logger.error("Could not fetch portfolio — skipping daily check")
            self._notifier.alert("Portfolio fetch failed. Skipping daily check.")
            return

        # Run agent pipeline
        self._run_agent_pipeline("daily_check", market_data, portfolio, strategy)

        # Mark daily check as done
        self._mark_daily_check_done(now_et)

    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down trading system")
        self._db.close()


# ---------------------------------------------------------------------------
# Build the 15-minute market-hours cron trigger
# ---------------------------------------------------------------------------

def _build_market_hours_trigger():
    """Return an APScheduler cron trigger for every 15 min during 9:30-16:00 ET.

    The schedule covers:
      9:30, 9:45, 10:00, 10:15, ..., 15:45, 16:00

    APScheduler 3.x cron syntax:
      hour=9, minute="30,45"     -> 9:30, 9:45
      hour="10-15", minute="0,15,30,45"  -> 10:00 through 15:45
      hour=16, minute="0"        -> 16:00
    """
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.combining import OrTrigger

    triggers = [
        # 9:30, 9:45
        CronTrigger(
            day_of_week="mon-fri",
            hour=9, minute="30,45",
            timezone=TZ,
        ),
        # 10:00 through 15:45 (every 15 min)
        CronTrigger(
            day_of_week="mon-fri",
            hour="10-15", minute="0,15,30,45",
            timezone=TZ,
        ),
        # 16:00
        CronTrigger(
            day_of_week="mon-fri",
            hour=16, minute=0,
            timezone=TZ,
        ),
    ]
    return OrTrigger(triggers)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated trading system with APScheduler",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run in dry-run mode (log orders but do not submit). This is the default.",
    )
    mode_group.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Run in live mode (submit real orders to Alpaca).",
    )
    args = parser.parse_args()

    # Determine dry_run mode: default is True (dry-run) unless --live is set
    dry_run = not args.live

    # Load config from environment, override dry_run from CLI
    config = TradingConfig.from_env()
    # TradingConfig is frozen, so create a new instance with the CLI override
    config = TradingConfig(
        project_root=config.project_root,
        db_path=config.db_path,
        lock_file=config.lock_file,
        blogs_dir=config.blogs_dir,
        log_dir=config.log_dir,
        alpaca=config.alpaca,
        fmp=config.fmp,
        email=config.email,
        max_daily_loss_pct=config.max_daily_loss_pct,
        max_weekly_loss_pct=config.max_weekly_loss_pct,
        max_drawdown_pct=config.max_drawdown_pct,
        vix_extreme=config.vix_extreme,
        max_daily_orders=config.max_daily_orders,
        max_daily_turnover_pct=config.max_daily_turnover_pct,
        max_single_order_pct=config.max_single_order_pct,
        max_deviation_pct=config.max_deviation_pct,
        min_trade_pct=config.min_trade_pct,
        min_trade_usd=config.min_trade_usd,
        api_fail_warn_threshold=config.api_fail_warn_threshold,
        api_fail_halt_threshold=config.api_fail_halt_threshold,
        fmp_quote_max_staleness=config.fmp_quote_max_staleness,
        fmp_treasury_max_staleness=config.fmp_treasury_max_staleness,
        alpaca_position_max_staleness=config.alpaca_position_max_staleness,
        alpaca_quote_max_staleness=config.alpaca_quote_max_staleness,
        index_etf_tolerance_pct=config.index_etf_tolerance_pct,
        check_interval_minutes=config.check_interval_minutes,
        daily_check_hour=config.daily_check_hour,
        daily_check_minute=config.daily_check_minute,
        dry_run=dry_run,
    )

    # Setup logging
    _setup_logging(config.log_dir)

    mode_label = "DRY-RUN" if config.dry_run else "LIVE"
    logger.info("=" * 60)
    logger.info("Trading system starting in %s mode", mode_label)
    logger.info("=" * 60)

    if not config.dry_run:
        logger.warning(
            "LIVE MODE: Orders will be submitted to Alpaca (%s)",
            "PAPER" if config.alpaca.is_paper else "PRODUCTION",
        )

    # Acquire exclusive file lock
    guard = SchedulerGuard(config.lock_file)
    if not guard.acquire():
        logger.error(
            "Another trading system instance is already running (lock: %s)",
            config.lock_file,
        )
        sys.exit(1)

    system = None
    try:
        # Initialize trading system
        system = TradingSystem(config)

        # Build scheduler
        scheduler = BlockingScheduler(
            timezone=TZ,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 900,
            },
        )

        # Job 1: 15-minute market-hours tick
        scheduler.add_job(
            system.market_tick,
            trigger=_build_market_hours_trigger(),
            id="market_tick",
            name="15-min market hours check",
        )

        # Job 2: Daily Claude check at 6:30 ET (Mon-Fri)
        scheduler.add_job(
            system.daily_check,
            trigger="cron",
            day_of_week="mon-fri",
            hour=config.daily_check_hour,
            minute=config.daily_check_minute,
            timezone=TZ,
            id="daily_check",
            name="Daily 6:30 ET Claude check",
        )

        # Graceful shutdown on SIGINT/SIGTERM
        def _signal_handler(signum: int, frame) -> None:
            sig_name = signal.Signals(signum).name
            logger.info("Received %s — initiating graceful shutdown", sig_name)
            scheduler.shutdown(wait=False)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        logger.info("Scheduler started. Jobs:")
        for job in scheduler.get_jobs():
            logger.info("  - %s (next run: %s)", job.name, job.next_run_time)

        # Start the blocking scheduler (runs until signal)
        scheduler.start()

    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
    finally:
        if system is not None:
            system.shutdown()
        guard.release()
        logger.info("Trading system stopped")


if __name__ == "__main__":
    main()

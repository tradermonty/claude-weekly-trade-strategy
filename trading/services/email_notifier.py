"""Email notification service using Gmail SMTP."""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from trading.config import EmailConfig, TradingConfig

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications at INFO / ALERT / CRITICAL levels.

    Every notification is logged to a file. If SMTP delivery fails the
    log entry is still written so that trading is never blocked by an
    email outage.
    """

    def __init__(self, config: TradingConfig) -> None:
        self._email = config.email
        self._log_dir = config.log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def info(self, message: str) -> None:
        """Send an INFO-level notification."""
        self._notify("INFO", message)

    def alert(self, message: str) -> None:
        """Send an ALERT-level notification."""
        self._notify("ALERT", message)

    def critical(self, message: str) -> None:
        """Send a CRITICAL-level notification."""
        self._notify("CRITICAL", message)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _notify(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"[{ts}] {message}"

        # Always log to file first.
        self._log_to_file(level, body)

        # Attempt email delivery; never raise.
        self._send_email(level, body)

    def _send_email(self, level: str, body: str) -> None:
        cfg = self._email
        if not cfg.sender or not cfg.password or not cfg.recipient:
            logger.debug("Email not configured — skipping SMTP delivery")
            return

        subject = f"[{level}] Trading Bot"
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg.sender
        msg["To"] = cfg.recipient

        try:
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as srv:
                srv.ehlo()
                srv.starttls()
                srv.ehlo()
                srv.login(cfg.sender, cfg.password)
                srv.sendmail(cfg.sender, [cfg.recipient], msg.as_string())
            logger.debug("Email sent: %s", subject)
        except Exception as exc:
            # SMTP failure must never block trading.
            logger.warning("Email delivery failed (%s): %s", subject, exc)

    def _log_to_file(self, level: str, body: str) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = self._log_dir / f"notifications_{today}.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{level}] {body}\n")
        except OSError as exc:
            logger.error("Failed to write notification log: %s", exc)

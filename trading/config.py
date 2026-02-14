"""Configuration for the trading system."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_float(key: str, default: float = 0.0) -> float:
    return float(os.environ.get(key, str(default)))


def _env_int(key: str, default: int = 0) -> int:
    return int(os.environ.get(key, str(default)))


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).lower() in ("true", "1", "yes")


@dataclass(frozen=True)
class AlpacaConfig:
    api_key: str = ""
    secret_key: str = ""
    base_url: str = "https://paper-api.alpaca.markets"  # paper by default
    data_url: str = "https://data.alpaca.markets"

    @classmethod
    def from_env(cls) -> AlpacaConfig:
        return cls(
            api_key=_env("ALPACA_API_KEY"),
            secret_key=_env("ALPACA_SECRET_KEY"),
            base_url=_env("ALPACA_BASE_URL", "https://paper-api.alpaca.markets"),
            data_url=_env("ALPACA_DATA_URL", "https://data.alpaca.markets"),
        )

    @property
    def is_paper(self) -> bool:
        return "paper" in self.base_url


@dataclass(frozen=True)
class FMPConfig:
    api_key: str = ""
    base_url: str = "https://financialmodelingprep.com/api/v3"

    @classmethod
    def from_env(cls) -> FMPConfig:
        return cls(
            api_key=_env("FMP_API_KEY"),
            base_url=_env("FMP_BASE_URL", "https://financialmodelingprep.com/api/v3"),
        )


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender: str = ""
    password: str = ""
    recipient: str = ""

    @classmethod
    def from_env(cls) -> EmailConfig:
        return cls(
            smtp_host=_env("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=_env_int("SMTP_PORT", 587),
            sender=_env("EMAIL_SENDER"),
            password=_env("EMAIL_PASSWORD"),
            recipient=_env("EMAIL_RECIPIENT"),
        )


@dataclass(frozen=True)
class TradingConfig:
    """All trading-related configuration with safe defaults."""

    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    db_path: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "trading_system.db")
    lock_file: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / ".scheduler.lock")
    blogs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "blogs")
    log_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "logs")

    # External services
    alpaca: AlpacaConfig = field(default_factory=AlpacaConfig)
    fmp: FMPConfig = field(default_factory=FMPConfig)
    email: EmailConfig = field(default_factory=EmailConfig)

    # Kill switch thresholds
    max_daily_loss_pct: float = -3.0
    max_weekly_loss_pct: float = -7.0
    max_drawdown_pct: float = -15.0
    vix_extreme: float = 40.0

    # Order limits
    max_daily_orders: int = 10
    max_daily_turnover_pct: float = 30.0
    max_single_order_pct: float = 15.0
    max_deviation_pct: float = 3.0
    min_trade_pct: float = 0.5
    min_trade_usd: float = 100.0

    # API failure escalation
    api_fail_warn_threshold: int = 3
    api_fail_halt_threshold: int = 6

    # Data freshness (seconds)
    fmp_quote_max_staleness: int = 300
    fmp_treasury_max_staleness: int = 86400
    alpaca_position_max_staleness: int = 60
    alpaca_quote_max_staleness: int = 120

    # Index-to-ETF conversion tolerance
    index_etf_tolerance_pct: float = 0.5

    # Scheduler
    check_interval_minutes: int = 15
    daily_check_hour: int = 6
    daily_check_minute: int = 30

    # Mode
    dry_run: bool = True  # log-only mode (no actual orders)

    @classmethod
    def from_env(cls) -> TradingConfig:
        project_root = Path(_env(
            "TRADING_PROJECT_ROOT",
            str(Path(__file__).parent.parent),
        ))
        return cls(
            project_root=project_root,
            db_path=project_root / "data" / "trading_system.db",
            lock_file=project_root / "data" / ".scheduler.lock",
            blogs_dir=project_root / "blogs",
            log_dir=project_root / "data" / "logs",
            alpaca=AlpacaConfig.from_env(),
            fmp=FMPConfig.from_env(),
            email=EmailConfig.from_env(),
            dry_run=_env_bool("TRADING_DRY_RUN", True),
            max_daily_loss_pct=_env_float("MAX_DAILY_LOSS_PCT", -3.0),
            max_weekly_loss_pct=_env_float("MAX_WEEKLY_LOSS_PCT", -7.0),
            max_drawdown_pct=_env_float("MAX_DRAWDOWN_PCT", -15.0),
        )

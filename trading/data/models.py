"""Data models for the trading system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional


# --- Enums ---

class CheckResultType(Enum):
    HALT = "halt"
    TRIGGER_FIRED = "trigger_fired"
    STOP_TRIGGERED = "stop_triggered"
    NO_ACTION = "no_action"


class ValidationResultType(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class NotificationLevel(Enum):
    INFO = "info"
    ALERT = "alert"
    CRITICAL = "critical"


# --- Check Results ---

@dataclass
class CheckResult:
    type: CheckResultType
    reason: str = ""
    details: Optional[dict] = None

    @classmethod
    def HALT(cls, reason: str) -> CheckResult:
        return cls(type=CheckResultType.HALT, reason=reason)

    @classmethod
    def TRIGGER_FIRED(cls, reason: str) -> CheckResult:
        return cls(type=CheckResultType.TRIGGER_FIRED, reason=reason)

    @classmethod
    def STOP_TRIGGERED(cls, details: dict) -> CheckResult:
        return cls(type=CheckResultType.STOP_TRIGGERED, reason="stop_triggered", details=details)

    @classmethod
    def NO_ACTION(cls) -> CheckResult:
        return cls(type=CheckResultType.NO_ACTION)


@dataclass
class ValidationResult:
    type: ValidationResultType
    errors: list[str] = field(default_factory=list)

    @classmethod
    def APPROVED(cls) -> ValidationResult:
        return cls(type=ValidationResultType.APPROVED)

    @classmethod
    def REJECTED(cls, errors: list[str]) -> ValidationResult:
        return cls(type=ValidationResultType.REJECTED, errors=errors)

    @property
    def is_approved(self) -> bool:
        return self.type == ValidationResultType.APPROVED


# --- Strategy Intent (Claude output) ---

@dataclass
class StrategyIntent:
    run_id: str
    scenario: str               # "base" / "bull" / "bear" / "tail_risk"
    rationale: str
    target_allocation: dict[str, float]  # {symbol: target_pct}
    priority_actions: list[dict]
    confidence: str             # "high" / "medium" / "low"
    blog_reference: str


# --- Strategy Spec (parsed from blog) ---

@dataclass
class TradingLevel:
    buy_level: Optional[float] = None
    sell_level: Optional[float] = None
    stop_loss: Optional[float] = None


@dataclass
class ScenarioSpec:
    name: str                   # "base" / "bull" / "bear" / "tail_risk"
    probability: int            # percentage (e.g. 45)
    triggers: list[str]
    allocation: dict[str, float]  # {symbol: pct}


@dataclass
class StrategySpec:
    blog_date: str              # YYYY-MM-DD
    current_allocation: dict[str, float]  # {symbol: pct}
    scenarios: dict[str, ScenarioSpec]
    trading_levels: dict[str, TradingLevel]  # {"sp500": TradingLevel, ...}
    stop_losses: dict[str, float]  # {"sp500": 6685.0, ...}
    vix_triggers: dict[str, float]  # {"risk_on": 17, "caution": 20, ...}
    yield_triggers: dict[str, float]  # {"lower": 4.11, "warning": 4.36, ...}
    breadth_200ma: Optional[float] = None
    uptrend_ratio: Optional[float] = None
    bubble_score: Optional[int] = None
    bubble_max: int = 15
    pre_event_dates: list[str] = field(default_factory=list)

    def get_scenario_allocation(self, scenario_name: str) -> dict[str, float]:
        if scenario_name in self.scenarios:
            return self.scenarios[scenario_name].allocation
        return self.current_allocation


# --- Market Data ---

@dataclass
class MarketData:
    timestamp: datetime
    vix: Optional[float] = None
    us10y: Optional[float] = None
    sp500: Optional[float] = None
    nasdaq: Optional[float] = None
    dow: Optional[float] = None
    gold: Optional[float] = None
    oil: Optional[float] = None
    copper: Optional[float] = None
    etf_prices: dict[str, float] = field(default_factory=dict)

    def get_index(self, name: str) -> Optional[float]:
        mapping = {
            "sp500": self.sp500, "nasdaq": self.nasdaq, "dow": self.dow,
            "gold": self.gold, "oil": self.oil, "copper": self.copper,
        }
        return mapping.get(name)


# --- Portfolio ---

@dataclass
class Position:
    symbol: str
    shares: float
    market_value: float
    cost_basis: float
    current_price: float


@dataclass
class Portfolio:
    account_value: float
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)

    def get_position_pct(self, symbol: str) -> float:
        if symbol not in self.positions or self.account_value == 0:
            return 0.0
        return (self.positions[symbol].market_value / self.account_value) * 100.0


# --- Orders ---

@dataclass
class Order:
    client_order_id: str
    symbol: str
    side: str                   # "buy" / "sell"
    quantity: float
    order_type: str             # "limit" / "market" / "stop"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"


# --- Snapshots ---

@dataclass
class AccountSnapshot:
    snapshot_type: str          # "daily_open" / "weekly_open"
    date: str                   # YYYY-MM-DD
    account_value: float
    created_at: Optional[str] = None


# --- Decision Log ---

@dataclass
class DecisionLog:
    timestamp: str
    run_id: Optional[str]
    trigger_type: str
    result: str                 # "NO_ACTION" / "APPROVED" / "REJECTED" / "HALT"
    scenario: Optional[str] = None
    rationale: Optional[str] = None

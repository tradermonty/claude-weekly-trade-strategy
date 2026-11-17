"""Session-date contract for independently published daily CSV feeds.

Dates denote US exchange sessions, not download/publication dates. Never map
an arbitrary weekend-labelled observation onto Friday: the producer must supply
an explicit session date. HTTP success says nothing about observation freshness.
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from trading.core.holidays import USMarketCalendar


def is_session(day: date) -> bool:
    return day.weekday() < 5 and not USMarketCalendar().is_market_holiday(day)


def previous_session(day: date) -> date:
    day -= timedelta(days=1)
    while not is_session(day):
        day -= timedelta(days=1)
    return day


def expected_session(report_date: date, timing: str) -> date:
    """Pre-market needs the previous session; post-market needs today's close."""
    if timing not in ("pre-market", "post-market"):
        raise ValueError(f"Invalid report timing: {timing}")
    if timing == "post-market" and is_session(report_date):
        return report_date
    return previous_session(report_date)


def completed_session(now: datetime | None = None) -> date:
    """Latest completed exchange session at an aware instant (including DST)."""
    now = now or datetime.now(ZoneInfo("America/New_York"))
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    local = now.astimezone(ZoneInfo("America/New_York"))
    day = local.date()
    if (is_session(day)
            and local.time() >= USMarketCalendar().get_market_close_time(day)):
        return day
    return previous_session(day)


def feed_freshness(observation_date, previous_date, expected: date) -> dict:
    """Keep original dates plus explicit current/prior session validity."""
    try:
        observed = date.fromisoformat(observation_date)
        if not is_session(observed):
            state = "invalid_session"
        elif observed < expected:
            state = "stale"
        elif observed > expected:
            state = "future"
        else:
            state = "fresh"
    except (TypeError, ValueError):
        state = "missing" if not observation_date else "invalid_date"
    prior = previous_session(expected).isoformat()
    return {
        "observation_date": observation_date,
        "expected_session": expected.isoformat(),
        "state": state,
        "fresh": state == "fresh",
        "previous_observation_date": previous_date,
        "expected_previous_session": prior,
        "consecutive": state == "fresh" and previous_date == prior,
    }


def describe_freshness(name: str, freshness: dict) -> str:
    return (
        f"{name}: 観測日 {freshness['observation_date'] or '不明'} / "
        f"期待取引日 {freshness['expected_session']} / {freshness['state']}"
    )

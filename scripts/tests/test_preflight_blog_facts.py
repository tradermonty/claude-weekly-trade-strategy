"""Tests for preflight_blog_facts.py option-expiry facts.

Focus: VIX options are AM-settled, so the tradable window ends the business
day BEFORE the expiry date. The 2026-07-27 blog quoted the 7/29 VIX weekly as
covering the 7/29 14:00 ET FOMC statement; those contracts stopped trading
7/28. The snapshot now carries `vix_last_trading_day` so the writer cannot
work from the expiry date alone.

Run with:
    python3 -m pytest scripts/tests/test_preflight_blog_facts.py -v
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "preflight_blog_facts",
    PROJECT_ROOT / "scripts" / "preflight_blog_facts.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules["preflight_blog_facts"] = module
spec.loader.exec_module(module)

prev_business_day = module.prev_business_day
get_option_expiries = module.get_option_expiries
US_MARKET_HOLIDAYS_2026 = module.US_MARKET_HOLIDAYS_2026


# === prev_business_day ===

def test_prev_business_day_midweek():
    assert prev_business_day(date(2026, 7, 29)) == date(2026, 7, 28)


def test_prev_business_day_skips_weekend():
    # Monday 2026-07-27 → Friday 2026-07-24
    assert prev_business_day(date(2026, 7, 27)) == date(2026, 7, 24)


def test_prev_business_day_skips_holiday():
    # 2026-07-03 is the observed Independence Day holiday, so the business day
    # before Monday 7/6 is Thursday 7/2.
    assert "2026-07-03" in US_MARKET_HOLIDAYS_2026
    assert prev_business_day(date(2026, 7, 6)) == date(2026, 7, 2)


# === vix_last_trading_day in the snapshot ===

def test_vix_last_trading_day_covers_weeklies_and_monthlies():
    out = get_option_expiries(2026, 7)
    ltd = out["vix_last_trading_day"]
    # Every VIX expiry in scope has a last trading day
    for expiry in list(out["vix_standard"].values()) + out["vix_weekly_wednesdays"]:
        if expiry:
            assert expiry in ltd


def test_the_2026_07_29_incident_case():
    """The expiry that triggered the incident resolves to 7/28."""
    out = get_option_expiries(2026, 7)
    assert out["vix_last_trading_day"]["2026-07-29"] == "2026-07-28"


def test_august_monthly_still_covers_a_july_fomc():
    out = get_option_expiries(2026, 7)
    ltd = date.fromisoformat(out["vix_last_trading_day"]["2026-08-19"])
    fomc_statement = date(2026, 7, 29)
    assert ltd > fomc_statement


def test_last_trading_day_is_always_before_expiry():
    out = get_option_expiries(2026, 7)
    for expiry, ltd in out["vix_last_trading_day"].items():
        assert date.fromisoformat(ltd) < date.fromisoformat(expiry)


def test_settlement_note_is_present():
    out = get_option_expiries(2026, 7)
    note = out["vix_settlement_note"]
    assert "AM-settled" in note
    assert "PRECEDING business day" in note


def test_existing_expiry_fields_unchanged():
    """The added fields must not disturb what downstream code already reads."""
    out = get_option_expiries(2026, 7)
    assert out["equity_etf_standard"]["2026-08"] == "2026-08-21"
    assert out["vix_standard"]["2026-08"] == "2026-08-19"
    assert "2026-07-29" in out["vix_weekly_wednesdays"]


if __name__ == "__main__":
    # Lightweight runner so CI can execute this file directly without pytest.
    # Without it the CI step exits 0 having run nothing.
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

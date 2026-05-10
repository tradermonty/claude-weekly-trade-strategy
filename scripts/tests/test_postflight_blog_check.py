"""Smoke tests for postflight_blog_check.py.

These tests use synthetic blog snippets to verify each detector triggers
on Round 2-4 incident patterns and stays silent on the corrected blog.

Run with:
    python3 -m pytest scripts/tests/test_postflight_blog_check.py -v
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "postflight_blog_check",
    PROJECT_ROOT / "scripts" / "postflight_blog_check.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules["postflight_blog_check"] = module
spec.loader.exec_module(module)

check_forbidden_terms = module.check_forbidden_terms
check_etf_spot_prices = module.check_etf_spot_prices
check_option_otm = module.check_option_otm
check_option_expiries = module.check_option_expiries
check_day_of_week = module.check_day_of_week
check_ir_times_against_yaml = module.check_ir_times_against_yaml
check_ir_manifest_completeness = module.check_ir_manifest_completeness


SNAPSHOT_FIXTURE = {
    "target_week_start": "2026-05-11",
    "market_prices": {
        "SPY": {"price": 737.62},
        "QQQ": {"price": 711.23},
        "GLD": {"price": 433.77},
    },
    "option_expiries": {
        "equity_etf_standard": {"2026-05": "2026-05-15", "2026-06": "2026-06-18"},
        "vix_standard": {"2026-05": "2026-05-19", "2026-06": "2026-06-17"},
        "vix_weekly_wednesdays": ["2026-05-06", "2026-05-13", "2026-05-20", "2026-05-27", "2026-06-03", "2026-06-10"],
    },
    "day_of_week_table": [
        {"date": "2026-05-11", "day_jp": "月"},
        {"date": "2026-05-12", "day_jp": "火"},
        {"date": "2026-05-13", "day_jp": "水"},
        {"date": "2026-05-14", "day_jp": "木"},
        {"date": "2026-05-15", "day_jp": "金"},
    ],
}


# === Issue #19: Option Expiry ===

def test_forbidden_6_19_expiry():
    findings = check_forbidden_terms("QQQ プット $640、6/19 満期")
    msgs = [f.message for f in findings]
    assert any("6/19 満期" in m for m in msgs)


def test_forbidden_5_21_vix_expiry():
    findings = check_forbidden_terms("VIX call 23 strike、5/21 満期")
    msgs = [f.message for f in findings]
    assert any("5/21 満期" in m for m in msgs)


# === Issue #21: Forbidden terminology ===

def test_forbidden_powell_tainin():
    findings = check_forbidden_terms("Powell 退任 + Warsh 後任承認待ち")
    assert any("Powell 退任" in f.message for f in findings)


def test_forbidden_panic_mode():
    findings = check_forbidden_terms("即時 Panic Mode に移行")
    assert any("Panic Mode" in f.message for f in findings)


def test_allowed_tail_risk_defensive_mode():
    findings = check_forbidden_terms("Tail Risk Defensive Mode に移行")
    # Tail Risk Defensive Mode is the approved phrase; no Panic Mode finding
    assert not any("Panic Mode" in f.message for f in findings)


def test_forbidden_fed_quiet_week():
    findings = check_forbidden_terms("5/11-5/17 は Fed 静寂週")
    assert any("静寂週" in f.message for f in findings)


def test_forbidden_wikipedia():
    findings = check_forbidden_terms("[詳細](https://en.wikipedia.org/wiki/foo)")
    assert any("Wikipedia" in f.message for f in findings)


# === Issue #18: ETF spot price ===

def test_etf_spot_present_passes():
    body = "GLD $433.77 維持。QQQ $711.23 で過熱。SPY $737.62 ATH 圏。"
    findings = check_etf_spot_prices(body, SNAPSHOT_FIXTURE)
    assert findings == []


def test_etf_spot_missing_fails():
    body = "GLD ≈ $473 で安定。QQQ ≈ $687 で天井圏。"
    findings = check_etf_spot_prices(body, SNAPSHOT_FIXTURE)
    assert any(f.severity == "high" and "GLD" in f.message for f in findings)
    assert any(f.severity == "high" and "QQQ" in f.message for f in findings)


# === Issue #18: OTM% auto-recompute ===

def test_otm_correct_passes():
    # QQQ $660 put @ $711.23 → -7.20% OTM
    body = "QQQ プット: $660 ストライク (現値 $711.23、-7.2% OTM)"
    findings = check_option_otm(body)
    assert findings == []


def test_otm_round_2_qqq_bug_detected():
    # Original Round 2 bug: claimed -6.8% but actual -10.0%
    body = "QQQ プット: $640 ストライク (現値 $711.23、-6.8% OTM)"
    findings = check_option_otm(body)
    assert any("QQQ" in f.message and "-10.0%" in f.message for f in findings)


def test_otm_round_2_gld_bug_detected():
    # Original Round 2 bug: claimed +3.6% with wrong spot $473 (actual $433.77)
    # If the body has wrong spot, OTM matches that spot → caught by spot check.
    # If body has correct spot but wrong OTM:
    body = "GLD コール: $490 ストライク (現値 $433.77、+3.6% OTM)"
    findings = check_option_otm(body)
    assert any("GLD" in f.message and "+13.0%" in f.message for f in findings)


# === Issue #19: Option expiry calendar ===

def test_option_expiry_correct_passes():
    body = "QQQ プット 6/18 (木) 満期。VIX コール 5/19 (火) 満期。"
    findings = check_option_expiries(body, SNAPSHOT_FIXTURE)
    assert findings == []


def test_option_expiry_juneteenth_bug_detected():
    body = "QQQ プット 6/19 満期 (Juneteenth 無視)"
    findings = check_option_expiries(body, SNAPSHOT_FIXTURE)
    assert any("6/19" in f.message for f in findings)


# === Issue #6: Day of week ===

def test_dow_correct_passes():
    body = "5/14 (木) Retail Sales、5/15 (金) Industrial Production"
    findings = check_day_of_week(body, SNAPSHOT_FIXTURE)
    assert findings == []


def test_dow_round_2_bug_detected():
    # Round 2 bug: 5/14 was written as Friday
    body = "Uptrend Ratio 5/14 (金) 週次更新予定"
    findings = check_day_of_week(body, SNAPSHOT_FIXTURE)
    assert any("5/14" in f.message and "(木)" in f.message for f in findings)


# === Round 5 regressions: spot must be cross-checked against facts ===

def test_otm_with_stale_spot_in_options_block_detected():
    """Round 5 finding 1: even if facts.SPY is correct elsewhere,
    a stale spot inside the options block (QQQ 現値 $687) must fail.
    """
    body = """
    Body has correct prices: SPY $737.62, QQQ $711.23, GLD $433.77

    Options:
    QQQ プット: $640 ストライク (現値 $687、-6.8% OTM、6/18 満期)
    GLD コール: $490 ストライク (現値 $473、+3.6% OTM、6/18 満期)
    """
    findings = check_option_otm(body, SNAPSHOT_FIXTURE)
    # Should detect that body's $687 doesn't match facts QQQ $711.23
    msgs = [f.message for f in findings]
    assert any("QQQ" in m and ("$687" in m or "spot mismatch" in m.lower()) for m in msgs), \
        f"Expected QQQ spot mismatch detection, got: {msgs}"
    assert any("GLD" in m and ("$473" in m or "spot mismatch" in m.lower()) for m in msgs), \
        f"Expected GLD spot mismatch detection, got: {msgs}"


# === Round 5 regression: VIX weekly date must NOT be allowed for ETF options ===

def test_etf_option_using_vix_weekly_date_detected():
    """Round 5 finding 3: 5/20 is a VIX weekly Wed, NOT a valid ETF monthly expiry.
    QQQ プット 5/20 満期 must fail because QQQ uses ETF expiries, not VIX weeklies.
    """
    body = "QQQ プット 5/20 (水) 満期"
    findings = check_option_expiries(body, SNAPSHOT_FIXTURE)
    # Currently passes because 5/20 is in valid_md as VIX weekly. After fix, must fail.
    assert any("5/20" in f.message and ("ETF" in f.message or "QQQ" in f.message) for f in findings), \
        f"Expected ETF-vs-VIX expiry mismatch, got findings: {[f.message for f in findings]}"


# === Round 5 regression: webcast/release must be cross-checked, not just call ===

PBR_IR_YAML = """
target_week_start: 2026-05-11
events:
  - ticker: PBR
    company: Petrobras
    official_ir_url: "https://www.investidorpetrobras.com.br/en/"
    source_type: official
    items:
      - type: release
        date_et: "2026-05-11"
        timing: AMC
        time_et: null
        time_note: "after markets close, time not specified"
      - type: webcast
        date_et: "2026-05-12"
        time_et: "10:30"
        time_jst: "23:30"
"""


def test_pbr_webcast_wrong_time_detected():
    """Round 5 finding 2: webcast time mismatch must be detected.
    Body says 'PBR webcast 16:30 ET' but ir_events.yaml says 10:30 ET.
    """
    body = "PBR webcast: 16:30 ET = 5:30 JST (5/12)"
    findings = check_ir_times_against_yaml(body, PBR_IR_YAML)
    assert any("PBR" in f.message and "16:30" in f.message for f in findings), \
        f"Expected PBR webcast 16:30 ET mismatch, got: {[f.message for f in findings]}"


def test_pbr_release_with_time_when_official_says_null():
    """Round 5 follow-up: if ir_events.yaml has time_et: null for release,
    and body writes a specific time, that must be flagged.
    """
    body = "PBR Q1 決算 release: 5/11 16:30 ET (米国引け後想定)"
    findings = check_ir_times_against_yaml(body, PBR_IR_YAML)
    assert any("PBR" in f.message and ("release" in f.message.lower() or "未明示" in f.message) for f in findings), \
        f"Expected PBR release-time-when-null finding, got: {[f.message for f in findings]}"


def test_pbr_jst_mismatch_detected():
    """Round 5 finding 5: JST in body must match ir_events.yaml time_jst.
    Body says webcast 19:30 JST but yaml says 23:30 JST.
    """
    body = "PBR webcast: 5/12 10:30 ET = 19:30 JST"
    findings = check_ir_times_against_yaml(body, PBR_IR_YAML)
    assert any("PBR" in f.message and ("JST" in f.message or "19:30" in f.message) for f in findings), \
        f"Expected PBR JST mismatch, got: {[f.message for f in findings]}"


# === Round 6 regressions ===

EMPTY_IR_YAML = """
target_week_start: 2026-05-11
events: []
"""


def test_round6_unverified_ticker_in_body_detected():
    """Round 6 finding 1: if body mentions BABA/CEG earnings call/release/webcast
    but manifest does not include that ticker, postflight must fail.
    """
    body = "BABA call: 5/13 6:00 ET (推測値)。CEG call: 5/11 8:00 ET。"
    findings = check_ir_manifest_completeness(body, EMPTY_IR_YAML)
    msgs = " | ".join(f.message for f in findings)
    assert "BABA" in msgs and ("manifest" in msgs.lower() or "未記載" in msgs.lower() or "not in" in msgs.lower()), \
        f"Expected BABA-not-in-manifest finding, got: {msgs}"
    assert "CEG" in msgs and ("manifest" in msgs.lower() or "未記載" in msgs.lower() or "not in" in msgs.lower()), \
        f"Expected CEG-not-in-manifest finding, got: {msgs}"


def test_round6_pbr_webcast_in_mixed_summary_detected():
    """Round 6 finding 2: when body summary mixes 'PBR webcast 16:30 ET'
    and other ticker call times in the same block, postflight should still
    detect the PBR webcast time mismatch via nearest-label association.
    """
    body = "[ ] PBR webcast 5/12 16:30 ET / BABA call 7:30 ET / CEG call 10:00 ET"
    findings = check_ir_times_against_yaml(body, PBR_IR_YAML)
    # PBR webcast should be detected as wrong (yaml says 10:30 ET, body says 16:30 ET)
    msgs = [f.message for f in findings]
    assert any("PBR" in m and "webcast" in m.lower() and "16:30" in m for m in msgs), \
        f"Expected PBR webcast 16:30 mismatch in mixed summary, got: {msgs}"


# Build a fixture VIX weekly snapshot
SNAPSHOT_FIXTURE_VIX_STRICT = dict(SNAPSHOT_FIXTURE)


def test_round6_vix_weekly_non_recommended_warned():
    """Round 6 finding 3: VIX expiry 5/20 (Wed weekly that is NOT post-AMAT
    weekly 5/27, NOT May standard 5/19) should produce a warning.
    """
    body = "VIX コール 23 strike、5/20 満期"
    findings = check_option_expiries(body, SNAPSHOT_FIXTURE_VIX_STRICT)
    # Expect at least a Medium warning about VIX 5/20 not being recommended
    assert any("5/20" in f.message and ("VIX" in f.message or "weekly" in f.message.lower()) and f.severity in ("medium", "high") for f in findings), \
        f"Expected VIX 5/20 warning, got: {[(f.severity, f.message) for f in findings]}"


if __name__ == "__main__":
    # Lightweight runner without pytest dependency
    test_funcs = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for fn in test_funcs:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

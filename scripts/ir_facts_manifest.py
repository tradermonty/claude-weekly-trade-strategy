#!/usr/bin/env python3
"""IR facts manifest generator/validator.

Generates `reports/YYYY-MM-DD/ir_events.yaml` from earnings calendar data,
or validates an existing one against schema rules.

The schema enforces release/call/webcast separation and forbids estimated times.

Usage:
    # Generate template from earnings calendar
    python3 scripts/ir_facts_manifest.py --date 2026-05-11 --generate

    # Validate existing manifest
    python3 scripts/ir_facts_manifest.py --date 2026-05-11 --validate

Reference: CLAUDE.md Issue #20 (Earnings Call Time IR Verification).
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Forbidden patterns in IR time fields
FORBIDDEN_TIME_PATTERNS = [
    re.compile(r"推定", re.IGNORECASE),
    re.compile(r"approx\.?", re.IGNORECASE),
    re.compile(r"\bestimated\b", re.IGNORECASE),
    re.compile(r"~\s*\d", re.IGNORECASE),
]


TEMPLATE = """# IR Events Manifest — __DATE__
# Schema v1.0 (CLAUDE.md Issue #20)
#
# Rules:
# 1. release / call / webcast must be SEPARATE entries (not combined).
# 2. Time fields must be VERIFIED from official IR. No estimation allowed.
# 3. If official IR does not specify a time, use:
#      time_et: null
#      time_note: "Official IR does not specify time"
# 4. official_ir_url is REQUIRED for every entry.
# 5. 3rd-party sources (StockTitan, Seeking Alpha, etc.) only allowed when
#    official IR is inaccessible; mark with `source_type: third_party`.
# 6. All date_et MUST fall within target_week_start ... target_week_start+6
#    (the validator rejects out-of-range dates).
#
# Schema reference (commented; uncomment and fill per ticker):
#
# - ticker: TICKER
#   company: Full Company Name
#   market_cap_usd_b: 0.0
#   impact: high|medium|low
#   official_ir_url: "https://..."         # MANDATORY
#   source_type: official                  # or "third_party" with note
#   items:
#     - type: release                       # release | call | webcast
#       date_et: "YYYY-MM-DD"               # MUST be within target week
#       timing: BMO                          # BMO | AMC | midday | (omit if only webcast)
#       time_et: null                        # null when official未明示
#       time_note: "..."                     # required when time_et is null
#     - type: call
#       date_et: "YYYY-MM-DD"
#       time_et: "HH:MM"                     # HH:MM ET, verified from IR
#       time_jst: "HH:MM"                    # HH:MM JST via zoneinfo
#       verified_via: "IR page section ..."

target_week_start: __DATE__

events:
  # === FILL IN VERIFIED ENTRIES BELOW ===
  # (Empty list is acceptable for low-news weeks; validator will pass.)
"""


def cmd_generate(target_date: date, force: bool) -> int:
    out_path = PROJECT_ROOT / "reports" / target_date.isoformat() / "ir_events.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists() and not force:
        print(f"Refusing to overwrite existing {out_path}. Use --force.", file=sys.stderr)
        return 1
    out_path.write_text(TEMPLATE.replace("__DATE__", target_date.isoformat()))
    print(f"Wrote template to {out_path.relative_to(PROJECT_ROOT)}")
    print("Next: market-news-analyzer must fill in verified IR times.")
    return 0


def cmd_validate(target_date: date) -> int:
    """Lightweight validation without yaml dependency: regex-based string checks."""
    from datetime import timedelta
    path = PROJECT_ROOT / "reports" / target_date.isoformat() / "ir_events.yaml"
    if not path.exists():
        print(f"FAIL: {path.relative_to(PROJECT_ROOT)} does not exist.", file=sys.stderr)
        return 2
    text = path.read_text()
    fails: list[str] = []

    # Verify target_week_start matches
    twk_m = re.search(r"^target_week_start:\s*(\S+)", text, flags=re.MULTILINE)
    if not twk_m:
        fails.append("missing target_week_start")
    elif twk_m.group(1) != target_date.isoformat():
        fails.append(
            f"target_week_start='{twk_m.group(1)}' does not match --date={target_date.isoformat()}"
        )

    # Compute valid date range: target week +0..+6 days
    valid_dates = {(target_date + timedelta(days=i)).isoformat() for i in range(7)}

    # Check for forbidden time patterns
    for pat in FORBIDDEN_TIME_PATTERNS:
        for m in pat.finditer(text):
            line_num = text[: m.start()].count("\n") + 1
            fails.append(f"line {line_num}: forbidden time qualifier '{m.group()}' (Issue #20)")

    # Check that every ticker block has official_ir_url
    ticker_blocks = re.split(r"^\s*-\s+ticker:\s*", text, flags=re.MULTILINE)
    for i, block in enumerate(ticker_blocks[1:], 1):
        if "official_ir_url" not in block:
            fails.append(f"ticker block #{i}: missing official_ir_url (Issue #20)")

    # Check each items list separates release/call/webcast (no combined types)
    for m in re.finditer(r"^\s+-\s+type:\s*(\S+)", text, flags=re.MULTILINE):
        type_val = m.group(1).strip().strip('"').strip("'")
        if type_val not in {"release", "call", "webcast"}:
            line_num = text[: m.start()].count("\n") + 1
            fails.append(f"line {line_num}: invalid type '{type_val}' (must be release/call/webcast)")

    # Check items have either time_et: null with time_note, or time_et: HH:MM
    for m in re.finditer(r"^\s+time_et:\s*(\S.*)$", text, flags=re.MULTILINE):
        val = m.group(1).strip()
        line_num = text[: m.start()].count("\n") + 1
        if val == "null":
            after = text[m.end():m.end() + 200]
            if "time_note" not in after:
                fails.append(f"line {line_num}: time_et: null requires time_note explaining why")
        elif val.startswith('"') or val.startswith("'"):
            content = val.strip('"').strip("'")
            if not re.match(r"^\d{2}:\d{2}", content) and "T" not in content:
                fails.append(f"line {line_num}: time_et must be HH:MM or ISO timestamp, got '{content}'")

    # Date range check (Round 5 finding 4): every date_et must be within target week
    for m in re.finditer(r'^\s+date_et:\s*"?([0-9]{4}-[0-9]{2}-[0-9]{2})"?', text, flags=re.MULTILINE):
        d = m.group(1)
        if d not in valid_dates:
            line_num = text[: m.start()].count("\n") + 1
            fails.append(
                f"line {line_num}: date_et '{d}' is outside target week "
                f"({sorted(valid_dates)[0]} ... {sorted(valid_dates)[-1]})"
            )

    if fails:
        print("VALIDATION FAILED:", file=sys.stderr)
        for f in fails:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1

    print(f"PASS: {path.relative_to(PROJECT_ROOT)} is valid (Issue #20 schema)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="IR facts manifest generator/validator")
    p.add_argument("--date", required=True, help="Target week start date (YYYY-MM-DD)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--generate", action="store_true", help="Generate template (must be filled by market-news-analyzer)")
    g.add_argument("--validate", action="store_true", help="Validate existing manifest")
    p.add_argument("--force", action="store_true", help="Overwrite existing file (with --generate)")
    args = p.parse_args()

    target = date.fromisoformat(args.date)
    if args.generate:
        return cmd_generate(target, args.force)
    if args.validate:
        return cmd_validate(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())

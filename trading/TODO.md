# Trading System - Remaining Tasks

Last updated: 2026-02-14
Current status: Phase 1 complete + Phase 2 code (F1/F3/F5) complete, 201 tests passing

---

## 1. Unimplemented E2E Tests (from design doc Section 10)

The following E2E tests are specified in `docs/auto-trade-system-design-v2.md:1066-1083`
but not yet implemented in `trading/tests/test_e2e_failures.py`.

| Test | Description | Priority |
|------|-------------|----------|
| `test_fmp_api_timeout` | FMP API 10s timeout: previous value retained + ALERT_ONLY | Medium |
| `test_alpaca_order_rejected` | Alpaca order rejection: log + email notification | Medium |
| `test_partial_fill_recovery` | Partial fill: correct evaluation at next check cycle | Medium |
| `test_db_lock_contention` | SQLite lock: retry with PRAGMA busy_timeout=5000 | Low |
| `test_process_crash_recovery` | Stale lock file: recovery via SchedulerGuard | Low |

Already implemented (9 of 14):
`test_duplicate_order_prevention`, `test_kill_switch_overrides_claude`,
`test_api_escalation_3_then_6`, `test_email_send_failure` (3 tests),
`test_stale_blog_handling` (2 tests), `test_holiday_detection` (6 tests),
`test_replace_order_failure_fallback` (in test_stop_loss_manager.py),
`test_session_freshness_premarket` (in test_data_validator.py),
`test_fractional_vs_whole_shares` (2 tests)

---

## 2. Operational Phases (design doc Section 9)

### Phase 2: Paper Trading (4 weeks)

Ref: `docs/auto-trade-system-design-v2.md:1029`

Code is complete. Operational validation remains:

- [ ] Deploy to Alpaca paper account
- [ ] Run 15-min interval checks for 3-4 weeks
- [ ] Verify Claude -> Rule Engine -> Order pipeline end-to-end
- [ ] Verify server-side stop orders are placed correctly and fire on index stop levels
- [ ] Verify client_order_id deduplication works against Alpaca
- [ ] Verify email notifications for all decision types (NO_ACTION/ALERT_ONLY/REBALANCE/HALT_AND_NOTIFY)
- [ ] Completion criteria: no unintended orders for 3 weeks

### Phase 3: Live Trading (staged scale-up)

Ref: `docs/auto-trade-system-design-v2.md:1042`

- [ ] 20% capital allocation (2 weeks)
- [ ] 50% capital allocation (2 weeks)
- [ ] 100% capital allocation (2 weeks)
- [ ] Criteria: paper trade returns within +/-5% of manual trading

---

## 3. Pre-Production Configuration

Before switching from `--dry-run` to `--live`:

- [ ] `ANTHROPIC_API_KEY` - set valid key for Layer 2 Claude agent
- [ ] `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` - switch from paper to live credentials
- [ ] `FMP_API_KEY` - verify rate limits for 15-min interval (96/day, well within free 250/day)
- [ ] SMTP settings - verify email delivery for alerts/critical notifications
- [ ] Confirm `dry_run=False` toggle procedure in `trading/config.py`
- [ ] Verify blog file exists in `blogs/` directory before first live run

---

## 4. Minor Warnings (Optional)

- [ ] `websockets.legacy` DeprecationWarning from alpaca-py
  - Harmless; tests pass. Will resolve when alpaca-py updates their dependency.
  - Ref: https://websockets.readthedocs.io/en/stable/howto/upgrade.html

---

## Implementation History

| Date | Milestone | Tests |
|------|-----------|-------|
| 2026-02-13 | Phase 1 implementation (Layer 1 + data foundation) | 163 |
| 2026-02-13 | Phase 1 review fixes (4 HIGH, 5 MEDIUM, 1 LOW) | 180 |
| 2026-02-14 | Phase 2 code: F1 Claude SDK, F3 atomic stop, F5 freshness | 199 |
| 2026-02-14 | F5 Medium fixes: timezone conversion, single-source stale check | 201 |

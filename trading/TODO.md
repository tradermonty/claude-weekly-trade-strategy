# Trading System - Remaining Tasks

Last updated: 2026-02-14
Current status: Phase 1 complete + Phase 2 code (F1/F3/F5) complete, all E2E tests implemented, 388 tests passing

---

## 1. ~~Unimplemented E2E Tests~~ (COMPLETE)

All 14 E2E tests specified in `docs/auto-trade-system-design-v2.md:1066-1083`
are now implemented in `trading/tests/test_e2e_failures.py`.

All implemented (14 of 14):
`test_duplicate_order_prevention`, `test_kill_switch_overrides_claude`,
`test_api_escalation_3_then_6`, `test_email_send_failure` (3 tests),
`test_stale_blog_handling` (2 tests), `test_holiday_detection` (6 tests),
`test_replace_order_failure_fallback` (in test_stop_loss_manager.py),
`test_session_freshness_premarket` (in test_data_validator.py),
`test_fractional_vs_whole_shares` (2 tests),
`test_fmp_api_timeout`, `test_alpaca_order_rejected`,
`test_partial_fill_recovery`, `test_db_lock_contention` (2 tests),
`test_process_crash_recovery` (3 tests)

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

## 5. Backtest Walk-Forward Re-validation

- [ ] **~2026-05-08**: Walk-forward 統計的有意性の再検証
  - 現状: n=71日, p=0.1456, verdict=NOT_SIGNIFICANT
  - 推定必要日数: ~127日（~25週）で p<0.05 到達見込み
  - 前提: 平均日次超過リターン +0.073%, IR=2.78 が維持される場合
  - コマンド:
    ```bash
    .venv/bin/python -m trading.backtest --start 2025-11-03 --end 2026-05-08 \
      --phase B --walk-forward --output results/robustness/
    ```
  - 判定が SIGNIFICANT に変われば B-transition 戦略の統計的裏付けが得られる
  - レジーム変化があった場合は Newey-West / ブートストラップ CI の追加を検討

---

## Implementation History

| Date | Milestone | Tests |
|------|-----------|-------|
| 2026-02-13 | Phase 1 implementation (Layer 1 + data foundation) | 163 |
| 2026-02-13 | Phase 1 review fixes (4 HIGH, 5 MEDIUM, 1 LOW) | 180 |
| 2026-02-14 | Phase 2 code: F1 Claude SDK, F3 atomic stop, F5 freshness | 199 |
| 2026-02-14 | F5 Medium fixes: timezone conversion, single-source stale check | 201 |
| 2026-02-14 | Backtest: cost model, benchmarks, robustness, walk-forward | 380 |
| 2026-02-14 | Fix TZ bug in count_today_orders + all E2E tests complete | 388 |

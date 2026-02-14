"""Tests for TriggerMatcher (Phase B)."""

from datetime import date, datetime

import pytest

from trading.backtest.trigger_matcher import TriggerMatcher, TRIGGER_SCENARIO_MAP
from trading.data.models import MarketData, ScenarioSpec, StrategySpec, TradingLevel


# --- Helpers ---

def _market(vix: float = 18.0, sp500: float = 6000.0) -> MarketData:
    return MarketData(
        timestamp=datetime(2026, 1, 5),
        vix=vix,
        sp500=sp500,
    )


def _strategy(
    scenarios: dict[str, ScenarioSpec] | None = None,
    vix_triggers: dict[str, float] | None = None,
    trading_levels: dict[str, TradingLevel] | None = None,
) -> StrategySpec:
    if scenarios is None:
        scenarios = {
            "base": ScenarioSpec("base", 50, [], {"SPY": 50, "BIL": 50}),
            "bull": ScenarioSpec("bull", 20, [], {"SPY": 70, "BIL": 30}),
            "bear": ScenarioSpec("bear", 25, [], {"SPY": 30, "BIL": 70}),
            "tail_risk": ScenarioSpec("tail_risk", 5, [], {"SPY": 10, "BIL": 90}),
        }
    return StrategySpec(
        blog_date="2026-01-05",
        current_allocation={"SPY": 50, "BIL": 50},
        scenarios=scenarios,
        trading_levels=trading_levels or {},
        stop_losses={},
        vix_triggers=vix_triggers or {"risk_on": 17, "caution": 20, "stress": 23},
        yield_triggers={},
    )


class _MockPortfolio:
    def get_allocation_pct(self):
        return {"SPY": 50, "BIL": 50}


# --- VIX Trigger Tests ---

class TestVIXTriggers:
    def test_vix_cross_up_stress(self):
        """VIX crossing up through stress level."""
        tm = TriggerMatcher()
        strat = _strategy()
        portfolio = _MockPortfolio()

        # First call establishes baseline
        tm.check(_market(vix=22.0), portfolio, strat)
        # Second call crosses stress (23)
        trigger = tm.check(_market(vix=24.0), portfolio, strat)
        assert trigger == "vix_stress"

    def test_vix_cross_up_caution(self):
        """VIX crossing up through caution level."""
        tm = TriggerMatcher()
        strat = _strategy()
        portfolio = _MockPortfolio()

        tm.check(_market(vix=19.0), portfolio, strat)
        trigger = tm.check(_market(vix=21.0), portfolio, strat)
        assert trigger == "vix_caution"

    def test_vix_cross_down_risk_on(self):
        """VIX crossing down through risk_on level."""
        tm = TriggerMatcher()
        strat = _strategy()
        portfolio = _MockPortfolio()

        tm.check(_market(vix=18.0), portfolio, strat)
        trigger = tm.check(_market(vix=16.0), portfolio, strat)
        assert trigger == "vix_risk_on"

    def test_vix_cross_down_caution_recover(self):
        """VIX crossing down through caution (recovery)."""
        tm = TriggerMatcher()
        strat = _strategy()
        portfolio = _MockPortfolio()

        tm.check(_market(vix=21.0), portfolio, strat)
        trigger = tm.check(_market(vix=19.0), portfolio, strat)
        assert trigger == "vix_caution_recover"

    def test_vix_no_cross_no_trigger(self):
        """VIX within range, no crossing."""
        tm = TriggerMatcher()
        strat = _strategy()
        portfolio = _MockPortfolio()

        tm.check(_market(vix=18.0), portfolio, strat)
        trigger = tm.check(_market(vix=19.0), portfolio, strat)
        assert trigger is None

    def test_first_day_no_trigger(self):
        """First day should not trigger (no previous VIX to compare)."""
        tm = TriggerMatcher()
        strat = _strategy()
        portfolio = _MockPortfolio()

        trigger = tm.check(_market(vix=25.0), portfolio, strat)
        assert trigger is None  # No prev_vix


class TestVIXCustomThresholds:
    def test_uses_strategy_thresholds(self):
        """Should use strategy's thresholds, not defaults."""
        tm = TriggerMatcher()
        # Custom: stress at 25 instead of 23
        strat = _strategy(vix_triggers={"risk_on": 15, "caution": 18, "stress": 25})
        portfolio = _MockPortfolio()

        tm.check(_market(vix=24.0), portfolio, strat)
        # VIX 24->26 crosses stress at 25
        trigger = tm.check(_market(vix=26.0), portfolio, strat)
        assert trigger == "vix_stress"


# --- Index Level Trigger Tests ---

class TestIndexLevelTriggers:
    def test_stop_loss_trigger(self):
        """Index hitting stop loss level."""
        tm = TriggerMatcher()
        levels = {"sp500": TradingLevel(buy_level=5800, sell_level=6200, stop_loss=5500)}
        strat = _strategy(trading_levels=levels)
        portfolio = _MockPortfolio()

        trigger = tm.check(_market(vix=18, sp500=5400), portfolio, strat)
        assert trigger == "index_stop_loss"

    def test_buy_level_trigger(self):
        """Index hitting buy level."""
        tm = TriggerMatcher()
        levels = {"sp500": TradingLevel(buy_level=5800, sell_level=6200, stop_loss=5500)}
        strat = _strategy(trading_levels=levels)
        portfolio = _MockPortfolio()

        trigger = tm.check(_market(vix=18, sp500=5750), portfolio, strat)
        assert trigger == "index_buy_level"

    def test_sell_level_trigger(self):
        """Index hitting sell level."""
        tm = TriggerMatcher()
        levels = {"sp500": TradingLevel(buy_level=5800, sell_level=6200, stop_loss=5500)}
        strat = _strategy(trading_levels=levels)
        portfolio = _MockPortfolio()

        trigger = tm.check(_market(vix=18, sp500=6300), portfolio, strat)
        assert trigger == "index_sell_level"


# --- Drift Trigger Tests ---

class TestDriftTrigger:
    def test_large_drift_triggers(self):
        """Drift > threshold should trigger."""
        tm = TriggerMatcher(drift_threshold_pct=3.0)
        strat = _strategy()

        class DriftedPortfolio:
            def get_allocation_pct(self):
                return {"SPY": 55, "BIL": 45}  # 5% drift

        trigger = tm.check(_market(vix=18), DriftedPortfolio(), strat)
        assert trigger == "drift"

    def test_small_drift_no_trigger(self):
        """Drift within threshold should not trigger."""
        tm = TriggerMatcher(drift_threshold_pct=3.0)
        strat = _strategy()

        class SmallDriftPortfolio:
            def get_allocation_pct(self):
                return {"SPY": 52, "BIL": 48}  # 2% drift

        trigger = tm.check(_market(vix=18), SmallDriftPortfolio(), strat)
        assert trigger is None


# --- Scenario Resolution Tests ---

class TestResolveScenario:
    def test_vix_stress_to_tail_risk(self):
        tm = TriggerMatcher()
        strat = _strategy()
        assert tm.resolve_scenario("vix_stress", strat) == "tail_risk"

    def test_vix_stress_fallback_to_bear(self):
        """When tail_risk absent, fall back to bear."""
        scenarios = {
            "base": ScenarioSpec("base", 60, [], {"SPY": 50, "BIL": 50}),
            "bear": ScenarioSpec("bear", 40, [], {"SPY": 30, "BIL": 70}),
        }
        tm = TriggerMatcher()
        strat = _strategy(scenarios=scenarios)
        assert tm.resolve_scenario("vix_stress", strat) == "bear"

    def test_vix_risk_on_to_bull(self):
        tm = TriggerMatcher()
        strat = _strategy()
        assert tm.resolve_scenario("vix_risk_on", strat) == "bull"

    def test_vix_caution_to_bear(self):
        tm = TriggerMatcher()
        strat = _strategy()
        assert tm.resolve_scenario("vix_caution", strat) == "bear"

    def test_fallback_to_base(self):
        """When all candidates missing, fall back to base."""
        scenarios = {
            "base": ScenarioSpec("base", 100, [], {"SPY": 50, "BIL": 50}),
        }
        tm = TriggerMatcher()
        strat = _strategy(scenarios=scenarios)
        result = tm.resolve_scenario("vix_stress", strat)
        assert result == "base"

    def test_no_base_raises(self):
        """When even base is missing, raise ValueError."""
        scenarios = {
            "custom": ScenarioSpec("custom", 100, [], {"SPY": 50, "BIL": 50}),
        }
        tm = TriggerMatcher()
        strat = _strategy(scenarios=scenarios)
        with pytest.raises(ValueError, match="No usable scenario"):
            tm.resolve_scenario("vix_stress", strat)

    def test_drift_returns_none(self):
        """Drift trigger returns None (no scenario change)."""
        tm = TriggerMatcher()
        strat = _strategy()
        assert tm.resolve_scenario("drift", strat) is None

    def test_index_stop_loss_to_bear(self):
        tm = TriggerMatcher()
        strat = _strategy()
        assert tm.resolve_scenario("index_stop_loss", strat) == "bear"

    def test_index_buy_level_to_bull(self):
        tm = TriggerMatcher()
        strat = _strategy()
        assert tm.resolve_scenario("index_buy_level", strat) == "bull"


# --- Trigger Priority Tests ---

class TestTriggerPriority:
    def test_vix_checked_before_index(self):
        """VIX trigger should fire before index level check."""
        tm = TriggerMatcher()
        levels = {"sp500": TradingLevel(buy_level=5800, sell_level=6200, stop_loss=5500)}
        strat = _strategy(trading_levels=levels)
        portfolio = _MockPortfolio()

        # First call: VIX 19
        tm.check(_market(vix=19.0, sp500=6000), portfolio, strat)
        # Second call: VIX crosses caution AND sp500 at buy level
        trigger = tm.check(_market(vix=21.0, sp500=5750), portfolio, strat)
        # VIX should fire first
        assert trigger == "vix_caution"


# --- TRIGGER_SCENARIO_MAP Tests ---

class TestTriggerScenarioMap:
    def test_all_triggers_have_mapping(self):
        expected_triggers = {
            "vix_stress", "vix_caution", "vix_risk_on",
            "vix_caution_recover", "index_stop_loss",
            "index_buy_level", "index_sell_level", "drift",
        }
        assert set(TRIGGER_SCENARIO_MAP.keys()) == expected_triggers

    def test_scenario_candidates_are_valid(self):
        valid_scenarios = {"base", "bull", "bear", "tail_risk"}
        for trigger, candidates in TRIGGER_SCENARIO_MAP.items():
            for c in candidates:
                assert c in valid_scenarios, f"{trigger}: {c} is not a valid scenario"

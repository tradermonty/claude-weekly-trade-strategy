"""MCP tool: emit_strategy_intent — parses Claude's output into StrategyIntent."""

from __future__ import annotations

import logging

from trading.data.models import StrategyIntent

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("run_id", "scenario", "target_allocation", "confidence")


def parse_strategy_intent(raw: dict) -> StrategyIntent:
    """Validate and convert Claude's raw tool output to a StrategyIntent.

    Parameters
    ----------
    raw:
        Dict from Claude's emit_strategy_intent tool call input.

    Returns
    -------
    StrategyIntent
        Validated strategy intent dataclass.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    # Check required fields
    missing = [f for f in REQUIRED_FIELDS if f not in raw or raw[f] is None]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Validate scenario
    valid_scenarios = {"base", "bull", "bear", "tail_risk"}
    scenario = raw["scenario"]
    if scenario not in valid_scenarios:
        raise ValueError(
            f"Invalid scenario '{scenario}'. Must be one of: {valid_scenarios}"
        )

    # Validate confidence
    valid_confidence = {"high", "medium", "low"}
    confidence = raw["confidence"]
    if confidence not in valid_confidence:
        raise ValueError(
            f"Invalid confidence '{confidence}'. Must be one of: {valid_confidence}"
        )

    # Validate target_allocation
    allocation = raw["target_allocation"]
    if not isinstance(allocation, dict) or len(allocation) == 0:
        raise ValueError("target_allocation must be a non-empty dict")

    for symbol, pct in allocation.items():
        if not isinstance(pct, (int, float)):
            raise ValueError(
                f"Allocation for {symbol} must be numeric, got {type(pct).__name__}"
            )
        if pct < 0:
            raise ValueError(f"Allocation for {symbol} cannot be negative: {pct}")

    total = sum(allocation.values())
    if abs(total - 100.0) > 0.5:
        raise ValueError(
            f"Target allocation must sum to ~100%, got {total:.1f}%"
        )

    # Validate priority_actions if present
    priority_actions = raw.get("priority_actions", [])
    if not isinstance(priority_actions, list):
        priority_actions = []

    return StrategyIntent(
        run_id=raw["run_id"],
        scenario=scenario,
        rationale=raw.get("rationale", ""),
        target_allocation=allocation,
        priority_actions=priority_actions,
        confidence=confidence,
        blog_reference=raw.get("blog_reference", ""),
    )

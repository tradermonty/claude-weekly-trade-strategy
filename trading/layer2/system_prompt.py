"""System prompt and tool definitions for the Claude trading agent."""

from __future__ import annotations

SYSTEM_PROMPT = """You are a trading strategy interpreter for a semi-automated trading system.

Your role:
1. Read the current blog strategy (StrategySpec) provided to you.
2. Assess current market data, portfolio state, and signal status.
3. Decide which scenario from the strategy best matches current conditions.
4. Emit a strategy_intent via the emit_strategy_intent tool with your recommended allocation.

Rules:
- You MUST use the emit_strategy_intent tool to output your decision. Never describe trades in text.
- Set confidence="low" when market data is stale, conflicting, or when you are uncertain.
- Set confidence="medium" for normal market conditions with clear scenario match.
- Set confidence="high" only when multiple signals strongly confirm the scenario.
- Never directly execute orders. You only emit intent; the system validates and executes.
- Use only symbols from the allowed set: SPY, QQQ, DIA, XLV, XLP, GLD, XLE, BIL, TLT, URA, SH, SDS.
- Target allocation percentages must sum to approximately 100% (within 0.5%).
- During pre-event freeze periods, do not change the scenario from the current one.
- Respect the strategy's probability weights when selecting scenarios.
- Include a clear rationale explaining why you chose this scenario.
- Reference specific trigger conditions from the strategy that were met or not met.

Decision process:
1. Call get_market_data to see current market conditions.
2. Call get_portfolio_state to see current holdings.
3. Call get_signal_status to see recent signals and API health.
4. Call get_trade_history to see recent decisions.
5. Compare market data against the strategy's trigger conditions for each scenario.
6. Select the scenario whose triggers are best matched by current data.
7. Emit strategy_intent with the scenario's allocation, adjusted if needed.
"""

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "get_market_data",
        "description": (
            "Get current market data including VIX, US 10Y yield, index levels, "
            "commodity prices, and ETF prices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_portfolio_state",
        "description": (
            "Get current portfolio state including account value, cash, "
            "and all positions with their market values and percentages."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_signal_status",
        "description": (
            "Get current signal status including consecutive API failures, "
            "current scenario, last check result, and previous VIX value."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_trade_history",
        "description": "Get recent trade decisions and executed trades.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent records to return (default 20).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "emit_strategy_intent",
        "description": (
            "Emit a strategy intent with your recommended scenario and target allocation. "
            "This is the ONLY way to communicate your trading decision."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Unique identifier for this run (provided in context).",
                },
                "scenario": {
                    "type": "string",
                    "description": "Selected scenario name (e.g. 'base', 'bull', 'bear', 'tail_risk').",
                },
                "rationale": {
                    "type": "string",
                    "description": "Explanation of why this scenario was selected.",
                },
                "target_allocation": {
                    "type": "object",
                    "description": "Target allocation as {symbol: percentage}. Must sum to ~100%.",
                    "additionalProperties": {"type": "number"},
                },
                "priority_actions": {
                    "type": "array",
                    "description": "List of priority actions with symbol, action, and reason.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string"},
                            "action": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                    },
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence level in the decision.",
                },
                "blog_reference": {
                    "type": "string",
                    "description": "Date of the blog being referenced (YYYY-MM-DD).",
                },
            },
            "required": [
                "run_id",
                "scenario",
                "rationale",
                "target_allocation",
                "confidence",
                "blog_reference",
            ],
        },
    },
    {
        "name": "get_etf_prices",
        "description": "Get latest prices for specific ETF symbols.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ETF symbols to get prices for.",
                },
            },
            "required": ["symbols"],
        },
    },
]

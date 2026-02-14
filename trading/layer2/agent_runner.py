"""Claude SDK agent runner for Layer 2."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from trading.config import TradingConfig
from trading.data.database import Database
from trading.data.models import MarketData, Portfolio, StrategyIntent, StrategySpec
from trading.layer2.system_prompt import SYSTEM_PROMPT, TOOL_DEFINITIONS
from trading.layer2.tools.strategy_intent import parse_strategy_intent

logger = logging.getLogger(__name__)


class AgentRunner:
    """Runs the Claude agent to interpret strategy and emit intent.

    This runner constructs the prompt context, invokes the Claude SDK,
    and extracts the strategy intent from tool calls in the response.
    """

    def __init__(self, config: TradingConfig, db: Database) -> None:
        self._config = config
        self._db = db

    def run(
        self,
        trigger_reason: str,
        market_data: MarketData,
        portfolio: Portfolio,
        strategy_spec: StrategySpec,
    ) -> Optional[StrategyIntent]:
        """Run the Claude agent and return the emitted strategy intent.

        Parameters
        ----------
        trigger_reason:
            Why this run was triggered (e.g. "vix_spike", "daily_check").
        market_data:
            Current market data snapshot.
        portfolio:
            Current portfolio state.
        strategy_spec:
            Parsed strategy from the blog.

        Returns
        -------
        Optional[StrategyIntent]
            The strategy intent emitted by Claude, or None on error.
        """
        run_id = self._generate_run_id()
        user_message = self._build_user_message(
            run_id, trigger_reason, market_data, portfolio, strategy_spec
        )

        logger.info("Starting agent run %s (trigger: %s)", run_id, trigger_reason)

        try:
            # Call Claude SDK and extract tool calls
            tool_calls = self._invoke_claude(user_message)
            return self._extract_intent(tool_calls)
        except Exception:
            logger.exception("Agent run %s failed", run_id)
            return None

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        return uuid.uuid4().hex[:12]

    def _build_user_message(
        self,
        run_id: str,
        trigger_reason: str,
        market_data: MarketData,
        portfolio: Portfolio,
        strategy_spec: StrategySpec,
    ) -> str:
        """Build the user message with all context for Claude."""
        # Market data summary
        market_section = (
            f"VIX: {market_data.vix}\n"
            f"US 10Y: {market_data.us10y}\n"
            f"S&P 500: {market_data.sp500}\n"
            f"Nasdaq: {market_data.nasdaq}\n"
            f"Dow: {market_data.dow}\n"
            f"Gold: {market_data.gold}\n"
            f"Oil: {market_data.oil}\n"
            f"Copper: {market_data.copper}\n"
        )
        if market_data.etf_prices:
            etf_lines = [f"  {s}: ${p:.2f}" for s, p in sorted(market_data.etf_prices.items())]
            market_section += "ETF Prices:\n" + "\n".join(etf_lines) + "\n"

        # Portfolio summary
        portfolio_section = (
            f"Account Value: ${portfolio.account_value:,.2f}\n"
            f"Cash: ${portfolio.cash:,.2f}\n"
        )
        if portfolio.positions:
            portfolio_section += "Positions:\n"
            for sym, pos in sorted(portfolio.positions.items()):
                pct = portfolio.get_position_pct(sym)
                portfolio_section += (
                    f"  {sym}: {pos.shares:.4f} shares, "
                    f"${pos.market_value:,.2f} ({pct:.1f}%)\n"
                )

        # Strategy spec summary
        scenarios_section = ""
        for name, sc in strategy_spec.scenarios.items():
            alloc_str = ", ".join(f"{s}: {p}%" for s, p in sorted(sc.allocation.items()))
            triggers_str = "; ".join(sc.triggers) if sc.triggers else "none"
            scenarios_section += (
                f"  {name} ({sc.probability}%): [{alloc_str}] "
                f"Triggers: {triggers_str}\n"
            )

        strategy_section = (
            f"Blog Date: {strategy_spec.blog_date}\n"
            f"Current Allocation: {strategy_spec.current_allocation}\n"
            f"VIX Triggers: {strategy_spec.vix_triggers}\n"
            f"Yield Triggers: {strategy_spec.yield_triggers}\n"
            f"Breadth 200MA: {strategy_spec.breadth_200ma}\n"
            f"Uptrend Ratio: {strategy_spec.uptrend_ratio}\n"
            f"Bubble Score: {strategy_spec.bubble_score}/{strategy_spec.bubble_max}\n"
            f"Pre-event Dates: {strategy_spec.pre_event_dates}\n"
            f"Scenarios:\n{scenarios_section}"
        )

        return (
            f"=== TRADING SYSTEM RUN ===\n"
            f"Run ID: {run_id}\n"
            f"Trigger: {trigger_reason}\n\n"
            f"--- MARKET DATA ---\n{market_section}\n"
            f"--- PORTFOLIO ---\n{portfolio_section}\n"
            f"--- STRATEGY ---\n{strategy_section}\n"
            f"Please analyze the above data, select the appropriate scenario, "
            f"and emit your strategy_intent using the emit_strategy_intent tool. "
            f"Use run_id='{run_id}' and blog_reference='{strategy_spec.blog_date}'."
        )

    def _invoke_claude(self, user_message: str) -> list[dict]:
        """Invoke Claude SDK and return tool call results.

        Uses the Anthropic Messages API with tool use. Gracefully degrades
        to empty tool calls when the SDK is not installed or the API key
        is not configured.
        """
        try:
            import anthropic
        except ImportError:
            logger.warning(
                "anthropic SDK not installed — returning empty tool calls. "
                "Run: pip install 'anthropic>=0.40'"
            )
            return []

        try:
            client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=self._convert_tools(TOOL_DEFINITIONS),
                messages=[{"role": "user", "content": user_message}],
            )
            tool_calls = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append({
                        "name": block.name,
                        "input": block.input,
                    })
            return tool_calls
        except anthropic.AuthenticationError:
            logger.warning(
                "ANTHROPIC_API_KEY not set or invalid — returning empty tool calls."
            )
            return []

    @staticmethod
    def _convert_tools(tool_defs: list[dict]) -> list[dict]:
        """Convert internal tool definitions to Anthropic API format.

        The Anthropic API expects each tool to have 'name', 'description',
        and 'input_schema' keys. Our internal format already matches this,
        but this method ensures compatibility and filters out any extra keys.
        """
        converted = []
        for tool in tool_defs:
            converted.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"],
            })
        return converted

    def _extract_intent(self, tool_calls: list[dict]) -> Optional[StrategyIntent]:
        """Extract StrategyIntent from Claude's tool calls.

        Parameters
        ----------
        tool_calls:
            List of tool call dicts with 'name' and 'input' keys.

        Returns
        -------
        Optional[StrategyIntent]
            Parsed intent if emit_strategy_intent was called, else None.
        """
        for call in tool_calls:
            if call.get("name") == "emit_strategy_intent":
                raw_input = call.get("input", {})
                try:
                    intent = parse_strategy_intent(raw_input)
                    logger.info(
                        "Agent emitted intent: scenario=%s, confidence=%s",
                        intent.scenario,
                        intent.confidence,
                    )
                    return intent
                except ValueError as exc:
                    logger.error("Invalid strategy intent from Claude: %s", exc)
                    return None

        logger.warning("Claude did not emit strategy_intent in this run")
        return None

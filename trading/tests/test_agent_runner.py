"""Tests for the AgentRunner (F1 — Claude SDK integration).

Covers: _invoke_claude normal/error paths, run() end-to-end,
_build_user_message format, _extract_intent parsing, _convert_tools.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from trading.config import TradingConfig
from trading.data.models import (
    MarketData,
    Portfolio,
    Position,
    ScenarioSpec,
    StrategyIntent,
    StrategySpec,
)
from trading.layer2.agent_runner import AgentRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config() -> TradingConfig:
    return TradingConfig(dry_run=True)


def _make_market_data() -> MarketData:
    return MarketData(
        timestamp=datetime.now(timezone.utc),
        vix=20.5,
        us10y=4.36,
        sp500=6828.0,
        nasdaq=21700.0,
        dow=44500.0,
        gold=5046.0,
        oil=62.8,
        copper=5.8,
        etf_prices={"SPY": 683.1, "QQQ": 531.2},
    )


def _make_portfolio() -> Portfolio:
    return Portfolio(
        account_value=100000,
        cash=28000,
        positions={
            "SPY": Position("SPY", 32.2, 22000, 20000, 683.1),
        },
    )


def _make_strategy() -> StrategySpec:
    return StrategySpec(
        blog_date="2026-02-16",
        current_allocation={"SPY": 50.0, "BIL": 50.0},
        scenarios={
            "base": ScenarioSpec(
                name="base", probability=60, triggers=[],
                allocation={"SPY": 50.0, "BIL": 50.0},
            ),
        },
        trading_levels={},
        stop_losses={},
        vix_triggers={"caution": 20.0},
        yield_triggers={"warning": 4.36},
    )


def _mock_tool_use_block(name: str, input_data: dict):
    """Create a mock content block that looks like a tool_use block."""
    block = SimpleNamespace()
    block.type = "tool_use"
    block.name = name
    block.input = input_data
    return block


def _mock_text_block(text: str):
    """Create a mock content block that looks like a text block."""
    block = SimpleNamespace()
    block.type = "text"
    block.text = text
    return block


# ---------------------------------------------------------------------------
# Tests — _invoke_claude
# ---------------------------------------------------------------------------


class TestInvokeClaude:
    """Tests for the _invoke_claude method."""

    @patch("trading.layer2.agent_runner.TOOL_DEFINITIONS", [])
    def test_invoke_claude_returns_tool_calls(self, tmp_db):
        """Normal response with tool_use blocks returns extracted tool_calls."""
        runner = AgentRunner(_make_config(), tmp_db)

        mock_response = SimpleNamespace(
            content=[
                _mock_text_block("Analyzing the data..."),
                _mock_tool_use_block("emit_strategy_intent", {
                    "run_id": "abc123",
                    "scenario": "base",
                    "rationale": "VIX stable",
                    "target_allocation": {"SPY": 50.0, "BIL": 50.0},
                    "confidence": "medium",
                    "blog_reference": "2026-02-16",
                }),
            ]
        )

        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            result = runner._invoke_claude("test message")

        assert len(result) == 1
        assert result[0]["name"] == "emit_strategy_intent"
        assert result[0]["input"]["scenario"] == "base"

    def test_invoke_claude_no_api_key(self, tmp_db):
        """When ANTHROPIC_API_KEY is missing, returns empty list gracefully."""
        runner = AgentRunner(_make_config(), tmp_db)

        import anthropic
        with patch("anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.side_effect = (
                anthropic.AuthenticationError(
                    message="Invalid API key",
                    response=MagicMock(status_code=401),
                    body=None,
                )
            )

            result = runner._invoke_claude("test message")

        assert result == []

    def test_invoke_claude_sdk_not_installed(self, tmp_db):
        """When anthropic package is not installed, returns empty list."""
        runner = AgentRunner(_make_config(), tmp_db)

        with patch.dict("sys.modules", {"anthropic": None}):
            result = runner._invoke_claude("test message")

        assert result == []


# ---------------------------------------------------------------------------
# Tests — run
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for the run() method end-to-end."""

    def test_run_returns_intent_on_success(self, tmp_db):
        """run() returns a StrategyIntent when Claude emits emit_strategy_intent."""
        runner = AgentRunner(_make_config(), tmp_db)

        tool_calls = [{
            "name": "emit_strategy_intent",
            "input": {
                "run_id": "test123",
                "scenario": "base",
                "rationale": "All signals normal",
                "target_allocation": {"SPY": 50.0, "BIL": 50.0},
                "confidence": "medium",
                "blog_reference": "2026-02-16",
            },
        }]

        with patch.object(runner, "_invoke_claude", return_value=tool_calls):
            result = runner.run(
                trigger_reason="daily_check",
                market_data=_make_market_data(),
                portfolio=_make_portfolio(),
                strategy_spec=_make_strategy(),
            )

        assert result is not None
        assert isinstance(result, StrategyIntent)
        assert result.scenario == "base"
        assert result.confidence == "medium"

    def test_run_returns_none_on_no_tool_call(self, tmp_db):
        """run() returns None when Claude does not emit any tool call."""
        runner = AgentRunner(_make_config(), tmp_db)

        with patch.object(runner, "_invoke_claude", return_value=[]):
            result = runner.run(
                trigger_reason="daily_check",
                market_data=_make_market_data(),
                portfolio=_make_portfolio(),
                strategy_spec=_make_strategy(),
            )

        assert result is None


# ---------------------------------------------------------------------------
# Tests — _build_user_message
# ---------------------------------------------------------------------------


class TestBuildUserMessage:
    """Tests for _build_user_message format."""

    def test_build_user_message_format(self, tmp_db):
        """User message contains market data, portfolio, and strategy sections."""
        runner = AgentRunner(_make_config(), tmp_db)

        msg = runner._build_user_message(
            run_id="msg_test_001",
            trigger_reason="vix_spike",
            market_data=_make_market_data(),
            portfolio=_make_portfolio(),
            strategy_spec=_make_strategy(),
        )

        assert "msg_test_001" in msg
        assert "vix_spike" in msg
        assert "VIX: 20.5" in msg
        assert "S&P 500: 6828.0" in msg
        assert "Account Value: $100,000.00" in msg
        assert "Blog Date: 2026-02-16" in msg
        assert "SPY" in msg


# ---------------------------------------------------------------------------
# Tests — _extract_intent
# ---------------------------------------------------------------------------


class TestExtractIntent:
    """Tests for _extract_intent parsing."""

    def test_extract_intent_parses_correctly(self, tmp_db):
        """emit_strategy_intent input is correctly parsed to StrategyIntent."""
        runner = AgentRunner(_make_config(), tmp_db)

        tool_calls = [{
            "name": "emit_strategy_intent",
            "input": {
                "run_id": "parse_test",
                "scenario": "bear",
                "rationale": "VIX rising above 23",
                "target_allocation": {
                    "SPY": 15.0, "QQQ": 5.0, "GLD": 15.0,
                    "XLV": 15.0, "BIL": 50.0,
                },
                "confidence": "high",
                "blog_reference": "2026-02-16",
            },
        }]

        result = runner._extract_intent(tool_calls)

        assert result is not None
        assert result.scenario == "bear"
        assert result.confidence == "high"
        assert result.target_allocation["BIL"] == 50.0

    def test_extract_intent_invalid_input(self, tmp_db):
        """Invalid emit_strategy_intent input returns None."""
        runner = AgentRunner(_make_config(), tmp_db)

        tool_calls = [{
            "name": "emit_strategy_intent",
            "input": {
                # Missing required fields
                "scenario": "invalid_scenario",
            },
        }]

        result = runner._extract_intent(tool_calls)
        assert result is None


# ---------------------------------------------------------------------------
# Tests — _convert_tools
# ---------------------------------------------------------------------------


class TestConvertTools:
    """Tests for _convert_tools static method."""

    def test_convert_tools_extracts_required_keys(self):
        """_convert_tools extracts name, description, input_schema."""
        tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "input_schema": {"type": "object", "properties": {}},
                "extra_key": "should be dropped",
            },
        ]

        result = AgentRunner._convert_tools(tools)

        assert len(result) == 1
        assert result[0]["name"] == "test_tool"
        assert result[0]["description"] == "A test tool"
        assert "extra_key" not in result[0]

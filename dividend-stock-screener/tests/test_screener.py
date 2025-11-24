"""Tests for screener module - TDD approach."""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestRSICalculation:
    """Test RSI calculation logic."""

    def test_rsi_returns_value_between_0_and_100(self):
        """RSI should always be between 0 and 100."""
        from screener import calculate_rsi

        # Sample price data with gains and losses
        prices = [44, 44.5, 44.2, 43.8, 44.3, 44.8, 45.2, 45.0,
                  44.7, 45.1, 45.5, 45.3, 45.8, 46.0, 45.7]

        result = calculate_rsi(prices)

        assert 0 <= result <= 100

    def test_rsi_returns_none_for_insufficient_data(self):
        """RSI needs at least 15 prices (14 periods)."""
        from screener import calculate_rsi

        prices = [44, 45, 46]  # Only 3 prices

        result = calculate_rsi(prices)

        assert result is None

    def test_rsi_below_40_is_oversold(self):
        """RSI <= 40 should be identified as oversold."""
        from screener import is_oversold

        assert is_oversold(30) is True
        assert is_oversold(40) is True
        assert is_oversold(41) is False
        assert is_oversold(50) is False


class TestDividendGrowthScreening:
    """Test dividend growth pullback screening criteria."""

    def test_qualifies_dividend_growth_with_valid_stock(self):
        """Stock meeting all criteria should qualify."""
        from screener import qualifies_dividend_growth_pullback

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 2.0,
            'dividend_cagr_3y': 15.0,
            'rsi': 35,
            'market_cap': 5_000_000_000,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
            'debt_to_equity': 1.5,
        }

        result = qualifies_dividend_growth_pullback(stock)

        assert result is True

    def test_rejects_low_dividend_growth(self):
        """Stock with dividend growth < 12% should not qualify."""
        from screener import qualifies_dividend_growth_pullback

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 2.0,
            'dividend_cagr_3y': 8.0,  # Below 12% threshold
            'rsi': 35,
            'market_cap': 5_000_000_000,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
            'debt_to_equity': 1.5,
        }

        result = qualifies_dividend_growth_pullback(stock)

        assert result is False

    def test_rejects_high_rsi(self):
        """Stock with RSI > 40 should not qualify."""
        from screener import qualifies_dividend_growth_pullback

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 2.0,
            'dividend_cagr_3y': 15.0,
            'rsi': 55,  # Above 40 threshold
            'market_cap': 5_000_000_000,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
            'debt_to_equity': 1.5,
        }

        result = qualifies_dividend_growth_pullback(stock)

        assert result is False

    def test_rejects_low_yield(self):
        """Stock with yield < 1.5% should not qualify."""
        from screener import qualifies_dividend_growth_pullback

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 1.0,  # Below 1.5% threshold
            'dividend_cagr_3y': 15.0,
            'rsi': 35,
            'market_cap': 5_000_000_000,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
            'debt_to_equity': 1.5,
        }

        result = qualifies_dividend_growth_pullback(stock)

        assert result is False


class TestValueDividendScreening:
    """Test value dividend screening criteria."""

    def test_qualifies_value_dividend_with_valid_stock(self):
        """Stock meeting all value criteria should qualify."""
        from screener import qualifies_value_dividend

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 4.0,
            'pe_ratio': 15,
            'pb_ratio': 1.5,
            'rsi': 38,
            'dividend_cagr_3y': 7.0,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
        }

        result = qualifies_value_dividend(stock)

        assert result is True

    def test_rejects_high_pe(self):
        """Stock with P/E > 20 should not qualify."""
        from screener import qualifies_value_dividend

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 4.0,
            'pe_ratio': 25,  # Above 20 threshold
            'pb_ratio': 1.5,
            'rsi': 38,
            'dividend_cagr_3y': 7.0,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
        }

        result = qualifies_value_dividend(stock)

        assert result is False

    def test_rejects_high_pb(self):
        """Stock with P/B > 2 should not qualify."""
        from screener import qualifies_value_dividend

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 4.0,
            'pe_ratio': 15,
            'pb_ratio': 2.5,  # Above 2 threshold
            'rsi': 38,
            'dividend_cagr_3y': 7.0,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
        }

        result = qualifies_value_dividend(stock)

        assert result is False

    def test_rejects_low_yield(self):
        """Stock with yield < 3% should not qualify."""
        from screener import qualifies_value_dividend

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 2.5,  # Below 3% threshold
            'pe_ratio': 15,
            'pb_ratio': 1.5,
            'rsi': 38,
            'dividend_cagr_3y': 7.0,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
        }

        result = qualifies_value_dividend(stock)

        assert result is False

    def test_rejects_high_rsi(self):
        """Stock with RSI > 40 should not qualify."""
        from screener import qualifies_value_dividend

        stock = {
            'symbol': 'TEST',
            'dividend_yield': 4.0,
            'pe_ratio': 15,
            'pb_ratio': 1.5,
            'rsi': 50,  # Above 40 threshold
            'dividend_cagr_3y': 7.0,
            'revenue_growth_positive': True,
            'eps_growth_positive': True,
        }

        result = qualifies_value_dividend(stock)

        assert result is False


class TestScreenerIntegration:
    """Integration tests for the screener."""

    def test_run_screening_returns_both_sections(self):
        """run_screening should return results for both strategies."""
        from screener import run_screening

        # Mock the API calls
        with patch('screener.fetch_dividend_growth_candidates') as mock_growth, \
             patch('screener.fetch_value_dividend_candidates') as mock_value:

            mock_growth.return_value = [
                {'symbol': 'GROW1', 'dividend_yield': 2.0, 'dividend_cagr_3y': 15.0,
                 'rsi': 35, 'market_cap': 5e9, 'revenue_growth_positive': True,
                 'eps_growth_positive': True, 'debt_to_equity': 1.0}
            ]
            mock_value.return_value = [
                {'symbol': 'VAL1', 'dividend_yield': 4.0, 'pe_ratio': 12,
                 'pb_ratio': 1.2, 'rsi': 38, 'dividend_cagr_3y': 6.0,
                 'revenue_growth_positive': True, 'eps_growth_positive': True}
            ]

            result = run_screening()

            assert 'dividend_growth_pullback' in result
            assert 'value_dividend' in result
            assert len(result['dividend_growth_pullback']) == 1
            assert len(result['value_dividend']) == 1

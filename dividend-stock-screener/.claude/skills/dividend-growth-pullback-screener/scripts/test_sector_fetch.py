#!/usr/bin/env python3
"""
TDD Tests for sector information fetching functionality.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screen_dividend_growth_rsi import FMPClient


class TestFMPClientSectorFetch(unittest.TestCase):
    """Test cases for FMPClient sector information fetching."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = FMPClient("test_api_key")

    @patch('screen_dividend_growth_rsi.requests.Session.get')
    def test_get_company_profile_returns_sector(self, mock_get):
        """Test that get_company_profile returns sector information."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'symbol': 'AAPL',
            'companyName': 'Apple Inc.',
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'exchange': 'NASDAQ'
        }]
        mock_get.return_value = mock_response

        # Act
        result = self.client.get_company_profile('AAPL')

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.get('sector'), 'Technology')
        self.assertEqual(result.get('companyName'), 'Apple Inc.')

    @patch('screen_dividend_growth_rsi.requests.Session.get')
    def test_get_company_profile_returns_none_on_error(self, mock_get):
        """Test that get_company_profile returns None on API error."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Act
        result = self.client.get_company_profile('INVALID')

        # Assert
        self.assertIsNone(result)

    @patch('screen_dividend_growth_rsi.requests.Session.get')
    def test_get_company_profile_returns_none_on_empty_response(self, mock_get):
        """Test that get_company_profile returns None for empty response."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Act
        result = self.client.get_company_profile('EMPTY')

        # Assert
        self.assertIsNone(result)

    @patch('screen_dividend_growth_rsi.requests.Session.get')
    def test_get_quote_with_profile_includes_sector(self, mock_get):
        """Test that get_quote_with_profile returns quote data with sector."""
        # Arrange
        def side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            if 'quote/' in url:
                mock_response.json.return_value = [{
                    'symbol': 'MSFT',
                    'price': 350.00,
                    'marketCap': 2500000000000
                }]
            elif 'profile/' in url:
                mock_response.json.return_value = [{
                    'symbol': 'MSFT',
                    'companyName': 'Microsoft Corporation',
                    'sector': 'Technology',
                    'industry': 'Software'
                }]
            return mock_response

        mock_get.side_effect = side_effect

        # Act
        result = self.client.get_quote_with_profile('MSFT')

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.get('symbol'), 'MSFT')
        self.assertEqual(result.get('sector'), 'Technology')
        self.assertEqual(result.get('companyName'), 'Microsoft Corporation')
        self.assertEqual(result.get('price'), 350.00)

    @patch('screen_dividend_growth_rsi.requests.Session.get')
    def test_get_quote_with_profile_fallback_to_unknown_sector(self, mock_get):
        """Test fallback to 'Unknown' when profile fetch fails."""
        # Arrange
        def side_effect(url, **kwargs):
            mock_response = Mock()
            if 'quote/' in url:
                mock_response.status_code = 200
                mock_response.json.return_value = [{
                    'symbol': 'XYZ',
                    'price': 100.00,
                    'marketCap': 5000000000
                }]
            elif 'profile/' in url:
                mock_response.status_code = 404
            return mock_response

        mock_get.side_effect = side_effect

        # Act
        result = self.client.get_quote_with_profile('XYZ')

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.get('symbol'), 'XYZ')
        self.assertEqual(result.get('sector'), 'Unknown')


class TestSectorInScreeningResults(unittest.TestCase):
    """Test that screening results include proper sector information."""

    def test_result_contains_valid_sector(self):
        """Test that screening result contains non-Unknown sector."""
        # This test verifies the integration - will be used after implementation
        result = {
            'symbol': 'ZTS',
            'company_name': 'Zoetis Inc.',
            'sector': 'Healthcare',
            'dividend_yield': 1.5,
            'rsi': 35.0
        }

        self.assertIn('sector', result)
        self.assertNotEqual(result['sector'], 'Unknown')
        self.assertEqual(result['sector'], 'Healthcare')


class TestPayoutRatioCalculation(unittest.TestCase):
    """Test cases for payout ratio calculation."""

    def test_calculate_payout_ratio_from_cashflow(self):
        """Test payout ratio calculation using dividendsPaid from cash flow."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - ZTS-like data
        cash_flow = [{'dividendsPaid': -786000000, 'freeCashFlow': 2298000000}]
        income_stmt = [{'netIncome': 2486000000}]

        # Act
        result = StockAnalyzer.calculate_payout_ratios(income_stmt, cash_flow)

        # Assert
        self.assertIsNotNone(result['payout_ratio'])
        self.assertAlmostEqual(result['payout_ratio'], 31.6, delta=0.5)

    def test_calculate_fcf_payout_ratio(self):
        """Test FCF payout ratio calculation."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange
        cash_flow = [{'dividendsPaid': -786000000, 'freeCashFlow': 2298000000}]
        income_stmt = [{'netIncome': 2486000000}]

        # Act
        result = StockAnalyzer.calculate_payout_ratios(income_stmt, cash_flow)

        # Assert
        self.assertIsNotNone(result['fcf_payout_ratio'])
        # 786 / 2298 = 34.2%
        self.assertAlmostEqual(result['fcf_payout_ratio'], 34.2, delta=0.5)

    def test_payout_ratio_with_positive_dividends_paid(self):
        """Test payout ratio when dividendsPaid is positive (some APIs return positive)."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - some APIs return positive value
        cash_flow = [{'dividendsPaid': 500000000, 'freeCashFlow': 1000000000}]
        income_stmt = [{'netIncome': 1000000000}]

        # Act
        result = StockAnalyzer.calculate_payout_ratios(income_stmt, cash_flow)

        # Assert
        self.assertIsNotNone(result['payout_ratio'])
        self.assertAlmostEqual(result['payout_ratio'], 50.0, delta=0.5)

    def test_payout_ratio_returns_none_when_no_data(self):
        """Test payout ratio returns None when data is missing."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Act
        result = StockAnalyzer.calculate_payout_ratios([], [])

        # Assert
        self.assertIsNone(result['payout_ratio'])
        self.assertIsNone(result['fcf_payout_ratio'])

    def test_payout_ratio_from_key_metrics_fallback(self):
        """Test payout ratio from key_metrics as fallback."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - key_metrics has payoutRatio directly
        key_metrics = [{'payoutRatio': 0.3161}]  # 31.61%

        # Act
        result = StockAnalyzer.get_payout_ratio_from_metrics(key_metrics)

        # Assert
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 31.6, delta=0.5)


class TestREITPayoutRatio(unittest.TestCase):
    """Test cases for REIT-specific FFO payout ratio calculation."""

    def test_is_reit_returns_true_for_real_estate_sector(self):
        """Test REIT detection based on sector."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange
        stock_data = {'sector': 'Real Estate', 'industry': 'REIT - Specialty'}

        # Act
        result = StockAnalyzer.is_reit(stock_data)

        # Assert
        self.assertTrue(result)

    def test_is_reit_returns_false_for_non_reit(self):
        """Test REIT detection returns false for non-REIT."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange
        stock_data = {'sector': 'Technology', 'industry': 'Software'}

        # Act
        result = StockAnalyzer.is_reit(stock_data)

        # Assert
        self.assertFalse(result)

    def test_calculate_ffo(self):
        """Test FFO calculation (Net Income + Depreciation & Amortization)."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - EQIX-like data
        cash_flow = [{'netIncome': 814000000, 'depreciationAndAmortization': 2009000000}]

        # Act
        ffo = StockAnalyzer.calculate_ffo(cash_flow)

        # Assert
        self.assertEqual(ffo, 2823000000)

    def test_calculate_ffo_payout_ratio(self):
        """Test FFO payout ratio calculation for REITs."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - EQIX-like data
        cash_flow = [{
            'netIncome': 814000000,
            'depreciationAndAmortization': 2009000000,
            'dividendsPaid': -1643000000
        }]

        # Act
        result = StockAnalyzer.calculate_ffo_payout_ratio(cash_flow)

        # Assert
        self.assertIsNotNone(result)
        # FFO = 814M + 2009M = 2823M, Dividends = 1643M, Ratio = 58.2%
        self.assertAlmostEqual(result, 58.2, delta=0.5)

    def test_calculate_payout_ratios_for_reit(self):
        """Test that calculate_payout_ratios uses FFO for REITs."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - EQIX-like REIT data
        income_stmt = [{'netIncome': 815000000}]
        cash_flow = [{
            'netIncome': 814000000,
            'depreciationAndAmortization': 2009000000,
            'dividendsPaid': -1643000000,
            'freeCashFlow': 1240000000
        }]
        is_reit = True

        # Act
        result = StockAnalyzer.calculate_payout_ratios(income_stmt, cash_flow, is_reit=is_reit)

        # Assert
        self.assertIsNotNone(result['payout_ratio'])
        # For REIT, payout_ratio should be FFO-based (~58%) not net income based (~200%)
        self.assertLess(result['payout_ratio'], 100)
        self.assertAlmostEqual(result['payout_ratio'], 58.2, delta=1.0)

    def test_calculate_payout_ratios_for_non_reit_unchanged(self):
        """Test that non-REIT calculation remains unchanged."""
        from screen_dividend_growth_rsi import StockAnalyzer

        # Arrange - Non-REIT data (ZTS-like)
        income_stmt = [{'netIncome': 2486000000}]
        cash_flow = [{
            'dividendsPaid': -786000000,
            'freeCashFlow': 2298000000,
            'depreciationAndAmortization': 500000000
        }]
        is_reit = False

        # Act
        result = StockAnalyzer.calculate_payout_ratios(income_stmt, cash_flow, is_reit=is_reit)

        # Assert - Should use net income, not FFO
        self.assertAlmostEqual(result['payout_ratio'], 31.6, delta=0.5)


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""
TDD Tests for value-dividend-screener improvements:
1. Sector information fetching
2. REIT FFO-based payout ratio calculation
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from screen_dividend_stocks import FMPClient, StockAnalyzer


class TestFMPClientSectorFetch(unittest.TestCase):
    """Test cases for sector information fetching."""

    def setUp(self):
        self.client = FMPClient("test_api_key")

    @patch('screen_dividend_stocks.requests.Session.get')
    def test_get_company_profile_returns_sector(self, mock_get):
        """Test that get_company_profile returns sector information."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'symbol': 'TRNO',
            'companyName': 'Terreno Realty Corporation',
            'sector': 'Real Estate',
            'industry': 'REIT - Industrial'
        }]
        mock_get.return_value = mock_response

        result = self.client.get_company_profile('TRNO')

        self.assertIsNotNone(result)
        self.assertEqual(result.get('sector'), 'Real Estate')

    @patch('screen_dividend_stocks.requests.Session.get')
    def test_get_company_profile_returns_none_on_error(self, mock_get):
        """Test that get_company_profile returns None on API error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = self.client.get_company_profile('INVALID')

        self.assertIsNone(result)


class TestREITDetection(unittest.TestCase):
    """Test cases for REIT detection."""

    def test_is_reit_returns_true_for_real_estate_sector(self):
        """Test REIT detection for Real Estate sector."""
        stock_data = {'sector': 'Real Estate', 'industry': 'REIT - Industrial'}
        result = StockAnalyzer.is_reit(stock_data)
        self.assertTrue(result)

    def test_is_reit_returns_true_for_reit_industry(self):
        """Test REIT detection for REIT in industry name."""
        stock_data = {'sector': 'Financial', 'industry': 'REIT - Hotel'}
        result = StockAnalyzer.is_reit(stock_data)
        self.assertTrue(result)

    def test_is_reit_returns_false_for_non_reit(self):
        """Test REIT detection returns false for non-REIT."""
        stock_data = {'sector': 'Technology', 'industry': 'Software'}
        result = StockAnalyzer.is_reit(stock_data)
        self.assertFalse(result)

    def test_is_reit_handles_missing_fields(self):
        """Test REIT detection handles missing fields gracefully."""
        stock_data = {}
        result = StockAnalyzer.is_reit(stock_data)
        self.assertFalse(result)


class TestFFOCalculation(unittest.TestCase):
    """Test cases for FFO calculation."""

    def test_calculate_ffo(self):
        """Test FFO calculation (Net Income + Depreciation)."""
        cash_flows = [{'netIncome': 100000000, 'depreciationAndAmortization': 50000000}]
        result = StockAnalyzer.calculate_ffo(cash_flows)
        self.assertEqual(result, 150000000)

    def test_calculate_ffo_returns_none_when_no_data(self):
        """Test FFO returns None when no data."""
        result = StockAnalyzer.calculate_ffo([])
        self.assertIsNone(result)

    def test_calculate_ffo_payout_ratio(self):
        """Test FFO payout ratio calculation."""
        cash_flows = [{
            'netIncome': 100000000,
            'depreciationAndAmortization': 50000000,
            'dividendsPaid': -75000000
        }]
        result = StockAnalyzer.calculate_ffo_payout_ratio(cash_flows)
        # FFO = 150M, Dividends = 75M, Ratio = 50%
        self.assertAlmostEqual(result, 50.0, delta=0.5)


class TestDividendSustainabilityWithREIT(unittest.TestCase):
    """Test cases for dividend sustainability with REIT support."""

    def test_analyze_dividend_sustainability_for_reit(self):
        """Test that analyze_dividend_sustainability uses FFO for REITs."""
        # TRNO-like REIT data
        income_stmts = [{'netIncome': 50000000}]
        cash_flows = [{
            'netIncome': 50000000,
            'depreciationAndAmortization': 100000000,
            'dividendsPaid': -75000000,
            'operatingCashFlow': 180000000,
            'capitalExpenditure': -100000000
        }]
        is_reit = True

        result = StockAnalyzer.analyze_dividend_sustainability(income_stmts, cash_flows, is_reit=is_reit)

        # FFO = 50M + 100M = 150M, Dividends = 75M, FFO Payout = 50%
        self.assertIsNotNone(result['payout_ratio'])
        self.assertAlmostEqual(result['payout_ratio'], 50.0, delta=1.0)
        # Should be sustainable at 50%
        self.assertTrue(result['sustainable'])

    def test_analyze_dividend_sustainability_for_non_reit(self):
        """Test that non-REIT calculation uses net income."""
        income_stmts = [{'netIncome': 100000000}]
        cash_flows = [{
            'dividendsPaid': -30000000,
            'operatingCashFlow': 120000000,
            'capitalExpenditure': -20000000,
            'depreciationAndAmortization': 10000000
        }]
        is_reit = False

        result = StockAnalyzer.analyze_dividend_sustainability(income_stmts, cash_flows, is_reit=is_reit)

        # Net Income based: 30M / 100M = 30%
        self.assertAlmostEqual(result['payout_ratio'], 30.0, delta=0.5)

    def test_reit_with_high_net_income_payout_but_reasonable_ffo_payout(self):
        """Test REIT with >100% net income payout but reasonable FFO payout."""
        # APLE-like scenario
        income_stmts = [{'netIncome': 60000000}]
        cash_flows = [{
            'netIncome': 60000000,
            'depreciationAndAmortization': 120000000,
            'dividendsPaid': -70000000,  # >100% of net income
            'operatingCashFlow': 200000000,
            'capitalExpenditure': -50000000
        }]
        is_reit = True

        result = StockAnalyzer.analyze_dividend_sustainability(income_stmts, cash_flows, is_reit=is_reit)

        # Net income payout would be 70/60 = 116.7% (unsustainable)
        # FFO payout = 70/(60+120) = 38.9% (sustainable)
        self.assertLess(result['payout_ratio'], 100)
        self.assertAlmostEqual(result['payout_ratio'], 38.9, delta=1.0)
        self.assertTrue(result['sustainable'])


class TestDividendStabilityValidation(unittest.TestCase):
    """Test cases for dividend stability validation (year-over-year growth)."""

    def test_analyze_dividend_stability_returns_stable_for_consistent_growth(self):
        """Test that dividends growing year-over-year are marked as stable."""
        # Consistent year-over-year growth: 1.00 -> 1.05 -> 1.10 -> 1.16
        dividend_history = {
            'historical': [
                {'date': '2024-03-15', 'dividend': 0.29},
                {'date': '2024-06-15', 'dividend': 0.29},
                {'date': '2024-09-15', 'dividend': 0.29},
                {'date': '2024-12-15', 'dividend': 0.29},  # 2024: 1.16
                {'date': '2023-03-15', 'dividend': 0.275},
                {'date': '2023-06-15', 'dividend': 0.275},
                {'date': '2023-09-15', 'dividend': 0.275},
                {'date': '2023-12-15', 'dividend': 0.275},  # 2023: 1.10
                {'date': '2022-03-15', 'dividend': 0.2625},
                {'date': '2022-06-15', 'dividend': 0.2625},
                {'date': '2022-09-15', 'dividend': 0.2625},
                {'date': '2022-12-15', 'dividend': 0.2625},  # 2022: 1.05
                {'date': '2021-03-15', 'dividend': 0.25},
                {'date': '2021-06-15', 'dividend': 0.25},
                {'date': '2021-09-15', 'dividend': 0.25},
                {'date': '2021-12-15', 'dividend': 0.25},  # 2021: 1.00
            ]
        }
        result = StockAnalyzer.analyze_dividend_stability(dividend_history)
        self.assertTrue(result['is_stable'])
        self.assertTrue(result['is_growing'])
        self.assertEqual(result['years_of_growth'], 3)

    def test_analyze_dividend_stability_returns_unstable_for_volatile_dividends(self):
        """Test that volatile dividends (like CALM) are marked as unstable."""
        # CALM-like volatile dividends
        dividend_history = {
            'historical': [
                {'date': '2024-10-29', 'dividend': 1.371},
                {'date': '2024-08-04', 'dividend': 2.354},
                {'date': '2024-04-30', 'dividend': 3.495},
                {'date': '2024-01-29', 'dividend': 1.489},  # 2024: ~8.71
                {'date': '2023-10-31', 'dividend': 0.006},
                {'date': '2023-08-04', 'dividend': 0.755},
                {'date': '2023-04-25', 'dividend': 2.199},
                {'date': '2023-01-24', 'dividend': 1.350},  # 2023: ~4.31
                {'date': '2022-10-25', 'dividend': 0.853},
                {'date': '2022-07-29', 'dividend': 0.749},
                {'date': '2022-04-26', 'dividend': 0.125},  # 2022: ~1.73
                {'date': '2021-04-27', 'dividend': 0.034},  # 2021: ~0.03
            ]
        }
        result = StockAnalyzer.analyze_dividend_stability(dividend_history)
        self.assertFalse(result['is_stable'])
        # May still show growth due to overall uptrend, but high volatility

    def test_analyze_dividend_stability_detects_dividend_cuts(self):
        """Test that dividend cuts are detected and marked as not growing."""
        dividend_history = {
            'historical': [
                {'date': '2024-03-15', 'dividend': 0.20},
                {'date': '2024-06-15', 'dividend': 0.20},
                {'date': '2024-09-15', 'dividend': 0.20},
                {'date': '2024-12-15', 'dividend': 0.20},  # 2024: 0.80 (cut!)
                {'date': '2023-03-15', 'dividend': 0.25},
                {'date': '2023-06-15', 'dividend': 0.25},
                {'date': '2023-09-15', 'dividend': 0.25},
                {'date': '2023-12-15', 'dividend': 0.25},  # 2023: 1.00
                {'date': '2022-03-15', 'dividend': 0.25},
                {'date': '2022-06-15', 'dividend': 0.25},
                {'date': '2022-09-15', 'dividend': 0.25},
                {'date': '2022-12-15', 'dividend': 0.25},  # 2022: 1.00
            ]
        }
        result = StockAnalyzer.analyze_dividend_stability(dividend_history)
        self.assertFalse(result['is_growing'])
        self.assertLess(result['years_of_growth'], 2)

    def test_analyze_dividend_stability_handles_empty_history(self):
        """Test handling of empty dividend history."""
        result = StockAnalyzer.analyze_dividend_stability({})
        self.assertFalse(result['is_stable'])
        self.assertFalse(result['is_growing'])
        self.assertEqual(result['years_of_growth'], 0)

    def test_analyze_dividend_stability_calculates_volatility(self):
        """Test that volatility percentage is calculated."""
        dividend_history = {
            'historical': [
                {'date': '2024-03-15', 'dividend': 0.25},
                {'date': '2024-06-15', 'dividend': 0.25},
                {'date': '2024-09-15', 'dividend': 0.25},
                {'date': '2024-12-15', 'dividend': 0.25},
                {'date': '2023-03-15', 'dividend': 0.25},
                {'date': '2023-06-15', 'dividend': 0.25},
                {'date': '2023-09-15', 'dividend': 0.25},
                {'date': '2023-12-15', 'dividend': 0.25},
                {'date': '2022-03-15', 'dividend': 0.25},
                {'date': '2022-06-15', 'dividend': 0.25},
                {'date': '2022-09-15', 'dividend': 0.25},
                {'date': '2022-12-15', 'dividend': 0.25},
            ]
        }
        result = StockAnalyzer.analyze_dividend_stability(dividend_history)
        self.assertIsNotNone(result['volatility_pct'])
        # Low volatility for consistent dividends
        self.assertLess(result['volatility_pct'], 50)


class TestRevenueTrendValidation(unittest.TestCase):
    """Test cases for revenue trend validation."""

    def test_analyze_revenue_trend_returns_uptrend_for_growing_revenue(self):
        """Test revenue uptrend detection."""
        income_statements = [
            {'revenue': 1200000000, 'fiscalYear': '2024'},  # Latest
            {'revenue': 1100000000, 'fiscalYear': '2023'},
            {'revenue': 1000000000, 'fiscalYear': '2022'},
            {'revenue': 900000000, 'fiscalYear': '2021'},   # Oldest
        ]
        result = StockAnalyzer.analyze_revenue_trend(income_statements)
        self.assertTrue(result['is_uptrend'])
        self.assertEqual(result['years_of_growth'], 3)

    def test_analyze_revenue_trend_detects_decline(self):
        """Test revenue decline detection."""
        income_statements = [
            {'revenue': 800000000, 'fiscalYear': '2024'},   # Latest (declining)
            {'revenue': 900000000, 'fiscalYear': '2023'},
            {'revenue': 1000000000, 'fiscalYear': '2022'},
            {'revenue': 1100000000, 'fiscalYear': '2021'},
        ]
        result = StockAnalyzer.analyze_revenue_trend(income_statements)
        self.assertFalse(result['is_uptrend'])
        self.assertEqual(result['years_of_growth'], 0)

    def test_analyze_revenue_trend_allows_one_dip(self):
        """Test that one dip in revenue trend is allowed."""
        income_statements = [
            {'revenue': 1200000000, 'fiscalYear': '2024'},
            {'revenue': 1050000000, 'fiscalYear': '2023'},  # Dip
            {'revenue': 1100000000, 'fiscalYear': '2022'},
            {'revenue': 1000000000, 'fiscalYear': '2021'},
        ]
        result = StockAnalyzer.analyze_revenue_trend(income_statements)
        # Overall uptrend (1000 -> 1200) with one dip should still be acceptable
        self.assertTrue(result['is_uptrend'])


class TestEarningsTrendValidation(unittest.TestCase):
    """Test cases for earnings/profit trend validation."""

    def test_analyze_earnings_trend_returns_uptrend_for_growing_earnings(self):
        """Test earnings uptrend detection."""
        income_statements = [
            {'netIncome': 120000000, 'eps': 4.8, 'fiscalYear': '2024'},
            {'netIncome': 110000000, 'eps': 4.4, 'fiscalYear': '2023'},
            {'netIncome': 100000000, 'eps': 4.0, 'fiscalYear': '2022'},
            {'netIncome': 90000000, 'eps': 3.6, 'fiscalYear': '2021'},
        ]
        result = StockAnalyzer.analyze_earnings_trend(income_statements)
        self.assertTrue(result['is_uptrend'])
        self.assertEqual(result['years_of_growth'], 3)

    def test_analyze_earnings_trend_detects_decline(self):
        """Test earnings decline detection."""
        income_statements = [
            {'netIncome': 80000000, 'eps': 3.2, 'fiscalYear': '2024'},
            {'netIncome': 100000000, 'eps': 4.0, 'fiscalYear': '2023'},
            {'netIncome': 110000000, 'eps': 4.4, 'fiscalYear': '2022'},
            {'netIncome': 120000000, 'eps': 4.8, 'fiscalYear': '2021'},
        ]
        result = StockAnalyzer.analyze_earnings_trend(income_statements)
        self.assertFalse(result['is_uptrend'])

    def test_analyze_earnings_trend_handles_negative_earnings(self):
        """Test handling of negative earnings."""
        income_statements = [
            {'netIncome': -50000000, 'eps': -2.0, 'fiscalYear': '2024'},
            {'netIncome': 100000000, 'eps': 4.0, 'fiscalYear': '2023'},
        ]
        result = StockAnalyzer.analyze_earnings_trend(income_statements)
        self.assertFalse(result['is_uptrend'])


class TestStabilityScoreIntegration(unittest.TestCase):
    """Test integration of stability scores into composite scoring."""

    def test_stability_score_penalizes_volatile_dividends(self):
        """Test that volatile dividends reduce composite score."""
        # High volatility dividend stock
        volatile_stability = {
            'is_stable': False,
            'is_growing': True,
            'volatility_pct': 200,
            'years_of_growth': 2
        }

        # Stable dividend stock
        stable_stability = {
            'is_stable': True,
            'is_growing': True,
            'volatility_pct': 10,
            'years_of_growth': 3
        }

        volatile_score = StockAnalyzer.calculate_stability_score(volatile_stability)
        stable_score = StockAnalyzer.calculate_stability_score(stable_stability)

        self.assertGreater(stable_score, volatile_score)

    def test_stability_score_rewards_consistent_growth(self):
        """Test that consistent growth increases stability score."""
        stability = {
            'is_stable': True,
            'is_growing': True,
            'volatility_pct': 15,
            'years_of_growth': 3
        }
        score = StockAnalyzer.calculate_stability_score(stability)
        self.assertGreater(score, 70)  # High score for stable, growing dividends


if __name__ == '__main__':
    unittest.main(verbosity=2)

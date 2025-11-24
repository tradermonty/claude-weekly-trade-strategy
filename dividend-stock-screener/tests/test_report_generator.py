"""Tests for HTML report generator module - TDD approach."""
import pytest
from datetime import date
import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestHTMLReportGeneration:
    """Test HTML report generation."""

    def test_generate_html_report_returns_valid_html(self):
        """Generated report should be valid HTML with doctype."""
        from report_generator import generate_html_report

        screening_results = {
            'dividend_growth_pullback': [],
            'value_dividend': [],
        }

        result = generate_html_report(screening_results)

        assert '<!DOCTYPE html>' in result
        assert '<html' in result
        assert '</html>' in result

    def test_report_contains_both_sections(self):
        """Report should have sections for both screening strategies."""
        from report_generator import generate_html_report

        screening_results = {
            'dividend_growth_pullback': [],
            'value_dividend': [],
        }

        result = generate_html_report(screening_results)

        assert 'Dividend Growth Pullback' in result
        assert 'Value Dividend' in result

    def test_report_displays_stock_data(self):
        """Report should display stock information in tables."""
        from report_generator import generate_html_report

        screening_results = {
            'dividend_growth_pullback': [
                {
                    'symbol': 'GROW1',
                    'company_name': 'Growth Corp',
                    'dividend_yield': 2.5,
                    'dividend_cagr_3y': 15.0,
                    'rsi': 35,
                    'price': 100.0,
                }
            ],
            'value_dividend': [
                {
                    'symbol': 'VAL1',
                    'company_name': 'Value Inc',
                    'dividend_yield': 4.5,
                    'pe_ratio': 12,
                    'pb_ratio': 1.5,
                    'rsi': 38,
                    'price': 50.0,
                }
            ],
        }

        result = generate_html_report(screening_results)

        # Check dividend growth section
        assert 'GROW1' in result
        assert 'Growth Corp' in result
        assert '2.5' in result  # yield
        assert '15.0' in result  # CAGR

        # Check value dividend section
        assert 'VAL1' in result
        assert 'Value Inc' in result
        assert '4.5' in result  # yield

    def test_report_includes_date(self):
        """Report should include the generation date."""
        from report_generator import generate_html_report

        screening_results = {
            'dividend_growth_pullback': [],
            'value_dividend': [],
        }

        result = generate_html_report(screening_results)
        today = date.today().strftime('%Y-%m-%d')

        assert today in result

    def test_report_shows_no_stocks_message_when_empty(self):
        """Report should show message when no stocks found."""
        from report_generator import generate_html_report

        screening_results = {
            'dividend_growth_pullback': [],
            'value_dividend': [],
        }

        result = generate_html_report(screening_results)

        assert 'No stocks found' in result or 'No qualifying stocks' in result


class TestReportFileSaving:
    """Test report file operations."""

    def test_save_report_creates_file(self, tmp_path):
        """save_report should create HTML file in reports directory."""
        from report_generator import save_report

        html_content = '<!DOCTYPE html><html><body>Test</body></html>'
        report_date = '2025-11-23'

        filepath = save_report(html_content, report_date, str(tmp_path))

        assert os.path.exists(filepath)
        assert filepath.endswith('.html')
        assert report_date in filepath

    def test_saved_file_contains_content(self, tmp_path):
        """Saved file should contain the HTML content."""
        from report_generator import save_report

        html_content = '<!DOCTYPE html><html><body>Test Content</body></html>'
        report_date = '2025-11-23'

        filepath = save_report(html_content, report_date, str(tmp_path))

        with open(filepath, 'r') as f:
            content = f.read()

        assert 'Test Content' in content


class TestStockRowFormatting:
    """Test individual stock row formatting."""

    def test_format_growth_stock_row(self):
        """Format dividend growth stock for HTML table."""
        from report_generator import format_growth_stock_row

        stock = {
            'symbol': 'TEST',
            'company_name': 'Test Corp',
            'dividend_yield': 2.5,
            'dividend_cagr_3y': 15.0,
            'rsi': 35,
            'price': 100.0,
            'sector': 'Technology',
        }

        result = format_growth_stock_row(stock)

        assert '<tr>' in result
        assert 'TEST' in result
        assert 'Test Corp' in result
        assert '2.5' in result
        assert '35' in result

    def test_format_value_stock_row(self):
        """Format value dividend stock for HTML table."""
        from report_generator import format_value_stock_row

        stock = {
            'symbol': 'TEST',
            'company_name': 'Test Corp',
            'dividend_yield': 4.5,
            'pe_ratio': 12,
            'pb_ratio': 1.5,
            'rsi': 38,
            'price': 50.0,
            'sector': 'Utilities',
        }

        result = format_value_stock_row(stock)

        assert '<tr>' in result
        assert 'TEST' in result
        assert '4.5' in result
        assert '12' in result  # P/E
        assert '38' in result  # RSI


class TestPayoutRatioAndStabilityDisplay:
    """Test payout ratio and dividend stability display in reports."""

    def test_payout_ratio_displays_when_present(self):
        """Payout ratio should display when available in stock data."""
        from report_generator import format_growth_stock_row

        stock = {
            'symbol': 'TEST',
            'company_name': 'Test Corp',
            'dividend_yield': 2.5,
            'dividend_cagr_3y': 15.0,
            'rsi': 35,
            'price': 100.0,
            'sector': 'Technology',
            'payout_ratio': 45.5,
        }

        result = format_growth_stock_row(stock)

        assert '46%' in result or '45%' in result  # Should show payout ratio

    def test_payout_ratio_shows_na_when_missing(self):
        """Payout ratio should show N/A when not available."""
        from report_generator import format_growth_stock_row

        stock = {
            'symbol': 'TEST',
            'company_name': 'Test Corp',
            'dividend_yield': 2.5,
            'dividend_cagr_3y': 15.0,
            'rsi': 35,
            'price': 100.0,
            'sector': 'Technology',
            'payout_ratio': None,
        }

        result = format_growth_stock_row(stock)

        assert 'N/A' in result

    def test_stability_badge_sustainable_when_dividend_sustainable(self):
        """Should show Sustainable badge when dividend_sustainable is True."""
        from report_generator import format_stability_badge

        stock = {
            'dividend_sustainable': True,
            'dividend_consistent': True,
        }

        result = format_stability_badge(stock)

        assert 'Sustainable' in result
        assert '#27ae60' in result  # Green color

    def test_stability_badge_consistent_when_only_consistent(self):
        """Should show Consistent badge when dividend_consistent but not sustainable."""
        from report_generator import format_stability_badge

        stock = {
            'dividend_sustainable': False,
            'dividend_consistent': True,
        }

        result = format_stability_badge(stock)

        assert 'Consistent' in result
        assert '#f39c12' in result  # Orange color

    def test_stability_badge_variable_when_neither(self):
        """Should show Variable badge when neither sustainable nor consistent."""
        from report_generator import format_stability_badge

        stock = {
            'dividend_sustainable': False,
            'dividend_consistent': False,
        }

        result = format_stability_badge(stock)

        assert 'Variable' in result
        assert '#95a5a6' in result  # Grey color

    def test_years_of_growth_displays_correctly(self):
        """Years of dividend growth should display in stability column."""
        from report_generator import format_growth_stock_row

        stock = {
            'symbol': 'TEST',
            'company_name': 'Test Corp',
            'dividend_yield': 2.5,
            'dividend_cagr_3y': 15.0,
            'rsi': 35,
            'price': 100.0,
            'sector': 'Technology',
            'dividend_years_of_growth': 10,
            'dividend_consistent': True,
        }

        result = format_growth_stock_row(stock)

        assert '10Y' in result  # Should show 10 years of growth

    def test_fcf_payout_used_when_payout_ratio_over_100(self):
        """When payout ratio > 100%, FCF payout ratio should be used instead."""
        from report_generator import format_payout_ratio

        # Yieldco/REIT case: high accounting payout, reasonable FCF payout
        payout = 380.0
        fcf_payout = 69.0

        result = format_payout_ratio(payout, fcf_payout)

        assert '69%' in result  # Should show FCF payout
        assert '380' not in result  # Should NOT show the inflated payout ratio

    def test_normal_payout_ratio_displayed_when_under_100(self):
        """When payout ratio <= 100%, normal payout ratio should be displayed."""
        from report_generator import format_payout_ratio

        payout = 45.0
        fcf_payout = 50.0

        result = format_payout_ratio(payout, fcf_payout)

        assert '45%' in result  # Should show normal payout ratio

    def test_fcf_payout_used_when_payout_none_but_fcf_available(self):
        """When payout ratio is None but FCF payout is available, use FCF."""
        from report_generator import format_payout_ratio

        payout = None
        fcf_payout = 55.0

        result = format_payout_ratio(payout, fcf_payout)

        assert '55%' in result

    def test_na_when_both_payout_ratios_none(self):
        """When both payout ratios are None, show N/A."""
        from report_generator import format_payout_ratio

        result = format_payout_ratio(None, None)

        assert 'N/A' in result

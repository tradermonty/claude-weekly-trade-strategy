"""Tests for email sending functionality - TDD approach."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestEmailSending:
    """Test email sending functionality."""

    def test_send_report_email_calls_smtp(self):
        """send_report_email should connect to Gmail SMTP."""
        from send_report import send_report_email

        html_content = '<html><body>Test</body></html>'
        subject = 'Test Report'
        recipient = 'test@example.com'

        with patch('send_report.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = Mock(return_value=False)

            with patch.dict(os.environ, {
                'GMAIL_APP_PASSWORD': 'test_password',
                'SENDER_EMAIL': 'sender@gmail.com'
            }):
                send_report_email(html_content, subject, recipient)

            mock_smtp.assert_called_once_with('smtp.gmail.com', 587)

    def test_send_report_email_sends_html_content(self):
        """Email should contain HTML content."""
        from send_report import send_report_email

        html_content = '<html><body>Test Content</body></html>'
        subject = 'Test Report'
        recipient = 'test@example.com'

        with patch('send_report.smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = Mock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = Mock(return_value=False)

            with patch.dict(os.environ, {
                'GMAIL_APP_PASSWORD': 'test_password',
                'SENDER_EMAIL': 'sender@gmail.com'
            }):
                send_report_email(html_content, subject, recipient)

            # Check sendmail was called
            mock_server.sendmail.assert_called_once()
            # The email message should contain the HTML content
            call_args = mock_server.sendmail.call_args
            assert 'Test Content' in call_args[0][2]

    def test_send_report_email_raises_without_password(self):
        """Should raise error if GMAIL_APP_PASSWORD not set."""
        from send_report import send_report_email

        html_content = '<html><body>Test</body></html>'

        with patch.dict(os.environ, {'GMAIL_APP_PASSWORD': ''}, clear=False):
            # Remove the key if it exists
            os.environ.pop('GMAIL_APP_PASSWORD', None)

            with pytest.raises(ValueError, match='GMAIL_APP_PASSWORD'):
                send_report_email(html_content, 'Test', 'test@example.com')


class TestEmailFormatting:
    """Test email message formatting."""

    def test_create_email_message_returns_multipart(self):
        """Email message should be multipart with HTML."""
        from send_report import create_email_message

        html_content = '<html><body>Test</body></html>'
        subject = 'Test Subject'
        sender = 'sender@gmail.com'
        recipient = 'recipient@example.com'

        msg = create_email_message(html_content, subject, sender, recipient)

        assert msg['Subject'] == subject
        assert msg['From'] == sender
        assert msg['To'] == recipient
        assert msg.is_multipart()

    def test_email_has_html_part(self):
        """Email should have HTML content part."""
        from send_report import create_email_message

        html_content = '<html><body>HTML Content</body></html>'
        msg = create_email_message(html_content, 'Test', 'a@b.com', 'c@d.com')

        # Get all payloads
        parts = msg.get_payload()
        html_found = False
        for part in parts:
            if part.get_content_type() == 'text/html':
                html_found = True
                assert 'HTML Content' in part.get_payload(decode=True).decode()

        assert html_found


class TestReportLoading:
    """Test loading report from file."""

    def test_load_latest_report(self, tmp_path):
        """Should load the most recent report file."""
        from send_report import load_latest_report

        # Create test report files
        (tmp_path / 'dividend_screening_2025-11-22.html').write_text('<html>Old</html>')
        (tmp_path / 'dividend_screening_2025-11-23.html').write_text('<html>Latest</html>')

        result = load_latest_report(str(tmp_path))

        assert 'Latest' in result

    def test_load_latest_report_returns_none_if_no_files(self, tmp_path):
        """Should return None if no reports exist."""
        from send_report import load_latest_report

        result = load_latest_report(str(tmp_path))

        assert result is None

    def test_get_latest_report_path(self, tmp_path):
        """Should return path to latest report."""
        from send_report import get_latest_report_path

        # Create test report files
        (tmp_path / 'dividend_screening_2025-11-22.html').write_text('<html>Old</html>')
        (tmp_path / 'dividend_screening_2025-11-23.html').write_text('<html>Latest</html>')

        result = get_latest_report_path(str(tmp_path))

        assert '2025-11-23' in result

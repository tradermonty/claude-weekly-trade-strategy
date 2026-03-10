"""Tests for scripts/send_dap_email.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from send_dap_email import (
    _extract_subject,
    create_email_message,
    md_to_html,
    send_email,
)


# -- md_to_html ---------------------------------------------------------------


def test_md_to_html_converts_table():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    html = md_to_html(md)
    assert "<table>" in html
    assert "<td>1</td>" in html


def test_md_to_html_preserves_japanese():
    md = "# 今日のアクション\n\n日本語テスト"
    html = md_to_html(md)
    assert "今日のアクション" in html
    assert "日本語テスト" in html


def test_md_to_html_includes_inline_css():
    html = md_to_html("hello")
    assert "<style>" in html
    assert "border-collapse" in html


# -- _extract_subject ----------------------------------------------------------


def test_subject_pre_market():
    subject = _extract_subject("reports/2026-03-10/daily-action-plan-pre.md")
    assert subject == "[DAP] 3/10 Pre-Market Action Plan"


def test_subject_post_market():
    subject = _extract_subject("reports/2026-03-10/daily-action-plan-post.md")
    assert subject == "[DAP] 3/10 Post-Market Action Plan"


def test_subject_no_date():
    subject = _extract_subject("some-report.md")
    assert "[DAP]" in subject
    assert "?" in subject


# -- create_email_message ------------------------------------------------------


def test_create_email_message_structure():
    msg = create_email_message(
        "<b>hi</b>", "hi", "[DAP] Test", "a@b.com", "c@d.com"
    )
    assert msg["Subject"] == "[DAP] Test"
    assert msg["From"] == "a@b.com"
    assert msg["To"] == "c@d.com"
    payloads = msg.get_payload()
    assert len(payloads) == 2  # plain + html


# -- send_email ----------------------------------------------------------------


def test_send_email_skips_when_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("EMAIL_SENDER", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.delenv("EMAIL_RECIPIENT", raising=False)

    report = tmp_path / "daily-action-plan-pre.md"
    report.write_text("# Test")

    result = send_email(str(report))
    assert result is False


def test_send_email_returns_false_for_missing_file(monkeypatch):
    monkeypatch.setenv("EMAIL_SENDER", "a@b.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "pass")
    monkeypatch.setenv("EMAIL_RECIPIENT", "c@d.com")

    result = send_email("/nonexistent/path.md")
    assert result is False


@patch("send_dap_email.smtplib.SMTP")
def test_send_email_success(mock_smtp_cls, monkeypatch, tmp_path):
    monkeypatch.setenv("EMAIL_SENDER", "a@b.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "pass")
    monkeypatch.setenv("EMAIL_RECIPIENT", "c@d.com")

    report = tmp_path / "2026-03-10" / "daily-action-plan-pre.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Today\n| A | B |\n|---|---|\n| 1 | 2 |")

    mock_srv = MagicMock()
    mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_srv)
    mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

    result = send_email(str(report))
    assert result is True
    mock_srv.ehlo.assert_called()
    mock_srv.starttls.assert_called_once()
    mock_srv.login.assert_called_once_with("a@b.com", "pass")
    mock_srv.sendmail.assert_called_once()


@patch("send_dap_email.smtplib.SMTP")
def test_send_email_smtp_failure_returns_false(mock_smtp_cls, monkeypatch, tmp_path):
    monkeypatch.setenv("EMAIL_SENDER", "a@b.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "pass")
    monkeypatch.setenv("EMAIL_RECIPIENT", "c@d.com")

    report = tmp_path / "daily-action-plan-pre.md"
    report.write_text("# Test")

    mock_smtp_cls.side_effect = ConnectionRefusedError("refused")

    result = send_email(str(report))
    assert result is False


# -- dotenv integration --------------------------------------------------------


def test_dotenv_loads_quoted_password(tmp_path, monkeypatch):
    """Verify python-dotenv correctly parses quoted values with spaces."""
    from dotenv import load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text(
        'EMAIL_PASSWORD="abcd efgh ijkl mnop"  # Gmail App Password\n'
    )
    # Clear any existing value
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    load_dotenv(env_file, override=True)

    assert os.environ.get("EMAIL_PASSWORD") == "abcd efgh ijkl mnop"

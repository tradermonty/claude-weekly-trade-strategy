#!/usr/bin/env python3
"""Send Daily Action Plan report as HTML email via Gmail SMTP.

Usage:
    python3 scripts/send_dap_email.py reports/2026-03-10/daily-action-plan-pre.md

Requires EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT in .env or environment.
Always exits 0 so DAP pipeline is never blocked by email failures.
"""

from __future__ import annotations

import argparse
import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import markdown


# -- Conversion ---------------------------------------------------------------

INLINE_CSS = """\
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
       Helvetica, Arial, sans-serif; font-size: 14px; color: #1a1a1a;
       line-height: 1.6; padding: 16px; max-width: 800px; margin: 0 auto; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; }
th { background: #f5f5f5; }
h1 { font-size: 20px; } h2 { font-size: 17px; } h3 { font-size: 15px; }
code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-size: 13px; }
pre { background: #f0f0f0; padding: 10px; border-radius: 4px; overflow-x: auto; }
blockquote { border-left: 3px solid #ccc; margin: 8px 0; padding-left: 12px; color: #555; }
ul, ol { padding-left: 24px; }
</style>
"""


def md_to_html(md_content: str) -> str:
    """Convert markdown to styled HTML suitable for email."""
    body = markdown.markdown(
        md_content,
        extensions=["tables", "nl2br", "fenced_code"],
    )
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{INLINE_CSS}</head><body>{body}</body></html>"


# -- Email --------------------------------------------------------------------


def _extract_subject(report_path: str) -> str:
    """Build email subject from filename.

    daily-action-plan-pre.md  -> "[DAP] 3/10 Pre-Market Action Plan"
    daily-action-plan-post.md -> "[DAP] 3/10 Post-Market Action Plan"
    """
    p = Path(report_path)

    # Extract date from parent dir name (YYYY-MM-DD)
    date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(p))
    if date_match:
        month = int(date_match.group(2))
        day = int(date_match.group(3))
        date_str = f"{month}/{day}"
    else:
        date_str = "?"

    # Extract timing
    name = p.stem.lower()
    if "pre" in name:
        timing = "Pre-Market"
    elif "post" in name:
        timing = "Post-Market"
    else:
        timing = "Daily"

    return f"[DAP] {date_str} {timing} Action Plan"


def create_email_message(
    html: str, plain: str, subject: str, sender: str, recipient: str
) -> MIMEMultipart:
    """Build a MIMEMultipart email with plain text fallback and HTML body."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_email(report_path: str) -> bool:
    """Read report and send as HTML email. Returns True on success."""
    sender = os.environ.get("EMAIL_SENDER", "")
    password = os.environ.get("EMAIL_PASSWORD", "")
    recipient = os.environ.get("EMAIL_RECIPIENT", "")

    if not sender or not password or not recipient:
        print("WARNING: EMAIL_SENDER/EMAIL_PASSWORD/EMAIL_RECIPIENT not configured. Skipping email.")
        return False

    path = Path(report_path)
    if not path.is_file():
        print(f"WARNING: Report file not found: {report_path}")
        return False

    md_content = path.read_text(encoding="utf-8")
    html = md_to_html(md_content)
    subject = _extract_subject(report_path)

    msg = create_email_message(html, md_content, subject, sender, recipient)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as srv:
            srv.ehlo()
            srv.starttls()
            srv.ehlo()
            srv.login(sender, password)
            srv.sendmail(sender, [recipient], msg.as_string())
        print(f"Email sent: {subject}")
        return True
    except Exception as exc:
        print(f"WARNING: Email delivery failed: {exc}")
        return False


# -- CLI ----------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Send DAP report via email")
    parser.add_argument("report_path", help="Path to the DAP markdown report")
    args = parser.parse_args()

    send_email(args.report_path)
    # Always exit 0 — email failure must not block the DAP pipeline
    sys.exit(0)


if __name__ == "__main__":
    main()

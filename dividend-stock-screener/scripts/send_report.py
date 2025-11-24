"""
Email sender for dividend stock screening reports.

Sends HTML reports via Gmail SMTP.
Based on ../stocktrading/src/email_sender.py
"""
import os
import smtplib
import glob
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


def create_email_message(
    html_content: str,
    subject: str,
    sender: str,
    recipient: str
) -> MIMEMultipart:
    """
    Create a multipart email message with HTML content.

    Parameters
    ----------
    html_content : str
        HTML content for the email body
    subject : str
        Email subject line
    sender : str
        Sender email address
    recipient : str
        Recipient email address

    Returns
    -------
    MIMEMultipart
        Email message object
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject

    # Add plain text version (fallback)
    plain_text = "This email contains an HTML report. Please view in an HTML-capable email client."
    msg.attach(MIMEText(plain_text, "plain"))

    # Add HTML version
    msg.attach(MIMEText(html_content, "html"))

    return msg


def send_report_email(
    html_content: str,
    subject: str,
    recipient: str,
    sender_email: Optional[str] = None,
    sender_password: Optional[str] = None
) -> None:
    """
    Send HTML report via Gmail SMTP.

    Parameters
    ----------
    html_content : str
        HTML content to send
    subject : str
        Email subject line
    recipient : str
        Recipient email address
    sender_email : Optional[str]
        Sender email (defaults to SENDER_EMAIL env var)
    sender_password : Optional[str]
        Gmail app password (defaults to GMAIL_APP_PASSWORD env var)

    Raises
    ------
    ValueError
        If required credentials are not provided
    """
    # Get credentials from environment if not provided
    if sender_email is None:
        sender_email = os.getenv("SENDER_EMAIL")
    if sender_password is None:
        sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_password:
        raise ValueError(
            "GMAIL_APP_PASSWORD environment variable not set and no sender_password provided"
        )

    if not sender_email:
        raise ValueError(
            "SENDER_EMAIL environment variable not set and no sender_email provided"
        )

    # Create email message
    msg = create_email_message(html_content, subject, sender_email, recipient)

    # Send via Gmail SMTP
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())

    print(f"Email sent successfully: {sender_email} -> {recipient}")


def get_latest_report_path(reports_dir: str) -> Optional[str]:
    """
    Get the path to the most recent report file.

    Parameters
    ----------
    reports_dir : str
        Directory containing report files

    Returns
    -------
    Optional[str]
        Path to latest report file, or None if no reports exist
    """
    pattern = os.path.join(reports_dir, "dividend_screening_*.html")
    files = glob.glob(pattern)

    if not files:
        return None

    # Sort by filename (date-based naming ensures correct order)
    files.sort(reverse=True)
    return files[0]


def load_latest_report(reports_dir: str) -> Optional[str]:
    """
    Load the content of the most recent report file.

    Parameters
    ----------
    reports_dir : str
        Directory containing report files

    Returns
    -------
    Optional[str]
        Report content, or None if no reports exist
    """
    filepath = get_latest_report_path(reports_dir)

    if filepath is None:
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    """Main function to send the latest report."""
    # Default configuration
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    recipient = 'taku.saotome@gmail.com'
    default_sender = 'taku.saotome@gmail.com'

    # Set default sender email if not in environment
    if not os.getenv("SENDER_EMAIL"):
        os.environ["SENDER_EMAIL"] = default_sender

    # Load latest report
    html_content = load_latest_report(reports_dir)

    if html_content is None:
        print("No reports found to send.")
        return

    # Extract date from latest report filename
    report_path = get_latest_report_path(reports_dir)
    report_date = os.path.basename(report_path).replace('dividend_screening_', '').replace('.html', '')

    # Send email
    subject = f"Dividend Stock Screening Report - {report_date}"
    send_report_email(html_content, subject, recipient)


if __name__ == "__main__":
    main()

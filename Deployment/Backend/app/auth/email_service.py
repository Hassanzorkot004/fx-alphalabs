import os
import smtplib
from email.message import EmailMessage


def _send_email(to_email: str, subject: str, content: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_password:
        print("SMTP config missing. Email not sent.")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(content)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def send_verification_email(to_email: str, username: str, code: str):
    content = f"""
Hello {username},

Your FX AlphaLab verification code is:

{code}

This code expires in 10 minutes.

If you did not create this account, please ignore this email.

FX AlphaLab Team
"""

    _send_email(
        to_email=to_email,
        subject="FX AlphaLab - Verification Code",
        content=content,
    )


def send_welcome_email(to_email: str, username: str):
    content = f"""
Hello {username},

Welcome to FX AlphaLab.

Your trader account has been verified successfully.

You can now access:
- live FX signals
- multi-agent explanations
- market news
- economic calendar
- AlphaBot assistant

This platform is for educational and decision-support purposes only.

FX AlphaLab Team
"""

    _send_email(
        to_email=to_email,
        subject="Welcome to FX AlphaLab",
        content=content,
    )
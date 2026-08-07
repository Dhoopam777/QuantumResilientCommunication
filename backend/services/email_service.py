"""Provider-neutral email delivery abstraction."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from core.config import settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    def send_verification(self, recipient: str, link: str) -> None:
        ...


class SMTPEmailSender:
    def send_verification(self, recipient: str, link: str) -> None:
        message = EmailMessage()
        message["Subject"] = "Verify your QRC email address"
        message["From"] = settings.SMTP_FROM
        message["To"] = recipient
        message.set_content(
            "Verify your QRC email address using this link:\n\n"
            f"{link}\n\nThis link expires in 24 hours."
        )
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)


class DevelopmentEmailSender:
    """Explicit local fallback; never logs the token or verification link."""

    def send_verification(self, recipient: str, link: str) -> None:
        logger.info("Verification email queued for recipient domain=%s", recipient.rsplit("@", 1)[-1])


def get_email_sender() -> EmailSender:
    if settings.SMTP_HOST:
        return SMTPEmailSender()
    return DevelopmentEmailSender()

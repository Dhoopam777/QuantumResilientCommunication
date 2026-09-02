from email import policy
from email.parser import BytesParser

from core.config import settings
from services.email_service import SMTPEmailSender


class CapturingSMTP:
    sent_messages = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def starttls(self):
        return None

    def login(self, username, password):
        return None

    def send_message(self, message):
        self.sent_messages.append(message.as_bytes())


def test_verification_email_serializes_non_ascii_body_as_utf8(monkeypatch):
    CapturingSMTP.sent_messages = []
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr("services.email_service.smtplib.SMTP", CapturingSMTP)

    SMTPEmailSender().send_verification(
        "recipient@example.test",
        "https://qrc.example.test/verify?note=Secure\u00a0link",
    )

    raw_message = CapturingSMTP.sent_messages[0]
    parsed = BytesParser(policy=policy.default).parsebytes(raw_message)
    assert parsed.get_content_charset() == "utf-8"
    assert parsed.get_content().replace("\r\n", "\n") == (
        "Verify your QRC email address using this link:\n\n"
        "https://qrc.example.test/verify?note=Secure\u00a0link\n\n"
        "This link expires in 24 hours.\n"
    )

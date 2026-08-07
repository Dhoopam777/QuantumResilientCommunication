"""ML-DSA message signature tests."""

from datetime import datetime, timezone
import base64
import secrets
from types import SimpleNamespace

from core.config import settings
from services.crypto_service import CryptoService


def test_valid_signature_and_tamper_detection(test_user, monkeypatch):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    monkeypatch.setattr(
        settings,
        "PQC_MASTER_KEY",
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii"),
    )
    CryptoService.generate_identity(test_user)
    created_at = datetime.now(timezone.utc)
    signature = CryptoService.sign_message(
        test_user,
        test_user.id,
        "text",
        "ciphertext",
        created_at,
        [{"id": "attachment-1", "checksum_sha256": "abc"}],
    )
    message = SimpleNamespace(
        signature=signature,
        signature_algorithm="ML-DSA-65",
        signature_created_at=created_at,
        conversation_id=test_user.id,
        sender_id=test_user.id,
        message_type="text",
        content_encrypted="ciphertext",
        created_at=created_at,
    )

    assert CryptoService.verify_message(
        message, test_user, [{"id": "attachment-1", "checksum_sha256": "abc"}]
    )
    message.content_encrypted = "tampered"
    assert not CryptoService.verify_message(message, test_user)
    message.content_encrypted = "ciphertext"
    message.signature_created_at = created_at.replace(second=created_at.second + 1)
    assert not CryptoService.verify_message(message, test_user)


def test_wrong_public_key_rejected(test_user, test_user2, monkeypatch):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    monkeypatch.setattr(
        settings,
        "PQC_MASTER_KEY",
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii"),
    )
    CryptoService.generate_identity(test_user)
    CryptoService.generate_identity(test_user2)
    created_at = datetime.now(timezone.utc)
    signature = CryptoService.sign_message(
        test_user, test_user.id, "text", "ciphertext", created_at
    )
    message = SimpleNamespace(
        signature=signature,
        signature_algorithm="ML-DSA-65",
        signature_created_at=created_at,
        conversation_id=test_user.id,
        sender_id=test_user.id,
        message_type="text",
        content_encrypted="ciphertext",
        created_at=created_at,
    )
    assert not CryptoService.verify_message(message, test_user2)

"""ML-DSA message signature tests.

These tests model the production architecture: the ML-DSA-65 signing key is
generated on the client device and never reaches the server. Only the public
key is registered, so the server-side verifier is exercised against real
device-produced signatures.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services.crypto_service import CryptoService
from tests.pqc_helpers import register_device_public_keys, sign_payload


def _device_signed_message(user, signing_key, created_at, attachments_metadata=None):
    """Build a message signed the way a client device signs it."""
    payload = CryptoService._message_payload(
        user.id,
        user.id,
        "text",
        "ciphertext",
        created_at,
        attachments_metadata,
    )
    return SimpleNamespace(
        signature=sign_payload(signing_key, payload),
        signature_algorithm="ML-DSA-65",
        signature_created_at=created_at,
        conversation_id=user.id,
        sender_id=user.id,
        message_type="text",
        content_encrypted="ciphertext",
        created_at=created_at,
    )


def test_valid_signature_and_tamper_detection(test_user):
    signing_key = register_device_public_keys(test_user)
    created_at = datetime.now(timezone.utc)
    attachments_metadata = [{"id": "attachment-1", "checksum_sha256": "abc"}]
    message = _device_signed_message(
        test_user, signing_key, created_at, attachments_metadata
    )

    assert CryptoService.verify_message(message, test_user, attachments_metadata)
    message.content_encrypted = "tampered"
    assert not CryptoService.verify_message(message, test_user)
    message.content_encrypted = "ciphertext"
    message.signature_created_at = created_at + timedelta(seconds=1)
    assert not CryptoService.verify_message(message, test_user)


def test_wrong_public_key_rejected(test_user, test_user2):
    signing_key = register_device_public_keys(test_user)
    register_device_public_keys(test_user2)
    created_at = datetime.now(timezone.utc)
    message = _device_signed_message(test_user, signing_key, created_at)

    assert not CryptoService.verify_message(message, test_user2)
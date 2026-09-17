"""Phase 0 regression tests: no server-side PQC private-key operations.

These tests lock in the security invariant that PQC private keys are generated
and retained exclusively on the client device. The server must never expose an
operation that generates, encrypts, stores, decrypts, or signs with PQC private
key material.
"""

import base64
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from core.config import settings
from models.message import Message
from pqcrypto.kem import ml_kem_768
from pqcrypto.sign import ml_dsa_65
from schemas.crypto import DevicePublicKeyUpdate
from services.crypto_service import CryptoService
from services.message_service import edit_message, send_message
from tests.pqc_helpers import register_device_public_keys, sign_payload


REMOVED_SERVER_PRIVATE_KEY_OPERATIONS = [
    "generate_identity",
    "decrypt_private_key",
    "sign_message",
    "create_session",
    "recover_session",
    "_derive_session_key",
    "_encrypt",
    "_cipher",
]

# Only these non-test sources may mention the temporarily retained encrypted
# private-key columns: the ORM definition and the defense-in-depth nulling path.
APPROVED_PRIVATE_COLUMN_REFERENCES = {
    "models/user.py",
    "routers/crypto.py",
}

PRIVATE_COLUMN_NAMES = (
    "pq_kem_private_key_encrypted",
    "pq_signature_private_key_encrypted",
)

SCANNED_SOURCE_ROOTS = (
    "core",
    "database",
    "managers",
    "models",
    "routers",
    "schemas",
    "services",
)

@pytest.mark.parametrize("operation", REMOVED_SERVER_PRIVATE_KEY_OPERATIONS)
def test_crypto_service_exposes_no_private_key_operations(operation):
    assert not hasattr(CryptoService, operation)


def test_device_public_key_update_rejects_private_key_fields():
    public_only = {
        "kem_public_key": "A" * 1184,
        "signature_public_key": "A" * 2592,
        "algorithm_version": "ML-KEM-768+ML-DSA-65",
    }
    assert DevicePublicKeyUpdate(**public_only)

    for forbidden in (
        "kem_private_key",
        "signature_private_key",
        "private_key",
        "secret_key",
    ):
        with pytest.raises(ValidationError):
            DevicePublicKeyUpdate(**{**public_only, forbidden: "leaked"})


def test_missing_client_signature_is_rejected_without_server_signing(
    db_session, test_user, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)

    with pytest.raises(ValueError, match="Message authentication failed"):
        send_message(
            db=db_session,
            conversation_id=test_conversation.id,
            sender_id=test_user.id,
            content_encrypted="ciphertext",
            content_hash="deadbeef",
            message_type="text",
        )

    assert db_session.query(Message).count() == 0


def test_missing_client_signature_on_edit_is_rejected(
    db_session, test_user, test_message, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)

    with pytest.raises(ValueError, match="Message authentication failed"):
        edit_message(
            db=db_session,
            message_id=test_message.id,
            user_id=test_user.id,
            content_encrypted="new-ciphertext",
            content_hash="newhash",
        )


def test_public_key_upload_stores_public_keys_only(
    client, db_session, test_user, auth_headers
):
    kem_public, _ = ml_kem_768.generate_keypair()
    signature_public, _ = ml_dsa_65.generate_keypair()
    kem_public_b64 = base64.b64encode(kem_public).decode("ascii")
    signature_public_b64 = base64.b64encode(signature_public).decode("ascii")

    response = client.put(
        "/api/v1/crypto/device-keys",
        json={
            "kem_public_key": kem_public_b64,
            "signature_public_key": signature_public_b64,
            "algorithm_version": "ML-KEM-768+ML-DSA-65",
        },
        headers=auth_headers,
    )

    assert response.status_code == 204
    db_session.refresh(test_user)
    assert test_user.pq_kem_public_key == kem_public_b64
    assert test_user.pq_signature_public_key == signature_public_b64
    assert test_user.pq_kem_private_key_encrypted is None
    assert test_user.pq_signature_private_key_encrypted is None

def test_client_produced_signature_still_verifies(test_user):
    signing_key = register_device_public_keys(test_user)
    created_at = datetime.now(timezone.utc)
    payload = CryptoService._message_payload(
        test_user.id, test_user.id, "text", "ciphertext", created_at
    )
    message = SimpleNamespace(
        signature=sign_payload(signing_key, payload),
        signature_algorithm="ML-DSA-65",
        signature_created_at=created_at,
        conversation_id=test_user.id,
        sender_id=test_user.id,
        message_type="text",
        content_encrypted="ciphertext",
    )

    assert CryptoService.verify_message(message, test_user)


def test_create_client_session_accepts_client_ciphertext(
    test_user, test_user2, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    recipient_public_key, _ = ml_kem_768.generate_keypair()
    ciphertext, _shared_secret = ml_kem_768.encrypt(recipient_public_key)
    ciphertext_b64 = base64.b64encode(ciphertext).decode("ascii")

    session = CryptoService.create_client_session(
        test_user.id, test_user2, test_conversation.id, ciphertext_b64
    )

    assert session.kem_ciphertext == ciphertext_b64
    assert session.algorithm == "ML-KEM-768+ML-DSA-65"
    assert session.session_key_id


def test_only_approved_sources_reference_encrypted_private_key_columns():
    backend_root = Path(__file__).resolve().parents[1]
    offenders = set()
    for root in SCANNED_SOURCE_ROOTS:
        for path in (backend_root / root).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(name in text for name in PRIVATE_COLUMN_NAMES):
                offenders.add(path.relative_to(backend_root).as_posix())

    assert offenders == APPROVED_PRIVATE_COLUMN_REFERENCES
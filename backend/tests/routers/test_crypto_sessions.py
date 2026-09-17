"""ML-KEM session establishment tests.

The server only ever persists client-supplied ML-KEM ciphertext. Decapsulation
and AES-256 key derivation happen on the client devices; these tests simulate
that client-side work locally to prove the server never handles a secret.
"""

import base64
import secrets
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from core.config import settings
from models.session_key import SessionKey
from pqcrypto.kem import ml_kem_768
from services.crypto_service import CryptoService


def _master_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def _client_encapsulate(recipient_public_key: str) -> tuple[str, bytes]:
    """Client-side ML-KEM encapsulation; returns ciphertext + shared secret."""
    ciphertext, shared_secret = ml_kem_768.encrypt(
        base64.b64decode(recipient_public_key.encode("ascii"), validate=True)
    )
    return base64.b64encode(ciphertext).decode("ascii"), shared_secret


def _client_session_payload(recipient_public_key: str) -> dict[str, str]:
    ciphertext, shared_secret = _client_encapsulate(recipient_public_key)
    del shared_secret
    return {"kem_ciphertext": ciphertext}


def _client_derive_aes_key(shared_secret: bytes, ciphertext: bytes) -> bytes:
    """Client-side HKDF derivation. The server never performs this step."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=ciphertext,
        info=b"qrc/ml-kem-768/session/aes-256",
    ).derive(shared_secret)


def _set_device_public_key(user) -> bytes:
    """Register a device's public key on ``user`` and return its secret key."""
    public_key, secret_key = ml_kem_768.generate_keypair()
    user.pq_kem_public_key = base64.b64encode(public_key).decode("ascii")
    user.pq_algorithm_version = "ML-KEM-768+ML-DSA-65"
    user.pq_key_created_at = datetime.now(timezone.utc)
    return secret_key
def test_client_session_persists_ciphertext_without_server_secrets(
    db_session, test_user, test_user2, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")

    recipient_secret_key = _set_device_public_key(test_user2)
    db_session.commit()

    ciphertext_b64, initiator_shared_secret = _client_encapsulate(
        test_user2.pq_kem_public_key
    )

    session = CryptoService.create_client_session(
        test_user.id, test_user2, test_conversation.id, ciphertext_b64
    )
    db_session.add(session)
    db_session.commit()

    # The server stores the client ciphertext and never a key or shared secret.
    assert not hasattr(session, "shared_secret")
    assert not hasattr(session, "aes_key")
    assert session.kem_ciphertext == ciphertext_b64
    assert session.session_key_id
    assert db_session.query(SessionKey).count() == 1

    ciphertext = base64.b64decode(session.kem_ciphertext)
    assert len(ciphertext) == ml_kem_768.CIPHERTEXT_SIZE
    assert CryptoService.expire_session(session) is False

    # Both parties derive the identical AES-256 key locally, entirely off-server.
    initiator_key = _client_derive_aes_key(initiator_shared_secret, ciphertext)
    recipient_key = _client_derive_aes_key(
        ml_kem_768.decrypt(recipient_secret_key, ciphertext), ciphertext
    )
    assert initiator_key == recipient_key
    assert len(initiator_key) == 32


def test_create_client_session_rejects_invalid_ciphertext(
    test_user, test_user2, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")

    with pytest.raises(ValueError):
        CryptoService.create_client_session(
            test_user.id,
            test_user2,
            test_conversation.id,
            base64.b64encode(b"too-short").decode("ascii"),
        )


def test_session_api_returns_metadata_only(
    client, db_session, auth_headers, test_user, test_user2, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    _set_device_public_key(test_user2)
    db_session.commit()

    response = client.post(
        f"/api/v1/crypto/session/{test_user2.username}",
        json=_client_session_payload(test_user2.pq_kem_public_key),
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert set(response.json()) == {"session_id", "algorithm", "expires_at"}
    assert "secret" not in response.text.lower()
    assert "ciphertext" not in response.text.lower()
    assert "key" not in response.text.lower()


def test_session_rejects_non_participant(
    client, db_session, auth_headers, test_user, test_user2, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    _set_device_public_key(test_user2)
    db_session.commit()

    response = client.post(
        f"/api/v1/crypto/session/{test_user2.username}",
        json=_client_session_payload(test_user2.pq_kem_public_key),
        headers=auth_headers,
    )

    assert response.status_code == 403
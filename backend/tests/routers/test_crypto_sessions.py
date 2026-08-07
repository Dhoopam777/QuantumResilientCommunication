"""ML-KEM session establishment tests."""

import base64
import secrets

from core.config import settings
from models.session_key import SessionKey
from services.crypto_service import CryptoService


def _master_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def test_ml_kem_and_hkdf_derive_identical_keys(
    client, db_session, test_user, test_user2, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", _master_key())
    CryptoService.generate_identity(test_user)
    CryptoService.generate_identity(test_user2)
    db_session.commit()

    session, initiator_key = CryptoService.create_session(
        test_user.id, test_user2, test_conversation.id
    )
    db_session.add(session)
    db_session.commit()
    recipient_key = CryptoService.recover_session(session, test_user2)

    assert initiator_key == recipient_key
    assert not hasattr(session, "shared_secret")
    assert not hasattr(session, "aes_key")
    assert session.kem_ciphertext
    assert session.session_key_id
    assert db_session.query(SessionKey).count() == 1


def test_session_api_returns_metadata_only(
    client, db_session, auth_headers, test_user, test_user2, test_conversation, monkeypatch
):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_ALGORITHM", "ML-KEM-768+ML-DSA-65")
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", _master_key())
    CryptoService.generate_identity(test_user)
    CryptoService.generate_identity(test_user2)
    db_session.commit()

    response = client.post(
        f"/api/v1/crypto/session/{test_user2.username}",
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
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", _master_key())
    CryptoService.generate_identity(test_user2)
    db_session.commit()

    response = client.post(
        f"/api/v1/crypto/session/{test_user2.username}",
        headers=auth_headers,
    )

    assert response.status_code == 403

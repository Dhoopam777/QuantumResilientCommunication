"""Post-quantum identity key tests."""

import base64

from core.config import settings
from core.security import create_access_token
from models.user import User
from services.crypto_service import CryptoService


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


def test_registration_generates_encrypted_pqc_identity(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", "test-only-master-key-0123456789012345")
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "pqc_user", "email": "pqc@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    user = db_session.query(User).filter(User.username == "pqc_user").first()
    assert user.pq_algorithm_version == "ML-KEM-768+ML-DSA-65"
    assert user.pq_kem_public_key
    assert user.pq_signature_public_key
    assert user.pq_kem_private_key_encrypted
    assert user.pq_signature_private_key_encrypted
    assert user.pq_kem_private_key_encrypted != user.pq_kem_public_key
    assert len(base64.b64decode(user.pq_kem_public_key)) == 1184
    assert CryptoService.decrypt_private_key(user.pq_kem_private_key_encrypted)


def test_public_key_api_excludes_private_material(client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", "test-only-master-key-0123456789012345")
    CryptoService.generate_identity(test_user)
    db_session.commit()
    response = client.get(
        f"/api/v1/crypto/public-key/{test_user.username}",
        headers=headers(test_user),
    )
    assert response.status_code == 200
    assert set(response.json()) == {"kem_public_key", "signature_public_key", "algorithm_version"}
    assert "private" not in response.text.lower()

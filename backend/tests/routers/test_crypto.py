"""Post-quantum identity key tests."""

import base64
import secrets
from urllib.parse import parse_qs, urlparse

from core.config import settings
from core.security import create_access_token
from models.user import User
from pqcrypto.kem import ml_kem_768
from pqcrypto.sign import ml_dsa_65
from tests.pqc_helpers import register_device_public_keys


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


def master_key():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


class CapturingSender:
    links = []

    def send_verification(self, recipient, link):
        self.links.append(link)


def test_registration_uses_client_device_keys(client, monkeypatch):
    sender = CapturingSender()
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", master_key())
    monkeypatch.setattr(
        "services.email_verification_service.get_email_sender", lambda: sender
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "pqc_user", "email": "pqc@example.com", "password": "SecurePass123!"},
    )
    assert response.status_code == 201
    assert response.json()["pq_key_created_at"] is None

    verification_token = parse_qs(urlparse(sender.links[-1]).query)["token"][0]
    assert client.get(f"/api/v1/auth/verify-email?token={verification_token}").status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "pqc_user", "password": "SecurePass123!"},
    )
    assert login.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    kem_public, _ = ml_kem_768.generate_keypair()
    signature_public, _ = ml_dsa_65.generate_keypair()
    device_keys = {
        "kem_public_key": base64.b64encode(kem_public).decode("ascii"),
        "signature_public_key": base64.b64encode(signature_public).decode("ascii"),
        "algorithm_version": "ML-KEM-768+ML-DSA-65",
    }
    assert client.put("/api/v1/crypto/device-keys", json=device_keys, headers=auth_headers).status_code == 204

    public_key = client.get("/api/v1/crypto/public-key/pqc_user", headers=auth_headers)
    assert public_key.status_code == 200
    assert public_key.json()["kem_public_key"] == device_keys["kem_public_key"]
    assert public_key.json()["signature_public_key"] == device_keys["signature_public_key"]
    assert public_key.json()["algorithm_version"] == device_keys["algorithm_version"]
    assert "private" not in public_key.text.lower()


def test_public_key_api_excludes_private_material(client, db_session, test_user, monkeypatch):
    monkeypatch.setattr(settings, "PQC_ENABLED", True)
    monkeypatch.setattr(settings, "PQC_MASTER_KEY", master_key())
    register_device_public_keys(test_user)
    db_session.commit()
    response = client.get(
        f"/api/v1/crypto/public-key/{test_user.username}",
        headers=headers(test_user),
    )
    assert response.status_code == 200
    assert set(response.json()) == {
        "kem_public_key",
        "signature_public_key",
        "algorithm_version",
        "created_at",
    }
    assert "private" not in response.text.lower()

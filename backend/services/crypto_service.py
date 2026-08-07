"""Post-quantum identity key management.

Uses the standardized ML-KEM-768 and ML-DSA-65 implementations exposed by
the maintained ``pqcrypto`` bindings. Message encryption is intentionally not
handled here.
"""

import base64
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from core.config import settings
from models.user import User
from pqcrypto.kem import ml_kem_768
from pqcrypto.sign import ml_dsa_65


ALGORITHM_VERSION = "ML-KEM-768+ML-DSA-65"


class CryptoService:
    """Generate PQC identity keys and protect private material at rest."""

    @staticmethod
    def _cipher() -> Fernet:
        configured_key = settings.PQC_MASTER_KEY.strip()
        try:
            raw_key = base64.b64decode(
                configured_key.encode("ascii"),
                altchars=b"-_",
                validate=True,
            )
        except (UnicodeEncodeError, ValueError, base64.binascii.Error) as exc:
            raise RuntimeError(
                "PQC_MASTER_KEY must be a URL-safe base64-encoded 32-byte key"
            ) from exc
        if (
            len(raw_key) != 32
            or base64.urlsafe_b64encode(raw_key).decode("ascii") != configured_key
        ):
            raise RuntimeError(
                "PQC_MASTER_KEY must be a URL-safe base64-encoded 32-byte key"
            )
        return Fernet(configured_key.encode("ascii"))

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @staticmethod
    def _encrypt(value: bytes) -> str:
        return CryptoService._cipher().encrypt(value).decode("ascii")

    @staticmethod
    def decrypt_private_key(value: str) -> bytes:
        """Decrypt server-held private material for future crypto operations."""
        return CryptoService._cipher().decrypt(value.encode("ascii"))

    @staticmethod
    def generate_identity(user: User) -> None:
        if not settings.PQC_ENABLED:
            return
        if settings.PQC_ALGORITHM != ALGORITHM_VERSION:
            raise RuntimeError(
                f"Unsupported PQC_ALGORITHM: {settings.PQC_ALGORITHM}"
            )
        kem_public, kem_private = ml_kem_768.generate_keypair()
        signature_public, signature_private = ml_dsa_65.generate_keypair()
        user.pq_kem_public_key = CryptoService._encode(kem_public)
        user.pq_kem_private_key_encrypted = CryptoService._encrypt(kem_private)
        user.pq_signature_public_key = CryptoService._encode(signature_public)
        user.pq_signature_private_key_encrypted = CryptoService._encrypt(signature_private)
        user.pq_algorithm_version = ALGORITHM_VERSION
        user.pq_key_created_at = datetime.now(timezone.utc)

    @staticmethod
    def public_key_metadata(user: User) -> dict:
        return {
            "username": user.username,
            "kem_public_key": user.pq_kem_public_key,
            "signature_public_key": user.pq_signature_public_key,
            "algorithm_version": user.pq_algorithm_version,
            "created_at": user.pq_key_created_at,
        }

"""Post-quantum identity key management.

Uses the standardized ML-KEM-768 and ML-DSA-65 implementations exposed by
the maintained ``pqcrypto`` bindings. Message encryption is intentionally not
handled here.

PQC private keys are generated on, and never leave, the user's device. This
module therefore only validates public keys, stores client-supplied KEM
ciphertext, and verifies device-produced ML-DSA-65 signatures. It never
generates, encrypts, stores, decrypts, or signs with a PQC private key.
"""

import base64
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from core.config import settings
from models.user import User
from models.session_key import SessionKey
from pqcrypto.kem import ml_kem_768
from pqcrypto.sign import ml_dsa_65


ALGORITHM_VERSION = "ML-KEM-768+ML-DSA-65"
SIGNATURE_ALGORITHM = "ML-DSA-65"


class CryptoService:
    """Validate public PQC keys and verify device-produced signatures."""

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        try:
            return base64.b64decode(value.encode("ascii"), validate=True)
        except (UnicodeEncodeError, ValueError, base64.binascii.Error) as exc:
            raise RuntimeError("Invalid encoded cryptographic value") from exc

    @staticmethod
    def validate_public_keys(kem_public_key: str, signature_public_key: str) -> None:
        """Validate canonical Base64 and FIPS-203/FIPS-204 public key sizes."""
        kem = CryptoService._decode(kem_public_key)
        signature = CryptoService._decode(signature_public_key)
        if len(kem) != ml_kem_768.PUBLIC_KEY_SIZE or len(signature) != ml_dsa_65.PUBLIC_KEY_SIZE:
            raise ValueError("Invalid public key size")

    @staticmethod
    def create_client_session(
        initiator_id: uuid.UUID,
        recipient: User,
        conversation_id: uuid.UUID,
        kem_ciphertext: str,
    ) -> SessionKey:
        """Persist client-created ML-KEM ciphertext without handling secrets."""
        if not settings.PQC_ENABLED or settings.PQC_ALGORITHM != ALGORITHM_VERSION:
            raise RuntimeError("PQC session establishment is unavailable")
        try:
            ciphertext = CryptoService._decode(kem_ciphertext)
        except RuntimeError as exc:
            raise ValueError("Invalid session ciphertext") from exc
        if len(ciphertext) != ml_kem_768.CIPHERTEXT_SIZE:
            raise ValueError("Invalid session ciphertext")
        return SessionKey(
            conversation_id=conversation_id,
            initiator_id=initiator_id,
            recipient_id=recipient.id,
            kem_ciphertext=CryptoService._encode(ciphertext),
            session_key_id=uuid.UUID(bytes=secrets.token_bytes(16), version=4),
            algorithm=ALGORITHM_VERSION,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.PQC_SESSION_TTL_MINUTES),
        )

    @staticmethod
    def expire_session(session: SessionKey) -> bool:
        """Return whether a session is expired without mutating stored metadata."""
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)

    @staticmethod
    def _message_payload(
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        message_type: str,
        content_encrypted: str,
        signature_created_at: datetime,
        attachments_metadata: list[dict] | None = None,
    ) -> bytes:
        # Canonicalize the timestamp to the exact 3-digit-millisecond UTC format
        # the signing client uses (e.g. "2026-09-12T10:00:00.123+00:00").
        # Python's datetime.isoformat() emits 6-digit microseconds (or no
        # fraction at all), which reconstructs a different signed payload and
        # rejects otherwise-valid ML-DSA signatures.
        sent_at = signature_created_at.astimezone(timezone.utc)
        timestamp = sent_at.strftime("%Y-%m-%dT%H:%M:%S") + f".{sent_at.microsecond // 1000:03d}+00:00"
        payload = {
            "conversation_id": str(conversation_id),
            "sender_id": str(sender_id),
            "message_type": message_type,
            "content_encrypted": content_encrypted,
            "attachments": sorted(
                attachments_metadata or [],
                key=lambda attachment: str(attachment.get("id", "")),
            ),
            "timestamp": timestamp,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def verify_message(
        message,
        sender: User,
        attachments_metadata: list[dict] | None = None,
    ) -> bool:
        """Verify a stored message signature without exposing signature bytes."""
        if (
            not message.signature
            or message.signature_algorithm != SIGNATURE_ALGORITHM
            or not message.signature_created_at
            or not sender.pq_signature_public_key
        ):
            return False
        signature_created_at = message.signature_created_at
        if signature_created_at.tzinfo is None:
            signature_created_at = signature_created_at.replace(tzinfo=timezone.utc)
        try:
            signature = CryptoService._decode(message.signature)
            public_key = CryptoService._decode(sender.pq_signature_public_key)
            payload = CryptoService._message_payload(
                message.conversation_id,
                message.sender_id,
                message.message_type,
                message.content_encrypted,
                signature_created_at,
                attachments_metadata,
            )
            return ml_dsa_65.verify(public_key, payload, signature)
        except (RuntimeError, TypeError, ValueError):
            return False

    @staticmethod
    def public_key_metadata(user: User) -> dict:
        return {
            "username": user.username,
            "kem_public_key": user.pq_kem_public_key,
            "signature_public_key": user.pq_signature_public_key,
            "algorithm_version": user.pq_algorithm_version,
            "created_at": user.pq_key_created_at,
        }

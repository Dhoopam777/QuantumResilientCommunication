"""Authenticated public post-quantum identity key endpoint."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased

from core.audit_logger import log_pqc_event, log_session_event
from core.dependencies import get_current_user, require_verified_user
from core.config import settings
from core.rate_limiter import rate_limiter
from database.database import get_db
from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant
from models.session_key import SessionKey
from models.user import User
from schemas.crypto import DevicePublicKeyUpdate, PublicKeyResponse
from schemas.session import SessionCreateRequest, SessionCreatedResponse, SessionMetadataResponse
from services.crypto_service import ALGORITHM_VERSION, CryptoService
from services.user_service import get_user_by_username

router = APIRouter(prefix="/api/v1/crypto", tags=["cryptography"])


def _active_conversation(
    db: Session, initiator_id: uuid.UUID, recipient_id: uuid.UUID
) -> Conversation | None:
    initiator = aliased(ConversationParticipant)
    recipient = aliased(ConversationParticipant)
    return (
        db.query(Conversation)
        .join(
            initiator,
            (initiator.conversation_id == Conversation.id)
            & (initiator.user_id == initiator_id)
            & initiator.left_at.is_(None),
        )
        .join(
            recipient,
            (recipient.conversation_id == Conversation.id)
            & (recipient.user_id == recipient_id)
            & recipient.left_at.is_(None),
        )
        .order_by(Conversation.created_at.asc())
        .first()
    )


@router.get("/public-key/{username}", response_model=PublicKeyResponse)
def get_public_key(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PublicKeyResponse:
    target = get_user_by_username(db, username)
    if (
        target is None
        or not target.is_active
        or not target.pq_kem_public_key
        or not target.pq_signature_public_key
        or not target.pq_algorithm_version
        or not target.pq_key_created_at
    ):
        log_pqc_event("PQC_OPERATION_FAILED", str(current_user.id), "public key unavailable")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public key not available",
        )
    log_pqc_event("PQC_PUBLIC_KEY_REQUEST", str(current_user.id))
    metadata = CryptoService.public_key_metadata(target)
    metadata.pop("username", None)
    return PublicKeyResponse(**metadata)


@router.post(
    "/session/{username}",
    response_model=SessionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def establish_session(
    username: str,
    request: SessionCreateRequest,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> SessionCreatedResponse:
    if not settings.PQC_ENABLED or settings.PQC_ALGORITHM != ALGORITHM_VERSION:
        log_session_event("SESSION_FAILED", str(current_user.id), reason="PQC unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session establishment unavailable",
        )
    rate_limiter.check_session_rate(str(current_user.id))
    recipient = get_user_by_username(db, username)
    if (
        recipient is None
        or recipient.id == current_user.id
        or not recipient.is_active
        or not recipient.pq_kem_public_key
    ):
        log_session_event("SESSION_FAILED", str(current_user.id), reason="recipient unavailable")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session unavailable")

    conversation = _active_conversation(db, current_user.id, recipient.id)
    if conversation is None:
        log_session_event("SESSION_FAILED", str(current_user.id), reason="conversation unavailable")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation access denied")

    try:
        session = CryptoService.create_client_session(
            current_user.id, recipient, conversation.id, request.kem_ciphertext
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    except (RuntimeError, ValueError) as exc:
        db.rollback()
        log_session_event("SESSION_FAILED", str(current_user.id), reason="cryptographic operation failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session unavailable") from exc
    except IntegrityError as exc:
        db.rollback()
        log_session_event("SESSION_FAILED", str(current_user.id), reason="session persistence failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session unavailable") from exc
    log_session_event(
        "SESSION_CREATED",
        str(current_user.id),
        str(session.id),
        str(conversation.id),
    )
    return SessionCreatedResponse(
        session_id=session.id,
        algorithm=session.algorithm,
        expires_at=session.expires_at,
    )


@router.put("/device-keys", status_code=status.HTTP_204_NO_CONTENT)
def upload_device_keys(
    request: DevicePublicKeyUpdate,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> None:
    if request.algorithm_version != ALGORITHM_VERSION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported algorithm")
    try:
        CryptoService.validate_public_keys(
            request.kem_public_key, request.signature_public_key
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid public key") from exc
    current_user.pq_kem_public_key = request.kem_public_key
    current_user.pq_signature_public_key = request.signature_public_key
    current_user.pq_algorithm_version = request.algorithm_version
    current_user.pq_key_created_at = datetime.now(timezone.utc)
    # Device ownership is the source of truth after migration. Legacy encrypted
    # server keys are removed so the backend cannot continue using private keys.
    current_user.pq_kem_private_key_encrypted = None
    current_user.pq_signature_private_key_encrypted = None
    db.commit()


@router.get("/sessions", response_model=list[SessionMetadataResponse])
def list_sessions(
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> list[SessionMetadataResponse]:
    now = datetime.now(timezone.utc)
    sessions = (
        db.query(SessionKey)
        .filter(
            (SessionKey.initiator_id == current_user.id)
            | (SessionKey.recipient_id == current_user.id)
        )
        .order_by(SessionKey.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        _session_metadata(current_user, session)
        for session in sessions
    ]


def _session_metadata(user: User, session: SessionKey) -> SessionMetadataResponse:
    expired = CryptoService.expire_session(session)
    if expired:
        log_session_event("SESSION_EXPIRED", str(user.id), str(session.id))
    return SessionMetadataResponse(
        algorithm=session.algorithm,
        created_at=session.created_at,
        expires_at=session.expires_at,
        status="expired" if expired else "active",
        session_id=session.id,
        conversation_id=session.conversation_id,
        kem_ciphertext=session.kem_ciphertext,
    )

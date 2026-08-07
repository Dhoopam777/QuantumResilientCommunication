"""Authenticated public post-quantum identity key endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.audit_logger import log_pqc_event
from core.dependencies import get_current_user
from database.database import get_db
from models.user import User
from schemas.crypto import PublicKeyResponse
from services.crypto_service import CryptoService
from services.user_service import get_user_by_username

router = APIRouter(prefix="/api/v1/crypto", tags=["cryptography"])


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

"""
Attachment Router for Quantum-Resilient Communication System

Secure file upload/download/delete endpoints with:
- JWT authentication
- Conversation membership authorization (IDOR prevention)
- Rate limiting
- Security headers (X-Content-Type-Options: nosniff)
- Content-Disposition headers
- No path disclosure
"""

import uuid
from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, Response,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.database import get_db
from core.dependencies import require_verified_user
from models.user import User
from schemas.attachment import AttachmentResponse, AttachmentUploadResponse
from services.attachment_service import (
    AttachmentService,
)
from core.audit_logger import log_auth_failure

router = APIRouter(
    prefix="/api/v1/attachments",
    tags=["attachments"],
)


@router.post(
    "/upload",
    response_model=AttachmentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload attachment to conversation",
    description=(
        "Upload a file attachment to a conversation. Only PNG, JPEG, and WebP "
        "images are accepted (Phase 8.1). Full security validation is performed: "
        "file size, MIME type, extension matching, EXIF stripping, and SHA-256 checksums."
    ),
    responses={
        201: {"description": "Attachment uploaded successfully"},
        400: {"description": "Invalid file or validation failed"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - user is not a participant in this conversation"},
        413: {"description": "Payload too large"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def upload_attachment(
    conversation_id: uuid.UUID = Form(..., description="Conversation ID"),
    file: UploadFile = File(..., description="File to upload"),
    encryption_algorithm: str | None = Form(None),
    declared_mime_type: str | None = Form(None),
    nonce: str | None = Form(None),
    authentication_tag: str | None = Form(None),
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> AttachmentUploadResponse:
    """
    Upload a secure file attachment to a conversation.

    Security measures applied:
    - File must be PNG, JPEG, or WebP (Phase 8.1)
    - MIME type detected from magic bytes, never from client header
    - Extension must match detected MIME type
    - EXIF metadata stripped; images re-encoded server-side
    - SHA-256 checksum computed server-side
    - File stored with UUIDv4 filename outside the web root
    - Rate limited per user
    - Logged for audit purposes
    """
    attachment = await AttachmentService.upload_attachment(
        db=db,
        conversation_id=conversation_id,
        uploader_id=current_user.id,
        file=file,
        original_filename=file.filename or "upload",
        encryption_algorithm=encryption_algorithm,
        declared_mime_type=declared_mime_type,
        nonce=nonce,
        authentication_tag=authentication_tag,
    )

    response = AttachmentUploadResponse.model_validate(attachment)
    # Build thumbnail URL — relative API path, never filesystem path
    if attachment.thumbnail_filename and not attachment.encryption_algorithm:
        response.thumbnail_url = f"/api/v1/attachments/{attachment.id}/thumbnail"
    return response


@router.get(
    "/{attachment_id}",
    response_model=AttachmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get attachment metadata",
    description="Get attachment metadata. Only visible to conversation participants.",
    responses={
        200: {"description": "Attachment metadata"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - not a participant"},
        404: {"description": "Attachment not found"},
    },
)
def get_attachment_metadata(
    attachment_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    """Get attachment metadata (no file content)."""
    attachment = AttachmentService.get_attachment(db, attachment_id, current_user.id)

    response = AttachmentResponse.model_validate(attachment)
    if attachment.thumbnail_filename and not attachment.encryption_algorithm:
        response.thumbnail_url = f"/api/v1/attachments/{attachment.id}/thumbnail"
    return response


@router.get(
    "/{attachment_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download attachment",
    description="Download the original attachment file. Only participants can download.",
    responses={
        200: {"description": "File content"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - not a participant"},
        404: {"description": "Attachment not found or file missing"},
    },
)
def download_attachment(
    attachment_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Download the original attachment file.

    Security:
    - Verifies user is conversation participant (IDOR prevention)
    - Sets X-Content-Type-Options: nosniff (prevents MIME sniffing)
    - Sets Content-Disposition: attachment (prevents inline rendering)
    - Never discloses filesystem paths
    """
    attachment = AttachmentService.get_attachment(db, attachment_id, current_user.id)

    try:
        file_bytes = AttachmentService.get_attachment_bytes(attachment)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment file not found on disk",
        )

    # Determine media type from validated MIME type
    media_type = attachment.mime_type

    # Generate safe download filename from sanitized original_filename
    download_filename = AttachmentService.sanitize_filename(attachment.original_filename)

    headers = {
        "Content-Disposition": f'attachment; filename="{download_filename}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Length": str(len(file_bytes)),
    }

    return StreamingResponse(
        iter([file_bytes]),
        media_type=media_type,
        headers=headers,
    )


@router.get(
    "/{attachment_id}/thumbnail",
    status_code=status.HTTP_200_OK,
    summary="Download attachment thumbnail",
    description="Download the thumbnail version of an attachment. Only participants can access.",
    responses={
        200: {"description": "Thumbnail image"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - not a participant"},
        404: {"description": "Thumbnail not found"},
    },
)
def download_thumbnail(
    attachment_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Download the thumbnail version of an attachment.

    Security:
    - Verifies user is conversation participant (IDOR prevention)
    - Sets X-Content-Type-Options: nosniff
    - Sets Content-Disposition: inline (thumbnails render in browser)
    """
    attachment = AttachmentService.get_attachment(db, attachment_id, current_user.id)

    if attachment.encryption_algorithm or not attachment.thumbnail_filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No thumbnail available for this attachment",
        )

    try:
        thumb_bytes = AttachmentService.get_thumbnail_bytes(attachment)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail file not found on disk",
        )

    headers = {
        "Content-Disposition": "inline",
        "X-Content-Type-Options": "nosniff",
        "Content-Length": str(len(thumb_bytes)),
    }

    return StreamingResponse(
        iter([thumb_bytes]),
        media_type="image/jpeg",  # thumbnails are always JPEG
        headers=headers,
    )


@router.delete(
    "/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete attachment",
    description="Delete an attachment. Only the uploader can delete their own attachment.",
    responses={
        204: {"description": "Attachment deleted"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - you can only delete your own attachments"},
        404: {"description": "Attachment not found"},
    },
)
def delete_attachment(
    attachment_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: Session = Depends(get_db),
) -> Response:
    """
    Delete an attachment.

    - Performs soft delete in the database (preserves audit trail)
    - Hard deletes the file from disk
    - Only the original uploader can delete
    - User must be a conversation participant (prevents IDOR)
    """
    AttachmentService.delete_attachment(db, attachment_id, current_user.id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

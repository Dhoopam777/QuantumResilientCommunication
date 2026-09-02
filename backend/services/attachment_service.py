"""
Attachment Service for Quantum-Resilient Communication System

Security-hardened file attachment operations. Implements:
- File size validation (max 10 MB, reject zero-byte)
- MIME type detection via magic bytes (server-side, never trust client)
- Extension validation (must match MIME, reject double extensions)
- Filename sanitization (strip path traversal, null bytes, encoded traversal)
- Image processing: EXIF stripping, re-encoding, decompression bomb detection
- Thumbnail generation server-side
- SHA-256 checksum (computed server-side, never trust client)
- Storage outside web root, never expose filesystem paths
- UUIDv4 filenames for on-disk storage
- Rate limiting and audit logging integration
- IDOR prevention via conversation membership checks
"""

import hashlib
import base64
import io
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from core.config import settings
from core.rate_limiter import rate_limiter
from core.audit_logger import (
    log_upload_success,
    log_upload_failure,
    log_auth_failure,
    log_invalid_mime,
    log_oversized_upload,
    log_rate_limited,
)
from models.attachment import Attachment
from models.message import Message
from services.conversation_service import is_participant


# ---------------------------------------------------------------------------
# MIME type detection via magic bytes
# ---------------------------------------------------------------------------

# Known magic byte signatures for Phase 8.1 allowed types
_MAGIC_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",  # WebP starts with RIFF....WEBP
}

# Mapping from detected MIME to allowed extension(s)
_MIME_TO_EXTENSIONS = {
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/webp": [".webp"],
    "audio/webm": [".webm"],
}

# Rejected extensions (executable / script types)
_BLOCKED_EXTENSIONS = {
    ".exe", ".dll", ".bat", ".cmd", ".ps1", ".jar", ".apk",
    ".php", ".js", ".html", ".svg", ".sh", ".com", ".msi",
    ".scr", ".vbs", ".wsf", ".hta", ".inf", ".reg",
}


class AttachmentService:
    """Service class for secure attachment operations."""

    # --- File size validation ---

    @staticmethod
    def validate_file_size(file_size: int) -> None:
        """
        Validate file size constraints.
        Rejects zero-byte files and files exceeding max size.
        """
        if file_size <= 0:
            raise ValueError("File is empty (zero bytes)")

        if file_size > settings.ATTACHMENT_MAX_SIZE_BYTES:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum "
                f"({settings.ATTACHMENT_MAX_SIZE_BYTES} bytes)"
            )

    # --- Filename sanitization ---

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a client-supplied filename for safe storage as metadata.

        Strips:
        - Path traversal sequences (../, ..\\, absolute paths)
        - Null bytes and null-byte injection
        - Encoded traversal sequences
        - Path separators
        - Double extensions that could be used to disguise executables
        """
        if not filename:
            raise ValueError("Filename is required")

        # Remove null bytes (null-byte injection)
        filename = filename.replace("\x00", "")

        # Take only the basename — strip any directory components
        # Handle both Unix and Windows path separators
        filename = os.path.basename(filename.replace("\\", "/"))

        # Check for encoded path traversal after basename extraction
        # Decode common encodings and re-check
        decoded = filename
        for _ in range(3):  # Handle double/triple encoding
            from urllib.parse import unquote
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded

        # Strip any remaining traversal attempts
        decoded = decoded.replace("../", "").replace("..\\", "")

        # Remove path separators that survived
        filename = re.sub(r'[\\/:*?"<>|]', '_', decoded)

        # Truncate to max length
        if len(filename) > settings.ATTACHMENT_MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            filename = name[:settings.ATTACHMENT_MAX_FILENAME_LENGTH - len(ext)] + ext

        if not filename or filename == "." or filename == "..":
            raise ValueError("Invalid filename after sanitization")

        return filename

    # --- MIME type detection ---

    @staticmethod
    def detect_mime_type(content: bytes) -> Optional[str]:
        """
        Detect MIME type from file content using magic bytes.
        Does NOT trust client-supplied Content-Type or filename extensions.
        """
        # Check PNG
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        # Check JPEG
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        # Check WebP (RIFF....WEBP)
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"

        return None

    @staticmethod
    def extract_extension(filename: str) -> str:
        """Extract lowercase extension including the dot, e.g. '.png'."""
        ext = os.path.splitext(filename)[1].lower()
        return ext

    @staticmethod
    def validate_extension(mime_type: str, extension: str) -> None:
        """
        Validate that the file extension matches the detected MIME type.
        Rejects double extensions and blocked extensions.
        """
        allowed = _MIME_TO_EXTENSIONS.get(mime_type, [])
        if extension not in allowed:
            raise ValueError(
                f"File extension '{extension}' does not match MIME type '{mime_type}'. "
                f"Allowed extensions: {', '.join(allowed)}"
            )

        # Check for double extensions (e.g., image.jpg.exe)
        parts = extension.split(".")
        if len(parts) > 2 or (len(parts) == 2 and parts[0] == ""):
            # Has a secondary extension — check all parts
            all_exts = [f".{p}" for p in parts[1:] if p]
            for ext in all_exts:
                if ext in _BLOCKED_EXTENSIONS:
                    raise ValueError(
                        f"Blocked file extension detected: '{ext}'. "
                        f"This may be a disguised executable."
                    )

        # Also check the full filename for any blocked extensions
        full_ext = os.path.splitext(filename_check := f"file{extension}")[1].lower()
        if full_ext in _BLOCKED_EXTENSIONS:
            raise ValueError(f"Blocked file extension: '{full_ext}'")

    @staticmethod
    def validate_no_double_extension(filename: str) -> None:
        """
        Explicitly check for double extension attacks like 'image.jpg.exe'.
        """
        # Strip the known extension, then check what remains
        name_without_ext = os.path.splitext(filename)[0]
        secondary_ext = os.path.splitext(name_without_ext)[1].lower()

        if secondary_ext:
            # There's a double extension — check if the secondary one is blocked
            if secondary_ext in _BLOCKED_EXTENSIONS:
                raise ValueError(
                    f"Double extension attack detected: '{filename}'. "
                    f"Secondary extension '{secondary_ext}' is blocked."
                )

    # --- Image processing ---

    @staticmethod
    def process_image(content: bytes, mime_type: str) -> tuple[bytes, Optional[bytes], Optional[int], Optional[int]]:
        """
        Process image for secure storage:
        1. Verify it's a valid image (reject malformed)
        2. Detect decompression bombs (Pillow raises DecompressionBombError)
        3. Strip ALL EXIF metadata (GPS, camera info, etc.)
        4. Re-encode image (removes hidden data in non-standard chunks)
        5. Return processed content; generate thumbnail

        Returns: (processed_content, thumbnail_content_or_None, width, height)
        """
        try:
            # Set a reasonable limit to prevent decompression bombs
            # Pillow's MAX_IMAGE_PIXELS helps detect oversized images
            Image.MAX_IMAGE_PIXELS = 50_000_000  # ~50 megapixels

            img = Image.open(io.BytesIO(content))

            # Verify this is actually an image (reject malformed)
            img.verify()

            # Re-open after verify (verify() invalidates the image)
            img = Image.open(io.BytesIO(content))

            # Convert to RGB if necessary (handles RGBA, P, L modes)
            if img.mode in ("RGBA", "P", "L", "LA"):
                img = img.convert("RGB")

            # Strip EXIF: recreate image without metadata
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)

            # Re-encode to the same format (removes EXIF, hidden chunks)
            output = io.BytesIO()
            if mime_type == "image/png":
                clean_img.save(output, format="PNG")
            elif mime_type == "image/jpeg":
                clean_img.save(output, format="JPEG", quality=92)
            elif mime_type == "image/webp":
                clean_img.save(output, format="WEBP", quality=92)

            processed_content = output.getvalue()
            width, height = clean_img.size

            # Verify re-encoded image is still valid
            if len(processed_content) == 0:
                raise ValueError("Image processing produced empty output")

            # Generate thumbnail
            thumbnail_content = AttachmentService._generate_thumbnail(
                processed_content, mime_type,
                settings.ATTACHMENT_THUMBNAIL_WIDTH,
                settings.ATTACHMENT_THUMBNAIL_HEIGHT,
            )

            return processed_content, thumbnail_content, width, height

        except Image.DecompressionBombError:
            raise ValueError("Image is too large (potential decompression bomb)")
        except Image.UnidentifiedImageError:
            raise ValueError("File is not a valid image")
        except Exception as e:
            raise ValueError(f"Image processing failed: {type(e).__name__}")

    @staticmethod
    def _generate_thumbnail(content: bytes, mime_type: str,
                           max_width: int, max_height: int) -> Optional[bytes]:
        """Generate a server-side thumbnail of the image."""
        try:
            img = Image.open(io.BytesIO(content))

            # Verify it's a valid image
            img.verify()
            img = Image.open(io.BytesIO(content))

            if img.mode in ("RGBA", "P", "L", "LA"):
                img = img.convert("RGB")

            img.thumbnail((max_width, max_height))

            output = io.BytesIO()
            if mime_type == "image/png":
                img.save(output, format="PNG")
            elif mime_type == "image/webp":
                img.save(output, format="WEBP", quality=85)
            else:
                img.save(output, format="JPEG", quality=85)

            return output.getvalue()
        except Exception:
            return None

    # --- Checksum ---

    @staticmethod
    def compute_checksum(content: bytes) -> str:
        """Compute SHA-256 checksum of file content (server-side only)."""
        return hashlib.sha256(content).hexdigest()

    # --- Storage ---

    @staticmethod
    def ensure_storage_dir() -> Path:
        """Ensure the storage directory exists (outside web root)."""
        storage_path = Path(settings.ATTACHMENT_STORAGE_PATH).resolve()
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    @staticmethod
    def generate_stored_filename(extension: str) -> str:
        """Generate a cryptographically random filename using UUIDv4."""
        return f"{uuid.uuid4().hex}{extension}"

    @staticmethod
    def save_file(content: bytes, stored_filename: str) -> Path:
        """
        Save file content to disk using the UUID-based filename.
        Never uses client-supplied filenames for storage.
        """
        storage_path = AttachmentService.ensure_storage_dir()
        file_path = storage_path / stored_filename

        # Write file atomically
        tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(file_path))

        return file_path

    @staticmethod
    def save_thumbnail(content: bytes, stored_filename: str) -> str:
        """Save thumbnail to disk and return its filename."""
        storage_path = AttachmentService.ensure_storage_dir()
        thumb_filename = AttachmentService.generate_stored_filename(".thumb.jpg")
        thumb_path = storage_path / thumb_filename

        tmp_path = thumb_path.with_suffix(".tmp")
        with open(tmp_path, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(thumb_path))

        return thumb_filename

    @staticmethod
    def get_file_path(stored_filename: str) -> Path:
        """Get the filesystem path for a stored file. Validates no path traversal."""
        # Ensure the stored_filename doesn't contain path traversal
        safe_name = os.path.basename(stored_filename)
        if safe_name != stored_filename:
            raise ValueError("Invalid stored filename (path traversal detected)")

        storage_path = AttachmentService.ensure_storage_dir()
        return storage_path / safe_name

    @staticmethod
    def delete_file(stored_filename: str) -> None:
        """Delete a file from disk."""
        file_path = AttachmentService.get_file_path(stored_filename)
        if file_path.exists():
            file_path.unlink()

    # --- Authorization ---

    @staticmethod
    def verify_conversation_access(db: Session, conversation_id: uuid.UUID,
                                   user_id: uuid.UUID) -> None:
        """
        Verify the user is an active participant of the conversation.
        Raises HTTPException 403 if not a participant.
        """
        if not is_participant(db, conversation_id, user_id):
            log_auth_failure(str(user_id), "conversation_access", str(conversation_id))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this conversation",
            )

    @staticmethod
    def verify_attachment_access(db: Session, attachment_id: uuid.UUID,
                                user_id: uuid.UUID) -> Attachment:
        """
        Verify the user can access an attachment (IDOR prevention).
        Checks that the user is an active participant in the attachment's conversation.
        Never trusts client-supplied attachment IDs without this check.
        """
        attachment = db.query(Attachment).filter(
            Attachment.id == attachment_id,
            Attachment.is_deleted == False,  # noqa: E712
        ).first()

        if attachment is None:
            log_auth_failure(str(user_id), "attachment_access", str(attachment_id))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found",
            )

        # Verify user is a participant in the conversation
        if not is_participant(db, attachment.conversation_id, user_id):
            log_auth_failure(str(user_id), "attachment_access", str(attachment_id))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this attachment",
            )

        return attachment

    @staticmethod
    def verify_ownership(db: Session, attachment: Attachment,
                         user_id: uuid.UUID) -> None:
        """
        Verify the user owns the attachment or is an admin.
        Used for delete operations.
        """
        if attachment.uploader_id != user_id:
            log_auth_failure(str(user_id), "delete", str(attachment.id))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete attachments you uploaded",
            )

    # --- Upload ---

    @staticmethod
    async def upload_attachment(
        db: Session,
        conversation_id: uuid.UUID,
        uploader_id: uuid.UUID,
        file: UploadFile,
        original_filename: str,
        encryption_algorithm: Optional[str] = None,
        declared_mime_type: Optional[str] = None,
        nonce: Optional[str] = None,
        authentication_tag: Optional[str] = None,
    ) -> Attachment:
        """
        Process and store an uploaded attachment with full security validation.

        Steps:
        1. Rate limit check
        2. Verify conversation access (auth)
        3. Read file content
        4. Validate file size
        5. Sanitize filename (path traversal, null bytes, double extensions)
        6. Detect MIME type via magic bytes
        7. Validate MIME type is allowed
        8. Validate extension matches MIME
        9. Validate no double extension attacks
        10. Process image (EXIF strip, re-encode, thumbnail, bomb detection)
        11. Compute SHA-256 checksum (server-side)
        12. Generate UUIDv4 stored filename
        13. Save file + thumbnail to disk
        14. Create DB record
        15. Log success

        Args:
            db: Database session
            conversation_id: UUID of the conversation
            uploader_id: UUID of the uploading user
            file: UploadFile from FastAPI
            original_filename: Client-supplied filename (sanitized before storage)

        Returns:
            Attachment: The created attachment record

        Raises:
            HTTPException: 403 (not a participant), 400 (validation), 429 (rate limit)
        """
        user_id_str = str(uploader_id)

        # Step 1: Rate limiting
        try:
            async with rate_limiter.upload_context(user_id_str):
                return await AttachmentService._do_upload(
                    db, conversation_id, uploader_id, file, original_filename,
                    encryption_algorithm, declared_mime_type, nonce, authentication_tag,
                )
        except HTTPException:
            log_rate_limited(user_id_str, "upload")
            raise

    @staticmethod
    async def _do_upload(
        db: Session,
        conversation_id: uuid.UUID,
        uploader_id: uuid.UUID,
        file: UploadFile,
        original_filename: str,
        encryption_algorithm: Optional[str] = None,
        declared_mime_type: Optional[str] = None,
        nonce: Optional[str] = None,
        authentication_tag: Optional[str] = None,
    ) -> Attachment:
        """Internal upload processing — called within rate limit context."""

        # Step 2: Authorization — verify conversation access
        AttachmentService.verify_conversation_access(db, conversation_id, uploader_id)

        # Step 3: Read file content
        content = await file.read()
        file_size = len(content)

        # Step 4: Validate file size
        try:
            AttachmentService.validate_file_size(file_size)
        except ValueError as e:
            log_oversized_upload(str(uploader_id), file_size)
            log_upload_failure(str(uploader_id), str(conversation_id), str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Step 5: Sanitize filename
        safe_filename = AttachmentService.sanitize_filename(original_filename)

        # Step 6: Validate filename length
        if len(safe_filename) > settings.ATTACHMENT_MAX_FILENAME_LENGTH:
            log_upload_failure(str(uploader_id), str(conversation_id), "filename too long")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is too long (max 255 characters)",
            )

        if encryption_algorithm:
            if encryption_algorithm != "AES-256-GCM":
                raise HTTPException(status_code=400, detail="Unsupported encryption algorithm")
            if not declared_mime_type or declared_mime_type not in settings.ATTACHMENT_ALLOWED_MIME_TYPES:
                raise HTTPException(status_code=400, detail="Unsupported attachment MIME type")
            if not nonce or not authentication_tag:
                raise HTTPException(status_code=400, detail="Encrypted attachment envelope incomplete")
            try:
                if len(base64.b64decode(nonce, validate=True)) != 12:
                    raise ValueError
                if len(base64.b64decode(authentication_tag, validate=True)) != 16:
                    raise ValueError
            except (ValueError, base64.binascii.Error) as exc:
                raise HTTPException(status_code=400, detail="Invalid encrypted attachment envelope") from exc
            mime_type = declared_mime_type
            extension = AttachmentService.extract_extension(safe_filename)
            try:
                AttachmentService.validate_extension(mime_type, extension)
                AttachmentService.validate_no_double_extension(safe_filename)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            checksum = AttachmentService.compute_checksum(content)
            stored_filename = AttachmentService.generate_stored_filename(extension)
            AttachmentService.save_file(content, stored_filename)
            attachment = Attachment(
                conversation_id=conversation_id,
                uploader_id=uploader_id,
                stored_filename=stored_filename,
                original_filename=safe_filename,
                mime_type=mime_type,
                file_extension=extension,
                file_size=file_size,
                checksum_sha256=checksum,
                encryption_algorithm=encryption_algorithm,
                nonce=nonce,
                authentication_tag=authentication_tag,
                encrypted_size=file_size,
            )
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
            log_upload_success(
                str(uploader_id), str(attachment.id), str(conversation_id),
                safe_filename, file_size,
            )
            return attachment

        # Step 7: Detect MIME type via magic bytes
        mime_type = AttachmentService.detect_mime_type(content)

        if mime_type is None:
            log_invalid_mime(str(uploader_id), file.content_type or "unknown", "unknown")
            log_upload_failure(str(uploader_id), str(conversation_id), "invalid MIME type")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type not allowed. Only PNG, JPEG, and WebP images are accepted.",
            )

        # Check MIME against allowed types
        if mime_type not in settings.ATTACHMENT_ALLOWED_MIME_TYPES:
            log_invalid_mime(str(uploader_id), "declared", mime_type)
            log_upload_failure(str(uploader_id), str(conversation_id), f"MIME not allowed: {mime_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File type not allowed. Only PNG, JPEG, and WebP images are accepted.",
            )

        # Step 8: Validate extension
        extension = AttachmentService.extract_extension(safe_filename)
        try:
            AttachmentService.validate_extension(mime_type, extension)
        except ValueError as e:
            log_upload_failure(str(uploader_id), str(conversation_id), str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Step 9: Check for double extensions
        try:
            AttachmentService.validate_no_double_extension(safe_filename)
        except ValueError as e:
            log_upload_failure(str(uploader_id), str(conversation_id), str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Step 10: Process image (EXIF strip, re-encode, thumbnail, bomb detection)
        try:
            processed_content, thumbnail_content, width, height = (
                AttachmentService.process_image(content, mime_type)
            )
        except ValueError as e:
            log_upload_failure(str(uploader_id), str(conversation_id), str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Validate metadata length
        if len(safe_filename) > settings.ATTACHMENT_MAX_METADATA_LENGTH:
            log_upload_failure(str(uploader_id), str(conversation_id), "metadata too long")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename metadata exceeds maximum length",
            )

        # Step 11: Compute SHA-256 checksum (server-side)
        checksum = AttachmentService.compute_checksum(processed_content)

        # Step 12: Generate UUIDv4 stored filename
        stored_filename = AttachmentService.generate_stored_filename(extension)

        # Step 13: Save file to disk
        AttachmentService.save_file(processed_content, stored_filename)

        # Save thumbnail
        thumb_filename = None
        if thumbnail_content:
            thumb_filename = AttachmentService.save_thumbnail(thumbnail_content, stored_filename)

        # Step 14: Create DB record
        attachment = Attachment(
            conversation_id=conversation_id,
            uploader_id=uploader_id,
            stored_filename=stored_filename,
            original_filename=safe_filename,
            mime_type=mime_type,
            file_extension=extension,
            file_size=len(processed_content),
            checksum_sha256=checksum,
            width=width,
            height=height,
            thumbnail_filename=thumb_filename,
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        # Step 15: Log success
        log_upload_success(
            str(uploader_id), str(attachment.id), str(conversation_id),
            safe_filename, len(processed_content),
        )

        return attachment

    # --- Retrieval ---

    @staticmethod
    def get_attachment(db: Session, attachment_id: uuid.UUID,
                      user_id: uuid.UUID) -> Attachment:
        """
        Retrieve an attachment after verifying access.
        Prevents IDOR — only participants of the conversation can access.
        """
        return AttachmentService.verify_attachment_access(db, attachment_id, user_id)

    @staticmethod
    def get_attachment_bytes(attachment: Attachment) -> bytes:
        """Read attachment file content from disk for serving."""
        file_path = AttachmentService.get_file_path(attachment.stored_filename)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment file not found on disk",
            )
        return file_path.read_bytes()

    @staticmethod
    def get_thumbnail_bytes(attachment: Attachment) -> bytes:
        """Read thumbnail file content from disk for serving."""
        if not attachment.thumbnail_filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No thumbnail available",
            )
        file_path = AttachmentService.get_file_path(attachment.thumbnail_filename)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thumbnail file not found on disk",
            )
        return file_path.read_bytes()

    # --- Delete ---

    @staticmethod
    def delete_attachment(db: Session, attachment_id: uuid.UUID,
                         user_id: uuid.UUID) -> None:
        """
        Delete an attachment (soft delete in DB + hard delete on disk).
        Only the uploader can delete their own attachment.
        """
        attachment = AttachmentService.verify_attachment_access(db, attachment_id, user_id)
        AttachmentService.verify_ownership(db, attachment, user_id)

        # Soft delete in DB
        attachment.is_deleted = True
        attachment.deleted_at = datetime.now(timezone.utc)

        # Hard delete file from disk
        try:
            AttachmentService.delete_file(attachment.stored_filename)
        except Exception:
            # Log but don't fail — DB record is still soft-deleted
            pass

        # Delete thumbnail
        if attachment.thumbnail_filename:
            try:
                AttachmentService.delete_file(attachment.thumbnail_filename)
            except Exception:
                pass

        db.commit()


# Convenience functions for direct usage (matching project patterns)
async def upload_attachment(
    db: Session,
    conversation_id: uuid.UUID,
    uploader_id: uuid.UUID,
    file: UploadFile,
    original_filename: str,
    encryption_algorithm: Optional[str] = None,
    declared_mime_type: Optional[str] = None,
    nonce: Optional[str] = None,
    authentication_tag: Optional[str] = None,
) -> Attachment:
    """Convenience function to upload an attachment."""
    return await AttachmentService.upload_attachment(
        db=db,
        conversation_id=conversation_id,
        uploader_id=uploader_id,
        file=file,
        original_filename=original_filename,
        encryption_algorithm=encryption_algorithm,
        declared_mime_type=declared_mime_type,
        nonce=nonce,
        authentication_tag=authentication_tag,
    )


def get_attachment(db: Session, attachment_id: uuid.UUID, user_id: uuid.UUID) -> Attachment:
    """Convenience function to get an attachment."""
    return AttachmentService.get_attachment(db, attachment_id, user_id)


def delete_attachment(db: Session, attachment_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Convenience function to delete an attachment."""
    AttachmentService.delete_attachment(db, attachment_id, user_id)

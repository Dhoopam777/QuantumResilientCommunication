"""Client-encrypted attachment storage tests."""

import base64
from io import BytesIO

import pytest
from fastapi import UploadFile

from core.config import settings
from services.attachment_service import AttachmentService


def _b64(size: int) -> str:
    return base64.b64encode(bytes(range(size))).decode("ascii")


@pytest.mark.asyncio
async def test_encrypted_upload_stores_ciphertext_without_inspection(
    db_session, test_user, test_conversation, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_PATH", str(tmp_path))
    ciphertext = b"not-a-real-png-but-valid-ciphertext"
    upload = UploadFile(filename="photo.png", file=BytesIO(ciphertext))

    attachment = await AttachmentService.upload_attachment(
        db=db_session,
        conversation_id=test_conversation.id,
        uploader_id=test_user.id,
        file=upload,
        original_filename="photo.png",
        encryption_algorithm="AES-256-GCM",
        declared_mime_type="image/png",
        nonce=_b64(12),
        authentication_tag=_b64(16),
    )

    assert attachment.encryption_algorithm == "AES-256-GCM"
    assert attachment.encrypted_size == len(ciphertext)
    assert attachment.thumbnail_filename is None
    assert AttachmentService.get_attachment_bytes(attachment) == ciphertext


@pytest.mark.asyncio
async def test_encrypted_upload_rejects_invalid_envelope(
    db_session, test_user, test_conversation
):
    upload = UploadFile(filename="photo.png", file=BytesIO(b"ciphertext"))

    with pytest.raises(Exception):
        await AttachmentService.upload_attachment(
            db=db_session,
            conversation_id=test_conversation.id,
            uploader_id=test_user.id,
            file=upload,
            original_filename="photo.png",
            encryption_algorithm="AES-256-GCM",
            declared_mime_type="image/png",
            nonce=_b64(11),
            authentication_tag=_b64(16),
        )


@pytest.mark.asyncio
async def test_encrypted_webm_audio_is_stored_as_ciphertext(
    db_session, test_user, test_conversation, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "ATTACHMENT_STORAGE_PATH", str(tmp_path))
    ciphertext = b"not-plaintext-webm"
    upload = UploadFile(filename="voice.webm", file=BytesIO(ciphertext))

    attachment = await AttachmentService.upload_attachment(
        db=db_session,
        conversation_id=test_conversation.id,
        uploader_id=test_user.id,
        file=upload,
        original_filename="voice.webm",
        encryption_algorithm="AES-256-GCM",
        declared_mime_type="audio/webm",
        nonce=_b64(12),
        authentication_tag=_b64(16),
    )

    assert attachment.mime_type == "audio/webm"
    assert AttachmentService.get_attachment_bytes(attachment) == ciphertext

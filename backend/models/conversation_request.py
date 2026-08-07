"""Conversation request persistence model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UUID, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class ConversationRequest(Base):
    """A username-targeted request that must be accepted before chat exists."""

    __tablename__ = "conversation_requests"
    __table_args__ = (
        UniqueConstraint("sender_id", "receiver_id", name="uq_conversation_request_pair"),
        Index("ix_conversation_requests_sender_id", "sender_id"),
        Index("ix_conversation_requests_receiver_id", "receiver_id"),
        Index("ix_conversation_requests_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    receiver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], back_populates="sent_conversation_requests")
    receiver: Mapped["User"] = relationship("User", foreign_keys=[receiver_id], back_populates="received_conversation_requests")

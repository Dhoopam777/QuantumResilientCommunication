"""
Rate Limiter for Attachment Uploads

Simple in-memory rate limiter — no Redis dependency.
Sufficient for single-server production deployment.
Tracks uploads per user per minute and concurrent uploads per user.
"""

import time
import threading
from collections import defaultdict
from contextlib import asynccontextmanager

from core.config import settings


class RateLimiter:
    """In-memory rate limiter for attachment uploads and message edits."""

    def __init__(
        self,
        max_uploads_per_minute: int = settings.ATTACHMENT_UPLOAD_RATE_LIMIT,
        max_concurrent: int = settings.ATTACHMENT_MAX_CONCURRENT_UPLOADS,
        max_edits_per_minute: int = settings.MESSAGE_EDIT_RATE_LIMIT,
        max_deletes_per_minute: int = settings.MESSAGE_DELETE_RATE_LIMIT,
        max_reactions_per_minute: int = settings.MESSAGE_REACTION_RATE_LIMIT,
        max_requests_per_day: int = settings.CONVERSATION_REQUESTS_PER_DAY,
    ):
        self.max_uploads_per_minute = max_uploads_per_minute
        self.max_concurrent = max_concurrent
        self.max_edits_per_minute = max_edits_per_minute
        self.max_deletes_per_minute = max_deletes_per_minute
        self.max_reactions_per_minute = max_reactions_per_minute
        self.max_requests_per_day = max_requests_per_day
        self._upload_times: dict[str, list[float]] = defaultdict(list)
        self._concurrent: dict[str, int] = defaultdict(int)
        self._edit_times: dict[str, list[float]] = defaultdict(list)
        self._delete_times: dict[str, list[float]] = defaultdict(list)
        self._reaction_times: dict[str, list[float]] = defaultdict(list)
        self._request_times: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup_old(self, user_id: str, now: float) -> None:
        """Remove upload timestamps older than 60 seconds."""
        self._upload_times[user_id] = [
            t for t in self._upload_times[user_id] if now - t < 60.0
        ]

    def check_upload_rate(self, user_id: str) -> None:
        """
        Check if user is within upload rate limits.
        Raises HTTPException 429 if exceeded.
        """
        from fastapi import HTTPException, status

        with self._lock:
            now = time.time()
            self._cleanup_old(user_id, now)

            if len(self._upload_times[user_id]) >= self.max_uploads_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Upload rate limit exceeded. Maximum {self.max_uploads_per_minute} "
                    f"uploads per minute.",
                    headers={"Retry-After": "60"},
                )

            self._upload_times[user_id].append(now)

    def _cleanup_old_edits(self, user_id: str, now: float) -> None:
        """Remove edit timestamps older than 60 seconds."""
        self._edit_times[user_id] = [
            t for t in self._edit_times[user_id] if now - t < 60.0
        ]

    def check_edit_rate(self, user_id: str) -> None:
        """
        Check if user is within message edit rate limits.
        Raises HTTPException 429 if exceeded.
        """
        from fastapi import HTTPException, status

        with self._lock:
            now = time.time()
            self._cleanup_old_edits(user_id, now)

            if len(self._edit_times[user_id]) >= self.max_edits_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Message edit rate limit exceeded. Maximum {self.max_edits_per_minute} "
                    f"edits per minute.",
                    headers={"Retry-After": "60"},
                )

            self._edit_times[user_id].append(now)

    def _cleanup_old_deletes(self, user_id: str, now: float) -> None:
        """Remove delete timestamps older than 60 seconds."""
        self._delete_times[user_id] = [
            t for t in self._delete_times[user_id] if now - t < 60.0
        ]

    def check_delete_rate(self, user_id: str) -> None:
        """
        Check if user is within message delete rate limits.
        Raises HTTPException 429 if exceeded.
        """
        from fastapi import HTTPException, status

        with self._lock:
            now = time.time()
            self._cleanup_old_deletes(user_id, now)

            if len(self._delete_times[user_id]) >= self.max_deletes_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Message delete rate limit exceeded. Maximum {self.max_deletes_per_minute} "
                    f"deletes per minute.",
                    headers={"Retry-After": "60"},
                )

            self._delete_times[user_id].append(now)

    def check_concurrent(self, user_id: str) -> None:
        """
        Check if user has exceeded concurrent upload limit.
        Raises HTTPException 429 if exceeded.
        """
        from fastapi import HTTPException, status

        with self._lock:
            if self._concurrent[user_id] >= self.max_concurrent:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many concurrent uploads. Maximum {self.max_concurrent} "
                    f"concurrent uploads allowed.",
                )
            self._concurrent[user_id] += 1

    def check_reaction_rate(self, user_id: str) -> None:
        """Check the per-user reaction mutation limit."""
        from fastapi import HTTPException, status

        with self._lock:
            now = time.time()
            self._reaction_times[user_id] = [
                t for t in self._reaction_times[user_id] if now - t < 60.0
            ]
            if len(self._reaction_times[user_id]) >= self.max_reactions_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Reaction rate limit exceeded",
                    headers={"Retry-After": "60"},
                )
            self._reaction_times[user_id].append(now)

    def check_conversation_request_rate(self, user_id: str) -> None:
        """Enforce the daily anti-spam request quota."""
        from fastapi import HTTPException, status

        with self._lock:
            now = time.time()
            self._request_times[user_id] = [
                t for t in self._request_times[user_id] if now - t < 86400.0
            ]
            if len(self._request_times[user_id]) >= self.max_requests_per_day:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Conversation request limit exceeded",
                    headers={"Retry-After": "86400"},
                )
            self._request_times[user_id].append(now)

    def release_concurrent(self, user_id: str) -> None:
        """Release a concurrent upload slot."""
        with self._lock:
            self._concurrent[user_id] = max(0, self._concurrent[user_id] - 1)

    @asynccontextmanager
    async def upload_context(self, user_id: str):
        """
        Context manager that enforces both rate and concurrency limits.
        Usage:
            async with rate_limiter.upload_context(str(user_id)):
                ...process upload...
        """
        self.check_upload_rate(user_id)
        self.check_concurrent(user_id)
        try:
            yield
        finally:
            self.release_concurrent(user_id)


# Global singleton instance
rate_limiter = RateLimiter()

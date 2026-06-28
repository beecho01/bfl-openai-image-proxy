"""Temporary storage for generated images served via /generated/{filename}."""
import asyncio
import logging
import os
import time
import uuid
from typing import Optional

from .config import Settings

logger = logging.getLogger("bfl-proxy")


class ImageStorage:
    """Manages temporary generated image files with TTL cleanup."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.dir = settings.generated_dir
        self._cleanup_task: Optional[asyncio.Task] = None

    def ensure_dir(self) -> None:
        os.makedirs(self.dir, exist_ok=True)

    def save_image(self, data: bytes, ext: str = "png") -> str:
        """Save image bytes to disk and return the filename. Respects STORE_GENERATED_IMAGES."""
        self.ensure_dir()
        if not self.settings.store_generated_images:
            # still save temporarily so we can serve it; cleanup will remove it
            pass
        filename = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(self.dir, filename)
        with open(path, "wb") as fh:
            fh.write(data)
        return filename

    def full_path(self, filename: str) -> str:
        return os.path.join(self.dir, filename)

    def exists(self, filename: str) -> bool:
        return os.path.isfile(self.full_path(filename))

    def start_cleanup_task(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("cleanup task error: %s", exc)

    def cleanup_expired(self) -> int:
        if not os.path.isdir(self.dir):
            return 0
        now = time.time()
        removed = 0
        for name in os.listdir(self.dir):
            path = os.path.join(self.dir, name)
            try:
                if os.path.isfile(path) and (now - os.path.getmtime(path)) > self.settings.image_ttl_seconds:
                    os.remove(path)
                    removed += 1
            except OSError:
                continue
        if removed:
            logger.info("cleaned up %d expired generated image(s)", removed)
        return removed
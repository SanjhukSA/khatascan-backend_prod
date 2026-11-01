"""Background cleanup of uploads that were never saved as a receipt."""

import asyncio
import logging
import re
import time
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import Receipt, ReceiptPage

log = logging.getLogger("receipts.cleanup")

# Only files this app created: <uuid>.jpg and <uuid>_thumb.jpg
_UPLOAD_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(_thumb)?\.jpg$")


def cleanup_orphan_uploads(upload_dir: str, max_age_hours: float, session_factory=SessionLocal) -> int:
    """
    Delete uploaded images older than `max_age_hours` that no saved receipt
    points at. Returns how many files were removed.

    The age limit protects an upload that's in the middle of being reviewed.
    """
    base = Path(upload_dir)
    if not base.is_dir():
        return 0

    db = session_factory()
    try:
        rows = db.query(Receipt.image_path, Receipt.thumbnail_path).all()
        rows += db.query(ReceiptPage.image_path, ReceiptPage.thumbnail_path).all()
    finally:
        db.close()
    referenced = {p for row in rows for p in row if p}

    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for path in base.iterdir():
        if not path.is_file() or not _UPLOAD_NAME.match(path.name):
            continue
        if path.name in referenced:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        except OSError as exc:
            log.warning("Could not remove %s: %s", path, exc)
    return removed


async def cleanup_loop() -> None:
    """Run the cleanup on a fixed interval until cancelled (started from main.lifespan)."""
    interval = max(1, settings.cleanup_interval_minutes) * 60
    while True:
        try:
            removed = await asyncio.to_thread(
                cleanup_orphan_uploads, settings.upload_dir, settings.pending_upload_ttl_hours
            )
            if removed:
                log.info("Removed %d orphaned upload file(s)", removed)
        except Exception:
            log.exception("Upload cleanup failed")
        await asyncio.sleep(interval)

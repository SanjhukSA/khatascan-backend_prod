"""Background cleanup of uploads that were never saved as a receipt."""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import Receipt, ReceiptPage, Upload

log = logging.getLogger("receipts.cleanup")

# Only files this app created: <uuid>.jpg and <uuid>_thumb.jpg
_UPLOAD_NAME = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(_thumb)?\.jpg$")


def _stem(filename: str) -> str:
    return filename.split(".")[0].removesuffix("_thumb")


def _unlink(path: Path) -> int:
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
            return 1
    except OSError as exc:
        log.warning("Could not remove %s: %s", path, exc)
    return 0


def cleanup_orphan_uploads(upload_dir: str, max_age_hours: float, session_factory=SessionLocal) -> int:
    """
    Delete uploads older than `max_age_hours` that no saved receipt points at.
    Returns how many files were removed.

    1. Pending uploads (rows in `uploads`) past the age limit: delete files and rows.
    2. Leftover files with no row at all (made before the table existed, or whose owner
       was deleted) and an old modification time.
    The age limit protects an upload that is in the middle of being reviewed.
    """
    base = Path(upload_dir)
    if not base.is_dir():
        return 0

    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    cutoff_ts = time.time() - max_age_hours * 3600
    removed = 0

    db = session_factory()
    try:
        rows = db.query(Receipt.image_path, Receipt.thumbnail_path).all()
        rows += db.query(ReceiptPage.image_path, ReceiptPage.thumbnail_path).all()
        referenced = {p for row in rows for p in row if p}

        pending = {str(r.id) for r in db.query(Upload.id).all()}
        expired = [r.id for r in db.query(Upload.id).filter(Upload.created_at < cutoff_dt).all()]

        for upload_id in expired:
            for name in (f"{upload_id}.jpg", f"{upload_id}_thumb.jpg"):
                if name not in referenced:
                    removed += _unlink(base / name)
        if expired:
            db.query(Upload).filter(Upload.id.in_(expired)).delete(synchronize_session=False)
            db.commit()
    finally:
        db.close()

    for path in base.iterdir():
        if not path.is_file() or not _UPLOAD_NAME.match(path.name):
            continue
        if path.name in referenced or _stem(path.name) in pending:
            continue
        try:
            if path.stat().st_mtime < cutoff_ts:
                removed += _unlink(path)
        except OSError as exc:
            log.warning("Could not check %s: %s", path, exc)
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

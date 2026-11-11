"""Duplicate detection for receipts. Two layers, both advisory (neither blocks saving):

1. Exact re-send: SHA-256 of the stored image, compared with saved pages.
2. Same purchase, different photo: same seller + printed date + total (within a paisa),
   or the same seller GSTIN + invoice number.
"""

import hashlib
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Receipt, ReceiptPage

_UNKNOWN_VENDOR = "unknown vendor"
_PAISA = 0.011   # a hair over 0.01 so float noise (118.01 - 118) still matches


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_receipt_by_hash(db: Session, digest: str) -> Optional[UUID]:
    """The saved receipt that already holds an identical page image, if any."""
    row = db.query(ReceiptPage.receipt_id).filter(ReceiptPage.content_hash == digest).first()
    return row.receipt_id if row else None


def find_possible_duplicate(db: Session, extracted: dict) -> Optional[Tuple[UUID, str]]:
    """
    Look for an already-saved receipt that this extraction probably duplicates.
    Returns (receipt_id, human-readable warning) or None.
    """
    gstin, invoice = extracted.get("vendor_gstin"), extracted.get("invoice_number")
    if gstin and invoice:
        row = db.query(Receipt.id).filter(
            Receipt.vendor_gstin == gstin, Receipt.invoice_number == invoice
        ).first()
        if row:
            return row.id, "This invoice (same seller GSTIN and invoice number) is already saved."

    day, total = extracted.get("receipt_date"), extracted.get("total") or 0
    if not day or total <= 0:
        return None

    vendor = (extracted.get("vendor_name") or "").strip().lower()
    same_seller = []
    if vendor and vendor != _UNKNOWN_VENDOR:
        same_seller.append(func.lower(func.trim(Receipt.vendor_name)) == vendor)
    if gstin:
        same_seller.append(Receipt.vendor_gstin == gstin)
    if not same_seller:
        return None            # date + total alone is too weak a match

    row = (
        db.query(Receipt.id)
        .filter(
            Receipt.receipt_date == day,
            Receipt.currency == extracted.get("currency", "INR"),
            Receipt.total.between(total - _PAISA, total + _PAISA),
            or_(*same_seller),
        )
        .order_by(Receipt.created_at.desc())
        .first()
    )
    if not row:
        return None
    return row.id, (
        f"You already saved a receipt from {extracted.get('vendor_name')} on {day} for "
        f"{total:.2f}. Save this one only if it's a different purchase."
    )
"""Receipt endpoints: upload, process (OCR), save, list, detail, update, delete."""

from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app import schemas
from app.config import settings
from app.decision import REJECTED, decide
from app.dependencies import get_db
from app.merge import MergeError, merge_pages
from app.models import Receipt, ReceiptItem, ReceiptPage
from app.normalize import parse_date
from app.ocr import OcrEngine, save_upload

router = APIRouter(prefix="/receipts", tags=["receipts"])

# ── Singleton OCR engine ─────────────────────────────────────────────────
_ocr_engine = None


def get_ocr_engine() -> OcrEngine:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OcrEngine(api_key=settings.gemini_api_key, model=settings.gemini_model)
    return _ocr_engine


# Columns the list endpoint may sort by (anything else → 422, never getattr).
_SORTABLE = {
    "created_at": Receipt.created_at,
    "receipt_date": Receipt.receipt_date,
    "total": Receipt.total,
    "vendor_name": Receipt.vendor_name,
}

# PATCH ignores an explicit null for these (they can't be empty in the DB).
_NOT_NULLABLE = {
    "vendor_name", "document_type", "total", "tax_total",
    "discount_total", "currency", "category", "needs_review",
}


# ═════════════════════════════════════════════════════════════════════════
#  Step 1: Upload image (no OCR, no Gemini cost)
# ═════════════════════════════════════════════════════════════════════════

@router.post("/upload", response_model=schemas.UploadResponse)
async def upload_receipt(file: UploadFile = File(...)):
    """
    Upload a receipt image. Returns an upload_id to pass to
    /receipts/{upload_id}/process. No Gemini call is made here.
    Uploads that are never saved are deleted automatically (see cleanup.py).
    """
    # Read at most limit+1 bytes: an oversized file is rejected without loading all of it.
    image_bytes = await file.read(settings.max_upload_bytes + 1)

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    if len(image_bytes) > settings.max_upload_bytes:
        mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File too large. Maximum is {mb} MB.")

    try:
        upload_id, _, _ = await run_in_threadpool(save_upload, image_bytes, settings.upload_dir)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(
            status_code=415,
            detail="Unsupported or corrupt image. Please upload a JPEG or PNG photo.",
        )

    return schemas.UploadResponse(
        upload_id=upload_id,
        filename=file.filename or "receipt.jpg",
        size_kb=round(len(image_bytes) / 1024, 1),
    )


# ═════════════════════════════════════════════════════════════════════════
#  Step 2: Process (run OCR on a previously uploaded image)
# ═════════════════════════════════════════════════════════════════════════

@router.post("/{upload_id}/process", response_model=schemas.ProcessResponse)
async def process_receipt(
    upload_id: UUID,
    force: bool = Query(
        False,
        description="User override: treat a rejected menu/ID/other image as a receipt (still flagged for review).",
    ),
):
    """
    Run OCR on one uploaded image, then apply the accept / needs_review / rejected
    policy (app/decision.py). Nothing is saved here.
    HTTP 200 is returned for all three statuses; check `status` in the body.
    For an invoice that spans several images use POST /receipts/process-pages.
    """
    extracted = await _extract_page(upload_id)
    verdict = decide(extracted, force=force)
    return _to_process_response([upload_id], extracted, verdict)


@router.post("/process-pages", response_model=schemas.ProcessResponse)
async def process_pages(
    body: schemas.ProcessPagesRequest,
    force: bool = Query(False, description="Same override as the single-page endpoint."),
):
    """
    Run OCR on every page of one invoice and merge them into a single result:
    items are concatenated in page order, header fields come from the first page,
    and the grand total from the last. Missing or repeated pages are reported.

    The response's `upload_ids` are in document order. Pass them, in that order,
    to POST /receipts. Pages of different invoices, or a page uploaded twice, give 422.
    """
    pages = []
    for n, upload_id in enumerate(body.upload_ids, start=1):
        pages.append(await _extract_page(upload_id, f" for page {n}"))

    try:
        merged = merge_pages(pages)
    except MergeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ordered_ids = [body.upload_ids[i] for i in merged["page_order"]]
    verdict = decide(merged, force=force)
    return _to_process_response(ordered_ids, merged, verdict)


# ═════════════════════════════════════════════════════════════════════════
#  Step 3: Save confirmed receipt to database
# ═════════════════════════════════════════════════════════════════════════

@router.post("", response_model=schemas.ReceiptOut, status_code=201)
def save_receipt(body: schemas.ReceiptCreate, db: Session = Depends(get_db)):
    """
    Save a user-confirmed receipt. `upload_ids` are its pages, in order.
    Called after the user reviews/edits the OCR result.
    Returns 409 if any upload was already saved or the same invoice
    (seller GSTIN + invoice number) already exists.
    """
    image_names = [f"{u}.jpg" for u in body.upload_ids]
    thumb_names = [f"{u}_thumb.jpg" for u in body.upload_ids]

    for n, name in enumerate(image_names, start=1):
        if not _stored_file(name).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Upload image for page {n} not found. Please re-upload it.",
            )

    if db.query(ReceiptPage.id).filter(ReceiptPage.image_path.in_(image_names)).first():
        raise HTTPException(status_code=409, detail="One of these uploads was already saved as a receipt.")

    if body.vendor_gstin and body.invoice_number:
        dup = (
            db.query(Receipt.id)
            .filter(
                Receipt.vendor_gstin == body.vendor_gstin,
                Receipt.invoice_number == body.invoice_number,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=409,
                detail=f"This invoice was already saved (receipt {dup.id}).",
            )

    receipt = Receipt(
        vendor_name=body.vendor_name,
        vendor_gstin=body.vendor_gstin,
        invoice_number=body.invoice_number,
        document_type=body.document_type,
        date=body.date,
        receipt_date=body.receipt_date or parse_date(body.date),
        total=body.total,
        tax_total=body.tax_total,
        discount_total=body.discount_total,
        currency=body.currency,
        category=body.category,
        confidence=body.confidence,
        needs_review=body.needs_review,
        review_reason=body.review_reason,
        total_auto_corrected=body.total_auto_corrected,
        raw_ocr_text=body.raw_ocr_text,
        image_path=image_names[0],
        thumbnail_path=thumb_names[0],
        items=[ReceiptItem(position=i, **item.model_dump()) for i, item in enumerate(body.items)],
        pages=[
            ReceiptPage(page_number=n, image_path=img, thumbnail_path=thumb)
            for n, (img, thumb) in enumerate(zip(image_names, thumb_names), start=1)
        ],
    )
    db.add(receipt)
    try:
        db.commit()   # receipt + items + pages in one transaction: all or nothing
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This receipt was already saved.")
    db.refresh(receipt)
    return _receipt_to_out(receipt)


# ═════════════════════════════════════════════════════════════════════════
#  CRUD: list, detail, update, delete
# ═════════════════════════════════════════════════════════════════════════

@router.get("", response_model=schemas.PaginatedReceipts)
def list_receipts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    needs_review: Optional[bool] = Query(None),
    q: Optional[str] = Query(None, max_length=100, description="Search vendor name or invoice number"),
    sort: str = Query("-created_at", description="One of: created_at, receipt_date, total, vendor_name (prefix - for descending)"),
    db: Session = Depends(get_db),
):
    """List receipts with pagination, filters, search and whitelisted sorting."""
    key = sort.lstrip("-")
    if key not in _SORTABLE:
        raise HTTPException(status_code=422, detail=f"Cannot sort by '{key}'. Allowed: {', '.join(_SORTABLE)}")

    query = db.query(Receipt)
    if category:
        query = query.filter(Receipt.category == category)
    if document_type:
        query = query.filter(Receipt.document_type == document_type)
    if needs_review is not None:
        query = query.filter(Receipt.needs_review == needs_review)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Receipt.vendor_name.ilike(like) | Receipt.invoice_number.ilike(like))

    col = _SORTABLE[key]
    query = query.order_by(col.desc() if sort.startswith("-") else col.asc(), Receipt.id)

    total = query.count()
    pages = max(1, -(-total // per_page))  # ceiling division
    receipts = (
        query.options(selectinload(Receipt.items))   # one extra query instead of one per receipt
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return schemas.PaginatedReceipts(
        items=[_receipt_to_out(r) for r in receipts],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{receipt_id}", response_model=schemas.ReceiptOut)
def get_receipt(receipt_id: UUID, db: Session = Depends(get_db)):
    """Get a single receipt by ID."""
    return _receipt_to_out(_get_or_404(db, receipt_id))


@router.patch("/{receipt_id}", response_model=schemas.ReceiptOut)
def update_receipt(receipt_id: UUID, body: schemas.ReceiptUpdate, db: Session = Depends(get_db)):
    """Partial update. If `items` is sent, it replaces all existing items."""
    receipt = _get_or_404(db, receipt_id)

    update_data = body.model_dump(exclude_unset=True)
    items_data = update_data.pop("items", None)

    for field in list(update_data):
        if update_data[field] is None and field in _NOT_NULLABLE:
            del update_data[field]

    # Editing the printed date re-derives the real date, unless a real date was sent too.
    if "date" in update_data and "receipt_date" not in update_data:
        update_data["receipt_date"] = parse_date(update_data["date"])

    for field, value in update_data.items():
        setattr(receipt, field, value)

    if items_data is not None:
        receipt.items = [
            ReceiptItem(position=i, **item)
            for i, item in enumerate(items_data)
        ]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another receipt already has this seller GSTIN + invoice number.")
    db.refresh(receipt)
    return _receipt_to_out(receipt)


@router.delete("/{receipt_id}", status_code=204)
def delete_receipt(receipt_id: UUID, db: Session = Depends(get_db)):
    """Delete a receipt, its items, and all its page images."""
    receipt = _get_or_404(db, receipt_id)

    names = {receipt.image_path, receipt.thumbnail_path}
    for page in receipt.pages:
        names.update((page.image_path, page.thumbnail_path))
    for name in names:
        if name:
            _stored_file(name).unlink(missing_ok=True)

    db.delete(receipt)
    db.commit()


# ═════════════════════════════════════════════════════════════════════════
#  Image serving
# ═════════════════════════════════════════════════════════════════════════

@router.get("/{receipt_id}/image")
def get_receipt_image(receipt_id: UUID, db: Session = Depends(get_db)):
    """Serve the receipt image (JPEG, max 1600 px)."""
    receipt = _get_or_404(db, receipt_id)
    if not receipt.image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    path = _stored_file(receipt.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from disk")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{receipt_id}/thumbnail")
def get_receipt_thumbnail(receipt_id: UUID, db: Session = Depends(get_db)):
    """Serve the receipt thumbnail."""
    receipt = _get_or_404(db, receipt_id)
    if not receipt.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = _stored_file(receipt.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file missing from disk")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{receipt_id}/pages/{page_number}/image")
def get_page_image(receipt_id: UUID, page_number: int, db: Session = Depends(get_db)):
    """Serve one page's image (1-based page_number)."""
    page = _get_page_or_404(db, receipt_id, page_number)
    path = _stored_file(page.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from disk")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{receipt_id}/pages/{page_number}/thumbnail")
def get_page_thumbnail(receipt_id: UUID, page_number: int, db: Session = Depends(get_db)):
    """Serve one page's thumbnail (1-based page_number)."""
    page = _get_page_or_404(db, receipt_id, page_number)
    if not page.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = _stored_file(page.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file missing from disk")
    return FileResponse(path, media_type="image/jpeg")


# ═════════════════════════════════════════════════════════════════════════
#  Helpers
# ═════════════════════════════════════════════════════════════════════════

async def _extract_page(upload_id: UUID, page_label: str = "") -> dict:
    """Load one uploaded image and run OCR on it. Raises 404 / 502 with a useful message."""
    image_path = _stored_file(f"{upload_id}.jpg")
    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Upload{page_label} not found. It may have been cleaned up, please re-upload.",
        )
    image_bytes = await run_in_threadpool(image_path.read_bytes)
    try:
        return await run_in_threadpool(get_ocr_engine().extract_receipt, image_bytes)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OCR failed{page_label}: {e}")


def _to_process_response(upload_ids: list, extracted: dict, verdict) -> schemas.ProcessResponse:
    ids = [str(u) for u in upload_ids]
    if verdict.status == REJECTED:
        return schemas.ProcessResponse(
            upload_id=ids[0],
            upload_ids=ids,
            status=verdict.status,
            is_receipt=False,
            rejection_reason=verdict.reason,
            document_type=extracted["document_type"],
            engine=extracted.get("engine"),
        )

    return schemas.ProcessResponse(
        upload_id=ids[0],
        upload_ids=ids,
        status=verdict.status,
        is_receipt=True,
        review_reason=verdict.reason,
        needs_review=verdict.status != "accepted",
        engine=extracted.get("engine"),
        document_type=extracted["document_type"],
        vendor_name=extracted["vendor_name"],
        vendor_gstin=extracted["vendor_gstin"],
        invoice_number=extracted["invoice_number"],
        date=extracted["date"],
        receipt_date=extracted["receipt_date"],
        total=extracted["total"],
        tax_total=extracted["tax_total"],
        discount_total=extracted["discount_total"],
        currency=extracted["currency"],
        category=extracted["category"],
        confidence=extracted["confidence"],
        total_auto_corrected=extracted["total_auto_corrected"],
        is_partial_page=extracted["is_partial_page"],
        page_number=extracted["page_number"],
        page_count=extracted["page_count"],
        items=[schemas.LineItemBase(**i) for i in extracted["items"]],
        raw_ocr_text=extracted["raw_text"],
    )


def _get_page_or_404(db: Session, receipt_id: UUID, page_number: int) -> ReceiptPage:
    page = (
        db.query(ReceiptPage)
        .filter(ReceiptPage.receipt_id == receipt_id, ReceiptPage.page_number == page_number)
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


def _stored_file(name: str) -> Path:
    """Resolve a file inside upload_dir; refuse anything that escapes it."""
    base = Path(settings.upload_dir).resolve()
    path = (base / name).resolve()
    if base not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return path


def _get_or_404(db: Session, receipt_id: UUID) -> Receipt:
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def _receipt_to_out(receipt: Receipt) -> schemas.ReceiptOut:
    """Convert a Receipt ORM model to ReceiptOut, adding image URLs."""
    return schemas.ReceiptOut(
        id=receipt.id,
        vendor_name=receipt.vendor_name,
        vendor_gstin=receipt.vendor_gstin,
        invoice_number=receipt.invoice_number,
        document_type=receipt.document_type,
        date=receipt.date,
        receipt_date=receipt.receipt_date,
        total=receipt.total,
        tax_total=receipt.tax_total,
        discount_total=receipt.discount_total,
        currency=receipt.currency,
        category=receipt.category,
        confidence=receipt.confidence,
        needs_review=receipt.needs_review,
        review_reason=receipt.review_reason,
        total_auto_corrected=receipt.total_auto_corrected,
        items=[schemas.LineItemOut.model_validate(i) for i in receipt.items],
        pages=[
            schemas.PageOut(
                page_number=p.page_number,
                image_url=f"/receipts/{receipt.id}/pages/{p.page_number}/image",
                thumbnail_url=(
                    f"/receipts/{receipt.id}/pages/{p.page_number}/thumbnail" if p.thumbnail_path else None
                ),
            )
            for p in receipt.pages
        ],
        raw_ocr_text=receipt.raw_ocr_text or "",
        image_url=f"/receipts/{receipt.id}/image" if receipt.image_path else None,
        thumbnail_url=f"/receipts/{receipt.id}/thumbnail" if receipt.thumbnail_path else None,
        created_at=receipt.created_at,
    )

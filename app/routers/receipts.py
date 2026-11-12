"""Receipt endpoints: upload, process (OCR), save, list, detail, update, delete."""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app import schemas
from app.authmanager import create_image_token
from app.config import settings
from app.decision import REJECTED, decide
from app.dependencies import get_current_user, get_db, get_image_user
from app.duplicates import file_sha256, find_possible_duplicate, find_receipt_by_hash
from app.merge import MergeError, merge_pages
from app.models import Receipt, ReceiptItem, ReceiptPage, Upload, User
from app.normalize import parse_date
from app.ocr import OcrEngine, save_upload
from app.ratelimit import limiter

router = APIRouter(prefix="/receipts", tags=["receipts"])
log = logging.getLogger("receipts.api")

# Per-user limits (numbers live in settings; each OCR page is one paid Gemini call).
UPLOAD_RULES = [("upload_hour", "upload_files_per_hour", 3600)]
OCR_RULES = [("ocr_hour", "ocr_pages_per_hour", 3600), ("ocr_day", "ocr_pages_per_day", 86400)]

# ── Singleton OCR engine ─────────────────────────────────────────────────
_ocr_engine = None


def get_ocr_engine() -> OcrEngine:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OcrEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            fallback_models=settings.gemini_fallbacks,
            max_attempts=settings.ocr_max_attempts,
        )
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

async def _ingest(file: UploadFile) -> tuple[str, float]:
    """Validate and store one uploaded image. Returns (upload_id, size_kb)."""
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
    return upload_id, round(len(image_bytes) / 1024, 1)


async def _already_saved(db: Session, upload_id: str, user_id: UUID) -> Optional[str]:
    """Id of a saved receipt that already holds an identical image, if any."""
    stored = Path(settings.upload_dir) / f"{upload_id}.jpg"
    found = await run_in_threadpool(lambda: find_receipt_by_hash(db, file_sha256(stored), user_id))
    return str(found) if found else None


@router.post("/upload-many", response_model=schemas.UploadManyResponse)
async def upload_many(files: List[UploadFile] = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Upload one or several images in one request (up to MAX_PAGES_PER_INVOICE, default 10).
    Returns an upload_id per file, in the order sent: pass them to POST /receipts/process-pages
    (it also works for a single image). All-or-nothing: if any file is rejected, none are kept
    and the error names the bad file.
    """
    limit = settings.max_pages_per_invoice
    if not files:
        raise HTTPException(status_code=422, detail="No files sent.")
    if len(files) > limit:
        raise HTTPException(status_code=422, detail=f"Too many files: the limit is {limit} per invoice.")

    limiter.hit(str(user.id), UPLOAD_RULES, cost=len(files))

    stored: list[schemas.UploadResponse] = []
    try:
        for f in files:
            name = f.filename or "receipt.jpg"
            try:
                upload_id, size_kb = await _ingest(f)
            except HTTPException as e:
                raise HTTPException(status_code=e.status_code, detail=f"{name}: {e.detail}")
            stored.append(schemas.UploadResponse(
                upload_id=upload_id,
                filename=name,
                size_kb=size_kb,
                already_saved_receipt_id=await _already_saved(db, upload_id, user.id),
            ))
        # Remember who owns each upload: only they can process or save it.
        await run_in_threadpool(_record_uploads, db, user.id, [u.upload_id for u in stored])
    except SQLAlchemyError:
        log.exception("Could not record uploads")
        _discard_uploads(stored)
        raise HTTPException(status_code=500, detail="Could not store the upload. Please try again.")
    except Exception:
        _discard_uploads(stored)           # leave nothing behind from a failed batch
        raise
    return schemas.UploadManyResponse(uploads=stored)


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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Run OCR on one uploaded image, then apply the accept / needs_review / rejected
    policy (app/decision.py). Nothing is saved here.
    HTTP 200 is returned for all three statuses; check `status` in the body.
    For an invoice that spans several images use POST /receipts/process-pages.
    """
    await run_in_threadpool(_require_owned_uploads, db, [upload_id], user)
    limiter.hit(str(user.id), OCR_RULES)
    extracted = await _extract_page(upload_id)
    verdict = decide(extracted, force=force)
    return await _flag_duplicate(db, _to_process_response([upload_id], extracted, verdict), extracted, user.id)


@router.post("/process-pages", response_model=schemas.ProcessResponse)
async def process_pages(
    body: schemas.ProcessPagesRequest,
    force: bool = Query(False, description="Same override as the single-page endpoint."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Run OCR on every page of one invoice and merge them into a single result:
    items are concatenated in page order, header fields come from the first page,
    and the grand total from the last. Missing or repeated pages are reported.

    The response's `upload_ids` are in document order. Pass them, in that order,
    to POST /receipts. Pages of different invoices, or a page uploaded twice, give 422.
    """
    await run_in_threadpool(_require_owned_uploads, db, body.upload_ids, user)
    limiter.hit(str(user.id), OCR_RULES, cost=len(body.upload_ids))

    # OCR pages concurrently (max 4 at a time): a 6-page invoice shouldn't take 6x as long.
    gate = asyncio.Semaphore(4)

    async def _one(n: int, upload_id: UUID) -> dict:
        async with gate:
            return await _extract_page(upload_id, f" for page {n}")

    pages = list(await asyncio.gather(*(_one(n, u) for n, u in enumerate(body.upload_ids, start=1))))

    try:
        merged = merge_pages(pages)
    except MergeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    ordered_ids = [body.upload_ids[i] for i in merged["page_order"]]
    verdict = decide(merged, force=force)
    return await _flag_duplicate(db, _to_process_response(ordered_ids, merged, verdict), merged, user.id)


# ═════════════════════════════════════════════════════════════════════════
#  Step 3: Save confirmed receipt to database
# ═════════════════════════════════════════════════════════════════════════

@router.post("", response_model=schemas.ReceiptOut, status_code=201)
def save_receipt(body: schemas.ReceiptCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Save a user-confirmed receipt. `upload_ids` are its pages, in order.
    Called after the user reviews/edits the OCR result.
    Returns 409 if any upload was already saved or the same invoice
    (seller GSTIN + invoice number) already exists.
    """
    image_names = [f"{u}.jpg" for u in body.upload_ids]
    thumb_names = [f"{u}_thumb.jpg" for u in body.upload_ids]

    # Saved already (e.g. a double tap on "Save")? Say so before anything else.
    if (
        db.query(ReceiptPage.id)
        .join(Receipt, Receipt.id == ReceiptPage.receipt_id)
        .filter(ReceiptPage.image_path.in_(image_names), Receipt.user_id == user.id)
        .first()
    ):
        raise HTTPException(status_code=409, detail="One of these uploads was already saved as a receipt.")

    _require_owned_uploads(db, body.upload_ids, user)

    for n, name in enumerate(image_names, start=1):
        if not _stored_file(name).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Upload image for page {n} not found. Please re-upload it.",
            )

    page_hashes = [file_sha256(_stored_file(n)) for n in image_names]

    if body.vendor_gstin and body.invoice_number:
        dup = (
            db.query(Receipt.id)
            .filter(
                Receipt.user_id == user.id,
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
        user_id=user.id,
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
            ReceiptPage(page_number=n, image_path=img, thumbnail_path=thumb, content_hash=digest)
            for n, (img, thumb, digest) in enumerate(zip(image_names, thumb_names, page_hashes), start=1)
        ],
    )
    db.add(receipt)
    # The uploads are now owned by the receipt: drop the pending rows in the same transaction.
    db.query(Upload).filter(Upload.id.in_(body.upload_ids)).delete(synchronize_session=False)
    try:
        db.commit()   # receipt + items + pages + upload rows in one transaction: all or nothing
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This receipt was already saved.")
    except DataError:
        db.rollback()
        raise HTTPException(status_code=422, detail="A field value is too long or out of range.")
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
    user: User = Depends(get_current_user),
):
    """List receipts with pagination, filters, search and whitelisted sorting."""
    key = sort.lstrip("-")
    if key not in _SORTABLE:
        raise HTTPException(status_code=422, detail=f"Cannot sort by '{key}'. Allowed: {', '.join(_SORTABLE)}")

    query = db.query(Receipt).filter(Receipt.user_id == user.id)
    if category:
        query = query.filter(Receipt.category == category)
    if document_type:
        query = query.filter(Receipt.document_type == document_type)
    if needs_review is not None:
        query = query.filter(Receipt.needs_review == needs_review)
    if q:
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{term}%"
        query = query.filter(
            Receipt.vendor_name.ilike(like, escape="\\") | Receipt.invoice_number.ilike(like, escape="\\")
        )

    col = _SORTABLE[key]
    ordering = col.desc() if sort.startswith("-") else col.asc()
    query = query.order_by(ordering.nulls_last(), Receipt.id)   # undated receipts always at the end

    total = query.count()
    pages = max(1, -(-total // per_page))  # ceiling division
    receipts = (
        query.options(selectinload(Receipt.items), selectinload(Receipt.pages))   # no per-receipt queries
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
def get_receipt(receipt_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get a single receipt by ID."""
    return _receipt_to_out(_get_or_404(db, receipt_id, user))


@router.patch("/{receipt_id}", response_model=schemas.ReceiptOut)
def update_receipt(receipt_id: UUID, body: schemas.ReceiptUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Partial update. If `items` is sent, it replaces all existing items."""
    receipt = _get_or_404(db, receipt_id, user)

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
    if update_data.get("needs_review") is False:
        receipt.review_reason = None   # user confirmed it, so the old warning is stale

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
    except DataError:
        db.rollback()
        raise HTTPException(status_code=422, detail="A field value is too long or out of range.")
    db.refresh(receipt)
    return _receipt_to_out(receipt)


@router.delete("/{receipt_id}", status_code=204)
def delete_receipt(receipt_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete a receipt, its items, and all its page images."""
    receipt = _get_or_404(db, receipt_id, user)

    names = {receipt.image_path, receipt.thumbnail_path}
    for page in receipt.pages:
        names.update((page.image_path, page.thumbnail_path))
    db.delete(receipt)
    db.commit()   # row first: if this fails, the images are still there
    for name in names:
        if name:
            _stored_file(name).unlink(missing_ok=True)


# ═════════════════════════════════════════════════════════════════════════
#  Image serving
# ═════════════════════════════════════════════════════════════════════════

@router.get("/{receipt_id}/image")
def get_receipt_image(receipt_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_image_user)):
    """Serve the receipt image (JPEG, max 1600 px)."""
    receipt = _get_or_404(db, receipt_id, user)
    if not receipt.image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    path = _stored_file(receipt.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from disk")
    return _image_response(path)


@router.get("/{receipt_id}/thumbnail")
def get_receipt_thumbnail(receipt_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_image_user)):
    """Serve the receipt thumbnail."""
    receipt = _get_or_404(db, receipt_id, user)
    if not receipt.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = _stored_file(receipt.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file missing from disk")
    return _image_response(path)


@router.get("/{receipt_id}/pages/{page_number}/image")
def get_page_image(receipt_id: UUID, page_number: int, db: Session = Depends(get_db), user: User = Depends(get_image_user)):
    """Serve one page's image (1-based page_number)."""
    page = _get_page_or_404(db, receipt_id, page_number, user)
    path = _stored_file(page.image_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from disk")
    return _image_response(path)


@router.get("/{receipt_id}/pages/{page_number}/thumbnail")
def get_page_thumbnail(receipt_id: UUID, page_number: int, db: Session = Depends(get_db), user: User = Depends(get_image_user)):
    """Serve one page's thumbnail (1-based page_number)."""
    page = _get_page_or_404(db, receipt_id, page_number, user)
    if not page.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = _stored_file(page.thumbnail_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file missing from disk")
    return _image_response(path)


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
    except Exception:
        # Details go to the log only: provider errors can contain URLs or keys.
        log.exception("OCR failed%s for upload %s", page_label, upload_id)
        raise HTTPException(status_code=502, detail=f"OCR failed{page_label}. Please try again in a moment.")


async def _flag_duplicate(db: Session, resp: schemas.ProcessResponse, extracted: dict, user_id: UUID) -> schemas.ProcessResponse:
    """Attach a possible-duplicate warning. Never changes the status: the user decides."""
    if resp.status == REJECTED:
        return resp
    hit = await run_in_threadpool(find_possible_duplicate, db, extracted, user_id)
    if hit:
        resp.possible_duplicate_of, resp.duplicate_warning = str(hit[0]), hit[1]
    return resp


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


def _get_page_or_404(db: Session, receipt_id: UUID, page_number: int, user: User) -> ReceiptPage:
    page = (
        db.query(ReceiptPage)
        .join(Receipt, Receipt.id == ReceiptPage.receipt_id)
        .filter(
            ReceiptPage.receipt_id == receipt_id,
            ReceiptPage.page_number == page_number,
            Receipt.user_id == user.id,
        )
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


def _get_or_404(db: Session, receipt_id: UUID, user: User) -> Receipt:
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id, Receipt.user_id == user.id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


def _receipt_to_out(receipt: Receipt) -> schemas.ReceiptOut:
    """Convert a Receipt ORM model to ReceiptOut, adding signed image URLs.

    Every image URL carries `?sig=...`, a short-lived token that opens only this receipt's
    images, so the app can use plain <img src> without exposing the login token."""
    sig = create_image_token(receipt.user_id, receipt.id) if receipt.user_id else None

    def url(path: str) -> str:
        return f"{path}?sig={sig}" if sig else path

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
                image_url=url(f"/receipts/{receipt.id}/pages/{p.page_number}/image"),
                thumbnail_url=(
                    url(f"/receipts/{receipt.id}/pages/{p.page_number}/thumbnail") if p.thumbnail_path else None
                ),
            )
            for p in receipt.pages
        ],
        raw_ocr_text=receipt.raw_ocr_text or "",
        image_url=url(f"/receipts/{receipt.id}/image") if receipt.image_path else None,
        thumbnail_url=url(f"/receipts/{receipt.id}/thumbnail") if receipt.thumbnail_path else None,
        created_at=receipt.created_at,
    )


def _image_response(path: Path) -> FileResponse:
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


def _record_uploads(db: Session, user_id: UUID, upload_ids: List[str]) -> None:
    db.add_all([Upload(id=UUID(u), user_id=user_id) for u in upload_ids])
    db.commit()


def _discard_uploads(stored: list) -> None:
    """Delete the files of uploads from a failed batch (their rows were never committed)."""
    for u in stored:
        _stored_file(f"{u.upload_id}.jpg").unlink(missing_ok=True)
        _stored_file(f"{u.upload_id}_thumb.jpg").unlink(missing_ok=True)


def _require_owned_uploads(db: Session, upload_ids: List[UUID], user: User) -> None:
    """404 unless every upload id is a pending upload of this user."""
    found = {
        r.id for r in db.query(Upload.id).filter(Upload.id.in_(list(upload_ids)), Upload.user_id == user.id)
    }
    for n, upload_id in enumerate(upload_ids, start=1):
        if upload_id not in found:
            label = f" for page {n}" if len(upload_ids) > 1 else ""
            raise HTTPException(
                status_code=404,
                detail=f"Upload{label} not found. It may have been cleaned up, please re-upload.",
            )


"""Pydantic schemas for request validation and response serialization."""

import datetime as dt   # `import datetime as dt` because a field below is literally named `date`
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.normalize import (
    normalize_category,
    normalize_doc_type,
    normalize_gstin,
)


# ═════════════════════════════════════════════════════════════════════════
#  Line items
# ═════════════════════════════════════════════════════════════════════════

class LineItemBase(BaseModel):
    name: str = Field(max_length=255)
    quantity: float = Field(1.0, gt=0)
    unit: Optional[str] = Field(None, max_length=20)
    hsn_code: Optional[str] = Field(None, max_length=20)
    unit_price: float = Field(0.0, ge=0)        # rate, before discount & tax
    discount: float = Field(0.0, ge=0)          # amount, not percent
    taxable_value: float = Field(0.0, ge=0)     # after discount, before tax
    tax_rate: float = Field(0.0, ge=0, le=100)  # combined GST %
    tax_amount: float = Field(0.0, ge=0)
    total_price: float = Field(0.0, ge=0)       # final line amount incl. tax

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("item name cannot be blank")
        return v


class LineItemOut(LineItemBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════
#  Receipts
# ═════════════════════════════════════════════════════════════════════════

class _ReceiptFieldCleaning(BaseModel):
    """Shared validators. None passes through so PATCH can leave a field untouched."""

    @field_validator("category", check_fields=False)
    @classmethod
    def _category(cls, v):
        return None if v is None else normalize_category(v)

    @field_validator("document_type", check_fields=False)
    @classmethod
    def _doc_type(cls, v):
        return None if v is None else normalize_doc_type(v)

    @field_validator("vendor_gstin", check_fields=False)
    @classmethod
    def _gstin(cls, v):
        return normalize_gstin(v)

    @field_validator("invoice_number", check_fields=False)
    @classmethod
    def _invoice_number(cls, v):
        v = (v or "").strip().upper()
        return v or None

    @field_validator("currency", check_fields=False)
    @classmethod
    def _currency(cls, v):
        if v is None:
            return None
        v = v.strip().upper()
        return v if len(v) == 3 else "INR"


MAX_PAGES = 20


def _unique_ids(v: List[UUID]) -> List[UUID]:
    if len(set(v)) != len(v):
        raise ValueError("the same upload appears more than once")
    return v


class ProcessPagesRequest(BaseModel):
    """Body of POST /receipts/process-pages: the uploads that make up one invoice."""
    upload_ids: List[UUID] = Field(min_length=1, max_length=MAX_PAGES)

    _check_unique = field_validator("upload_ids")(_unique_ids)


class UploadResponse(BaseModel):
    """Returned by POST /receipts/upload (step 1, no OCR yet)."""
    upload_id: str
    filename: str
    size_kb: float


class ProcessResponse(BaseModel):
    """Returned by POST /receipts/{upload_id}/process (step 2, OCR result)."""
    upload_id: str                    # first page
    upload_ids: List[str] = []        # all pages, in document order: pass these to POST /receipts
    status: str                       # accepted | needs_review | rejected
    is_receipt: bool                  # False only when status == rejected
    rejection_reason: Optional[str] = None
    review_reason: Optional[str] = None
    needs_review: bool = False
    engine: Optional[str] = None

    document_type: str = "other"
    vendor_name: str = "Unknown Vendor"
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    receipt_date: Optional[dt.date] = None
    total: float = 0.0
    tax_total: float = 0.0
    discount_total: float = 0.0
    currency: str = "INR"
    category: str = "Other"
    confidence: str = "medium"
    total_auto_corrected: bool = False

    is_partial_page: bool = False
    page_number: Optional[int] = None
    page_count: Optional[int] = None

    items: List[LineItemBase] = []
    raw_ocr_text: str = ""


class ReceiptCreate(_ReceiptFieldCleaning):
    """Sent by the frontend to save a confirmed receipt (step 3)."""
    # UUID types are what block path tricks like "../../x". Order = page order.
    upload_ids: List[UUID] = Field(min_length=1, max_length=MAX_PAGES)
    vendor_name: str = Field("Unknown Vendor", max_length=255)
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = Field(None, max_length=100)
    document_type: str = "printed_receipt"
    date: Optional[str] = Field(None, max_length=50)
    receipt_date: Optional[dt.date] = None   # if omitted, parsed from `date`
    total: float = Field(0.0, ge=0)
    tax_total: float = Field(0.0, ge=0)
    discount_total: float = Field(0.0, ge=0)
    currency: str = "INR"
    category: str = "Other"
    confidence: str = "medium"
    needs_review: bool = False
    review_reason: Optional[str] = None
    total_auto_corrected: bool = False
    items: List[LineItemBase] = []
    raw_ocr_text: str = ""

    _check_unique = field_validator("upload_ids")(_unique_ids)


class ReceiptUpdate(_ReceiptFieldCleaning):
    """Partial update for an existing receipt. Omitted fields are left alone."""
    vendor_name: Optional[str] = Field(None, max_length=255)
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = Field(None, max_length=100)
    document_type: Optional[str] = None
    date: Optional[str] = Field(None, max_length=50)
    receipt_date: Optional[dt.date] = None
    total: Optional[float] = Field(None, ge=0)
    tax_total: Optional[float] = Field(None, ge=0)
    discount_total: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    category: Optional[str] = None
    needs_review: Optional[bool] = None
    items: Optional[List[LineItemBase]] = None


class PageOut(BaseModel):
    page_number: int
    image_url: str
    thumbnail_url: Optional[str] = None


class ReceiptOut(BaseModel):
    """Full receipt returned by GET / list endpoints."""
    id: UUID
    vendor_name: str
    vendor_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    document_type: str
    date: Optional[str] = None
    receipt_date: Optional[dt.date] = None
    total: float
    tax_total: float
    discount_total: float
    currency: str
    category: str
    confidence: str
    needs_review: bool
    review_reason: Optional[str] = None
    total_auto_corrected: bool
    items: List[LineItemOut] = []
    pages: List[PageOut] = []
    raw_ocr_text: str
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedReceipts(BaseModel):
    items: List[ReceiptOut]
    total: int
    page: int
    per_page: int
    pages: int


# ═════════════════════════════════════════════════════════════════════════
#  Analytics
# ═════════════════════════════════════════════════════════════════════════

class DailySpend(BaseModel):
    date: str
    total: float


class MonthlySummary(BaseModel):
    month: int
    year: int
    total_spent: float
    receipt_count: int
    avg_per_receipt: float
    previous_month_total: float
    daily_breakdown: List[DailySpend]


class CategoryBreakdownItem(BaseModel):
    category: str
    total: float
    percentage: float
    count: int

"""SQLAlchemy ORM models for receipts and receipt line items."""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """An account. Only the bcrypt hash of the password is stored."""

    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, unique=True, index=True)  # stored lowercase
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Upload(Base):
    """An image that was uploaded but not saved as a receipt yet.

    `id` is the upload_id the client holds (it is also the file name stem on disk).
    The row is deleted in the same transaction that saves the receipt; the cleanup job
    removes rows (and files) that never got saved."""

    __tablename__ = "uploads"

    id = Column(Uuid(as_uuid=True), primary_key=True)
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class Receipt(Base):
    """One receipt / bill / invoice. Only fields we query or sum are columns;
    everything else printed on the document stays in raw_ocr_text."""

    __tablename__ = "receipts"
    __table_args__ = (
        # Same seller + same invoice number = same invoice. (NULLs never collide,
        # so receipts without a GSTIN / invoice number are unaffected.)
        UniqueConstraint("user_id", "vendor_gstin", "invoice_number", name="uq_receipt_vendor_invoice"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Owner. Nullable only so rows from before accounts existed survive the migration.
    user_id = Column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # ── Who / what ───────────────────────────────────────────────────
    vendor_name = Column(String(255), nullable=False, default="Unknown Vendor")
    vendor_gstin = Column(String(15), nullable=True, index=True)
    invoice_number = Column(String(100), nullable=True)
    document_type = Column(String(30), nullable=False, default="printed_receipt")

    # ── When ─────────────────────────────────────────────────────────
    date = Column(String(50), nullable=True)               # exactly as printed
    receipt_date = Column(Date, nullable=True, index=True)  # parsed; used by analytics

    # ── Money ────────────────────────────────────────────────────────
    total = Column(Float, nullable=False, default=0.0)
    tax_total = Column(Float, nullable=False, default=0.0)
    discount_total = Column(Float, nullable=False, default=0.0)
    currency = Column(String(3), nullable=False, default="INR")

    # ── Classification / review state ────────────────────────────────
    category = Column(String(100), nullable=False, default="Other")
    confidence = Column(String(20), nullable=False, default="medium")  # high / medium / low
    needs_review = Column(Boolean, nullable=False, default=False)
    review_reason = Column(Text, nullable=True)
    total_auto_corrected = Column(Boolean, nullable=False, default=False)

    # ── Raw data + files ─────────────────────────────────────────────
    raw_ocr_text = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True, unique=True)  # relative to upload_dir
    thumbnail_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items = relationship(
        "ReceiptItem",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptItem.position",
    )
    pages = relationship(
        "ReceiptPage",
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="ReceiptPage.page_number",
    )

    def __repr__(self) -> str:
        return f"<Receipt {self.vendor_name} {self.total}>"


class ReceiptPage(Base):
    """One uploaded image of a receipt. Multi-page invoices have several."""

    __tablename__ = "receipt_pages"
    __table_args__ = (
        UniqueConstraint("receipt_id", "page_number", name="uq_receipt_page_number"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number = Column(Integer, nullable=False)  # 1-based, in document order
    image_path = Column(String(500), nullable=False, unique=True)
    thumbnail_path = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 of the stored JPEG

    receipt = relationship("Receipt", back_populates="pages")


class ReceiptItem(Base):
    __tablename__ = "receipt_items"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False, default=0)  # row order on the document
    name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String(20), nullable=True)               # Pac / Pcs / Kg ...
    hsn_code = Column(String(20), nullable=True)
    unit_price = Column(Float, nullable=False, default=0.0)     # rate, before discount & tax
    discount = Column(Float, nullable=False, default=0.0)       # amount, not percent
    taxable_value = Column(Float, nullable=False, default=0.0)  # after discount, before tax
    tax_rate = Column(Float, nullable=False, default=0.0)       # combined GST %, e.g. 5
    tax_amount = Column(Float, nullable=False, default=0.0)
    total_price = Column(Float, nullable=False, default=0.0)    # final line amount incl. tax

    receipt = relationship("Receipt", back_populates="items")

    def __repr__(self) -> str:
        return f"<ReceiptItem {self.name} {self.total_price}>"
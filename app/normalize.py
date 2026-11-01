"""Pure helpers that clean up whatever the OCR engines return.

No I/O and no framework imports, so everything here is easy to unit test.
The OCR engine feeds its raw output through `normalize_extraction`,
so the rest of the app sees one consistent shape.
"""

import math
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional

CATEGORIES = [
    "Groceries",
    "Food & Dining",
    "Transport",
    "Shopping",
    "Bills & Utilities",
    "Health",
    "Entertainment",
    "Education",
    "Other",
]

DOCUMENT_TYPES = [
    "printed_receipt",
    "handwritten_bill",
    "gst_invoice",
    "invoice",
    "utility_bill",
    "payment_screenshot",
    "menu",
    "id_card",
    "other",
]

_CATEGORY_ALIASES = {
    "grocery": "Groceries",
    "food": "Food & Dining",
    "dining": "Food & Dining",
    "restaurant": "Food & Dining",
    "food and dining": "Food & Dining",
    "travel": "Transport",
    "fuel": "Transport",
    "bills": "Bills & Utilities",
    "utilities": "Bills & Utilities",
    "bills and utilities": "Bills & Utilities",
    "medical": "Health",
    "pharmacy": "Health",
    "healthcare": "Health",
    "clothing": "Shopping",
    "electronics": "Shopping",
}

_DOC_TYPE_ALIASES = {
    "receipt": "printed_receipt",
    "printed": "printed_receipt",
    "handwritten": "handwritten_bill",
    "handwritten_receipt": "handwritten_bill",
    "tax_invoice": "gst_invoice",
    "gst_bill": "gst_invoice",
    "bill": "invoice",
    "electricity_bill": "utility_bill",
    "upi": "payment_screenshot",
    "payment_confirmation": "payment_screenshot",
}

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


# ── Numbers ──────────────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(r"[₹$€£¥]|rs\.?|inr|usd|eur", re.IGNORECASE)


def safe_float(value: Any) -> float:
    """
    Convert OCR output to float. Handles currency symbols (₹1,250.00, Rs. 340),
    thousands commas, None / empty / garbage (→ 0.0).
    """
    if value is None or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else 0.0
    s = _CURRENCY_RE.sub("", str(value)).replace(",", "").replace(" ", "").strip()
    try:
        f = float(s)
    except ValueError:
        return 0.0
    return f if math.isfinite(f) else 0.0


# ── Dates ────────────────────────────────────────────────────────────────

_ISO_FORMATS = ["%Y-%m-%d", "%Y/%m/%d"]
_DAY_FIRST_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
]
_NAMED_FORMATS = [
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%b-%y", "%d %b, %Y", "%d %B, %Y",
    "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y",
]
_MONTH_FIRST_FORMATS = ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"]


def parse_date(text: Optional[str], today: Optional[date] = None) -> Optional[date]:
    """
    Parse a date as printed on a receipt into a real date.

    Numeric dates are read day-first (Indian convention): 03/04/2026 → 3 April.
    Month-first is only tried if day-first is impossible (e.g. 04/13/2026).
    Returns None for unparseable, pre-2000, or future (> tomorrow) dates, since
    those are almost always OCR misreads.
    """
    if not text:
        return None
    s = str(text).strip()
    s = re.split(r"\s+\d{1,2}:\d{2}", s)[0]                    # drop any time part
    s = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", s, flags=re.I)   # 1st, 2nd, 16th
    s = re.sub(r"\bSept\b", "Sep", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" ,")

    for fmt in _ISO_FORMATS + _DAY_FIRST_FORMATS + _NAMED_FORMATS + _MONTH_FIRST_FORMATS:
        try:
            d = datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        limit = (today or date.today()) + timedelta(days=1)
        if d.year < 2000 or d > limit:
            return None
        return d
    return None


# ── Small normalisers ────────────────────────────────────────────────────

def normalize_category(value: Optional[str]) -> str:
    if not value:
        return "Other"
    key = str(value).strip().lower()
    for cat in CATEGORIES:
        if key == cat.lower():
            return cat
    return _CATEGORY_ALIASES.get(key, "Other")


def normalize_doc_type(value: Optional[str]) -> str:
    key = re.sub(r"[\s\-]+", "_", str(value or "").strip().lower())
    if key in DOCUMENT_TYPES:
        return key
    return _DOC_TYPE_ALIASES.get(key, "other")


def normalize_gstin(value: Optional[str]) -> Optional[str]:
    """Return a valid 15-char GSTIN (uppercase) or None."""
    if not value:
        return None
    g = re.sub(r"\s+", "", str(value)).upper()
    return g if GSTIN_RE.match(g) else None


def normalize_level(value: Optional[str], default: str = "medium") -> str:
    v = str(value or "").strip().lower()
    return v if v in ("high", "medium", "low") else default


def _clean_str(value: Any, max_len: int) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s[:max_len] if s else None


def _to_int(value: Any) -> Optional[int]:
    f = safe_float(value)
    return int(f) if f > 0 else None


# ── The main entry point ─────────────────────────────────────────────────

def normalize_extraction(raw: dict, today: Optional[date] = None) -> dict:
    """
    Turn a raw extraction dict (from Gemini) into the clean
    shape used everywhere else. Never raises on messy input.

    Money rules:
      * Line items keep rate / discount / taxable / tax / line total separately.
        A missing line total is derived (taxable + tax, or qty × rate − discount + tax).
      * The stated grand total is NEVER overwritten. If it is missing it is
        computed from the items and `total_auto_corrected` is set.
      * `totals_match` says whether the items add up to the total (either
        items == total, as on GST invoices, or items + tax == total, as on
        receipts with a separate tax line). None = can't tell.
    """
    items = []
    for it in raw.get("items") or []:
        if not isinstance(it, dict):
            continue
        name = _clean_str(it.get("name"), 255)
        if not name:
            continue
        qty = safe_float(it.get("quantity"))
        qty = qty if qty > 0 else 1.0
        rate = max(safe_float(it.get("unit_price")), 0.0)
        discount = max(safe_float(it.get("discount")), 0.0)
        taxable = max(safe_float(it.get("taxable_value")), 0.0)
        tax_amount = max(safe_float(it.get("tax_amount")), 0.0)
        tax_rate = min(max(safe_float(it.get("tax_rate")), 0.0), 100.0)
        line_total = max(safe_float(it.get("total_price")), 0.0)

        if line_total == 0:
            if taxable > 0:
                line_total = taxable + tax_amount
            elif rate > 0:
                line_total = max(qty * rate - discount, 0.0) + tax_amount

        items.append({
            "name": name,
            "quantity": qty,
            "unit": _clean_str(it.get("unit"), 20),
            "hsn_code": _clean_str(it.get("hsn_code"), 20),
            "unit_price": round(rate, 2),
            "discount": round(discount, 2),
            "taxable_value": round(taxable, 2),
            "tax_rate": round(tax_rate, 2),
            "tax_amount": round(tax_amount, 2),
            "total_price": round(line_total, 2),
        })

    item_sum = round(sum(i["total_price"] for i in items), 2)

    stated_total = max(safe_float(raw.get("total")), 0.0)
    total = stated_total
    auto_corrected = False
    if total == 0 and item_sum > 0:
        total = item_sum
        auto_corrected = True

    tax_total = max(safe_float(raw.get("tax_total")), 0.0)
    if tax_total == 0:
        tax_total = round(sum(i["tax_amount"] for i in items), 2)
    discount_total = max(safe_float(raw.get("discount_total")), 0.0)
    if discount_total == 0:
        discount_total = round(sum(i["discount"] for i in items), 2)

    totals_match: Optional[bool] = None
    if items and stated_total > 0 and item_sum > 0:
        tol = max(1.0, 0.01 * stated_total)  # absorbs round-off lines
        totals_match = (
            abs(item_sum - stated_total) <= tol
            or abs(item_sum + tax_total - stated_total) <= tol
        )

    date_text = _clean_str(raw.get("date"), 50)
    receipt_date = parse_date(date_text, today=today)
    date_problem = None
    if date_text and receipt_date is None:
        date_problem = f"Couldn't read the date '{date_text}'. Please check it."

    level = normalize_level(raw.get("legibility") or raw.get("confidence"))
    currency = (_clean_str(raw.get("currency"), 3) or "INR").upper()

    return {
        "document_type": normalize_doc_type(raw.get("document_type")),
        "engine": raw.get("engine"),
        "vendor_name": _clean_str(raw.get("vendor_name"), 255) or "Unknown Vendor",
        "vendor_gstin": normalize_gstin(raw.get("vendor_gstin")),
        "invoice_number": (_clean_str(raw.get("invoice_number"), 100) or "").upper() or None,
        "date": date_text,
        "receipt_date": receipt_date,
        "date_problem": date_problem,
        "total": round(total, 2),
        "tax_total": round(tax_total, 2),
        "discount_total": round(discount_total, 2),
        "currency": currency if len(currency) == 3 else "INR",
        "category": normalize_category(raw.get("category")),
        "legibility": level,
        "confidence": level,
        "has_total": stated_total > 0,
        "has_date": bool(date_text),
        "total_auto_corrected": auto_corrected,
        "totals_match": totals_match,
        "item_sum": item_sum,
        "is_partial_page": bool(raw.get("is_partial_page")),
        "page_number": _to_int(raw.get("page_number")),
        "page_count": _to_int(raw.get("page_count")),
        "items": items,
        "raw_text": str(raw.get("raw_text") or ""),
    }

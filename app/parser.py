"""Local regex-based receipt parser for 100% offline privacy mode.

Works on simple "name ... price" receipts. It is NOT layout-aware, so wide
multi-column GST invoices will mostly come back with few or no items; use the
Gemini engine for those.
"""

import re
from typing import List, Optional, Tuple

_AMOUNT = r"([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)"
_CUR = r"(?:rs\.?|₹|inr|\$)?"

TOTAL_PATTERN = re.compile(
    rf"(?i)(?<![a-z])(grand\s*total|net\s*amount|amount\s*payable|total\s*amt|total)"
    rf"\s*[:\-]?\s*{_CUR}\s*{_AMOUNT}"
)

# Lines that contain the word "total" but are not the payable amount.
_NOT_THE_TOTAL = re.compile(
    r"(?i)sub\s*-?\s*total|total\s*(items?|qty|quantity|savings?|discount)|\b[cs]gst\b|\bigst\b"
)

DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
    r"|\d{4}[/\-]\d{1,2}[/\-]\d{1,2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}"
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b"
)

LINE_ITEM_PATTERN = re.compile(
    rf"^(.{{2,40}}?)\s+(?:x\s*\d+\s+)?{_CUR}\s*{_AMOUNT}$",
    re.IGNORECASE,
)

GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")

INVOICE_NO_PATTERN = re.compile(
    r"(?i)(?:invoice|inv|bill|receipt|memo)\s*(?:no|number|num|#)\.?\s*[:\-#]?\s*"
    r"([A-Z0-9][A-Z0-9\-/]{2,30})"
)

_NOT_ITEM_WORDS = (
    "total", "tax", "cgst", "sgst", "igst", "subtotal", "discount", "cash",
    "change", "round", "gstin", "invoice", "phone", "mobile", "tel", "upi",
)

_CATEGORY_KEYWORDS = {
    "Health": ["pharmacy", "medical", "hospital", "clinic", "apollo", "medplus", "doctor", "diagnostic", "rx", "tablet", "chemist"],
    "Food & Dining": ["restaurant", "cafe", "coffee", "pizza", "burger", "swiggy", "zomato", "kitchen", "bistro", "dine", "hotel", "biryani"],
    "Groceries": ["supermarket", "mart", "fresh", "grocery", "kirana", "blinkit", "zepto", "instamart", "reliance smart", "dmart", "provision", "general store"],
    "Transport": ["uber", "ola", "rapido", "petrol", "fuel", "indian oil", "hpcl", "bpcl", "parking", "toll", "irctc", "metro"],
    "Bills & Utilities": ["electricity", "water", "broadband", "airtel", "jio", "recharge", "gas", "bill"],
    "Shopping": ["fashion", "trends", "zudio", "myntra", "amazon", "flipkart", "mall", "apparel", "store"],
}

_HEADER_LINES = {"tax invoice", "cash memo", "receipt", "bill of supply", "invoice", "cash bill"}


def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return 0.0


def _guess_vendor_name(lines: List[str]) -> str:
    for line in lines:
        low = line.lower()
        if low in _HEADER_LINES:
            continue
        if sum(c.isalpha() for c in line) < 3:   # phone numbers, dates, ids
            continue
        if GSTIN_PATTERN.search(line.upper()):
            continue
        if 3 <= len(line) <= 40:
            return line
    return "Unknown Vendor"


def _guess_category(raw_text: str) -> str:
    """Pick the category with the most whole-word keyword hits (no substring noise)."""
    lower = raw_text.lower()
    best, best_hits = "Other", 0
    for category, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", lower))
        if hits > best_hits:
            best, best_hits = category, hits
    return best


def _find_total(lines: List[str]) -> float:
    # Search bottom-up so the grand total wins over an earlier subtotal.
    for line in reversed(lines):
        if _NOT_THE_TOTAL.search(line):
            continue
        m = TOTAL_PATTERN.search(line)
        if m:
            value = _to_float(m.group(2))
            if value > 0:
                return value
    return 0.0


def _find_items(lines: List[str]) -> List[Tuple[str, float]]:
    items: List[Tuple[str, float]] = []
    for line in lines:
        m = LINE_ITEM_PATTERN.match(line)
        if not m:
            continue
        name, price = m.group(1).strip(), _to_float(m.group(2))
        if price <= 0:
            continue
        if any(w in name.lower() for w in _NOT_ITEM_WORDS):
            continue
        if sum(c.isalpha() for c in name) < 2:
            continue
        items.append((name, price))
    return items


def parse_receipt_to_dict(raw_text: str, avg_score: Optional[float] = None) -> dict:
    """
    Convert raw local OCR text into the raw extraction schema that
    normalize_extraction() expects (same keys the Gemini prompt asks for).

    avg_score: mean OCR confidence (0-1) if the engine provides it. Local mode
    never reports "high" legibility, so its results always get a human glance.
    """
    raw_text = raw_text or ""
    if len(raw_text.strip()) < 10:
        return {"document_type": "other", "legibility": "low", "items": [], "total": 0, "raw_text": raw_text}

    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    legibility = "medium" if (avg_score is None or avg_score >= 0.75) else "low"

    total = _find_total(lines)
    items = _find_items(lines)

    date_match = DATE_PATTERN.search(raw_text)
    date_text = date_match.group(1) if date_match else None

    gstin_match = GSTIN_PATTERN.search(raw_text.upper())
    invoice_match = INVOICE_NO_PATTERN.search(raw_text)

    if gstin_match:
        doc_type = "gst_invoice"
    elif len(items) >= 3 and total == 0 and not date_text:
        doc_type = "menu"   # lots of prices but no transaction evidence
    else:
        doc_type = "printed_receipt"

    return {
        "document_type": doc_type,
        "legibility": legibility,
        "vendor_name": _guess_vendor_name(lines),
        "vendor_gstin": gstin_match.group(0) if gstin_match else None,
        "invoice_number": invoice_match.group(1) if invoice_match else None,
        "date": date_text,
        "total": total,
        "category": _guess_category(raw_text),
        "items": [
            {"name": n, "quantity": 1, "unit_price": p, "total_price": p}
            for n, p in items
        ],
        "raw_text": raw_text,
    }

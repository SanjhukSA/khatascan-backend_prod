"""Accept / review / reject policy for extracted documents.

The OCR engines only *describe* what they see (document type, legibility,
totals, items). All policy lives here, as a pure function, so it can be tuned
and unit-tested without touching a prompt or calling any API.
"""

from dataclasses import dataclass, field
from typing import List, Optional

REJECT_TYPES = {"menu", "id_card", "other"}

_TYPE_LABELS = {
    "menu": "menu or price list",
    "id_card": "ID card",
    "other": "non-receipt document",
}

ACCEPTED = "accepted"
NEEDS_REVIEW = "needs_review"
REJECTED = "rejected"


@dataclass
class Verdict:
    status: str  # accepted | needs_review | rejected
    reasons: List[str] = field(default_factory=list)

    @property
    def reason(self) -> Optional[str]:
        return " ".join(self.reasons) if self.reasons else None


def decide(data: dict, force: bool = False) -> Verdict:
    """
    Decide what to do with a normalized extraction (see normalize_extraction).

    1. Nothing priced and no total → rejected. Not overridable: there is
       nothing to save.
    2. Menu / ID card / other → rejected, unless `force` (the user says
       "this is a receipt"), in which case it becomes needs_review.
    3. Anything shaky → needs_review, with every reason listed.
    4. Otherwise → accepted.

    Receipts with no line items but a clear total (utility bills, UPI
    screenshots) are valid, so "no items" alone is not a rejection.
    """
    doc_type = data.get("document_type", "other")
    total = data.get("total", 0) or 0
    priced_items = [i for i in data.get("items") or [] if (i.get("total_price") or 0) > 0]

    if not priced_items and total <= 0:
        return Verdict(REJECTED, ["No prices or total found on this image."])

    reasons: List[str] = []

    if doc_type in REJECT_TYPES:
        label = _TYPE_LABELS[doc_type]
        if not force:
            return Verdict(REJECTED, [f"This looks like a {label}, not a receipt."])
        reasons.append(f"Looked like a {label}; accepted because you confirmed it's a receipt.")

    if doc_type == "handwritten_bill":
        reasons.append("Handwritten bill, please check the values.")

    if data.get("legibility") == "low":
        reasons.append("The image is hard to read, please check the values.")

    if data.get("is_partial_page"):
        page, pages = data.get("page_number"), data.get("page_count")
        where = f"page {page} of {pages}" if page and pages else "one page of a longer invoice"
        reasons.append(
            f"This is {where}. The total shown is this page's total, "
            "the invoice's grand total is on the last page."
        )

    if data.get("total_auto_corrected"):
        reasons.append("No total was printed, so it was calculated from the items.")
    elif not data.get("has_total") and not data.get("has_date"):
        reasons.append("No total or date was found.")

    if data.get("totals_match") is False and not data.get("is_partial_page"):
        reasons.append(
            f"Line items add up to {data.get('item_sum')}, which doesn't match the total."
        )

    if data.get("date_problem"):
        reasons.append(data["date_problem"])

    if doc_type == "gst_invoice" and not data.get("vendor_gstin"):
        reasons.append("Seller GSTIN is missing or unreadable.")

    reasons.extend(data.get("merge_issues") or [])   # set by merge_pages for multi-page invoices

    return Verdict(NEEDS_REVIEW if reasons else ACCEPTED, reasons)

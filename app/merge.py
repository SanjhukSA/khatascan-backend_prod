"""Merge the per-page extractions of a multi-page invoice into one receipt.

Pure functions (no I/O). Input pages are normalized extractions
(see app.normalize.normalize_extraction); the output has the same shape plus
`page_order` and `merge_issues`, so decide() and the API treat it like any other
extraction.
"""

from datetime import date
from typing import List, Optional

from app.decision import REJECT_TYPES
from app.normalize import normalize_extraction

_LEVELS = ["low", "medium", "high"]


class MergeError(ValueError):
    """The pages can't be one invoice (different invoices, or the same page twice)."""


def _first(pages: List[dict], key: str, empty=(None, "")):
    for p in pages:
        if p.get(key) not in empty:
            return p[key]
    return None


def _join(nums: List[int]) -> str:
    return ", ".join(str(n) for n in nums)


def merge_pages(pages: List[dict], today: Optional[date] = None) -> dict:
    """
    Combine page extractions (in upload order) into one extraction.

    - Pages are re-ordered by their printed page number when every page has one;
      `page_order` lists the original positions in the new order.
    - Header fields (seller, GSTIN, invoice no, date, category...) come from the
      first page that has them. Items are concatenated in page order.
    - The grand total comes from the final page. If the final page wasn't
      uploaded, the total is the sum of the uploaded items and the problem is
      reported in `merge_issues`.
    - Raises MergeError for pages of different invoices or a repeated page number.
    """
    if not pages:
        raise MergeError("No pages to merge.")

    order = list(range(len(pages)))
    nums = [p.get("page_number") for p in pages]
    numbered = all(nums)

    if numbered:
        dupes = sorted({n for n in nums if nums.count(n) > 1})
        if dupes:
            raise MergeError(f"Page {_join(dupes)} was uploaded more than once.")
        order.sort(key=lambda i: nums[i])
    ordered = [pages[i] for i in order]

    invoice_numbers = {p["invoice_number"] for p in ordered if p.get("invoice_number")}
    gstins = {p["vendor_gstin"] for p in ordered if p.get("vendor_gstin")}
    if len(invoice_numbers) > 1 or len(gstins) > 1:
        raise MergeError(
            "These pages come from different invoices"
            + (f" ({', '.join(sorted(invoice_numbers))})." if len(invoice_numbers) > 1 else ".")
        )

    issues: List[str] = []

    # ── Completeness ─────────────────────────────────────────────────
    declared = max((p.get("page_count") or 0 for p in ordered), default=0)
    if numbered:
        expected = max(declared, max(nums))
        missing = sorted(set(range(1, expected + 1)) - set(nums))
        if missing:
            issues.append(f"Missing page(s) {_join(missing)} of {expected}.")
    elif declared and len(ordered) < declared:
        issues.append(f"Only {len(ordered)} of {declared} pages were uploaded.")

    for n, p in enumerate(ordered, start=1):
        if p.get("document_type") in REJECT_TYPES:
            label = p.get("page_number") or n
            issues.append(f"Page {label} doesn't look like part of a receipt.")

    # ── Totals ───────────────────────────────────────────────────────
    items = [i for p in ordered for i in p["items"]]
    item_sum = round(sum(i["total_price"] for i in items), 2)

    last = ordered[-1]
    last_is_final = not last.get("is_partial_page") or bool(
        last.get("page_number") and last.get("page_count") and last["page_number"] >= last["page_count"]
    )

    if last_is_final and last.get("has_total"):
        total, tax_total, discount_total = last["total"], last["tax_total"], last["discount_total"]
    elif last_is_final:
        total, tax_total, discount_total = 0, 0, 0     # normalize will compute it and flag it
    else:
        total, tax_total, discount_total = item_sum, 0, 0
        issues.append(
            "The grand total is on the last page, which wasn't uploaded. "
            "The total shown is the sum of the uploaded pages."
        )

    date_page = next((p for p in ordered if p.get("date")), ordered[0])
    best_level = min((p.get("legibility", "medium") for p in ordered), key=_LEVELS.index)

    merged = normalize_extraction(
        {
            "document_type": _first(ordered, "document_type", empty=(None, "", "other")) or "other",
            "engine": last.get("engine"),
            "vendor_name": _first(ordered, "vendor_name", empty=(None, "", "Unknown Vendor")),
            "vendor_gstin": _first(ordered, "vendor_gstin"),
            "invoice_number": _first(ordered, "invoice_number"),
            "date": date_page.get("date"),
            "total": total,
            "tax_total": tax_total,
            "discount_total": discount_total,
            "currency": _first(ordered, "currency"),
            "category": _first(ordered, "category", empty=(None, "", "Other")),
            "legibility": best_level,
            "page_count": declared or None,
            "items": items,
            "raw_text": "\n\n".join(
                f"--- page {i} ---\n{p.get('raw_text', '')}" for i, p in enumerate(ordered, start=1)
            ),
        },
        today=today,
    )
    merged["page_order"] = order
    merged["merge_issues"] = issues
    return merged

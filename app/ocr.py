"""Receipt OCR engine backed by Google Gemini.

Returns a normalized dict (see app.normalize); the accept / review / reject
policy lives in app.decision, not here.
"""

import io
import json
import re
import uuid
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image, ImageOps
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.normalize import normalize_extraction

# Longest side before we downscale. Keeps Gemini payloads small and prevents
# memory spikes from 48 MP phone cameras.
_MAX_IMAGE_DIM = 1600
_THUMB_SIZE = (300, 300)


_EXTRACTION_PROMPT = """
You are a data extractor for receipts, bills and invoices (Indian and international).
The photo may be rotated, skewed or crumpled: read it in its correct orientation.
Ignore pen marks, ticks, circles and stamps drawn over the document.

Return ONLY one JSON object with these keys:

{
  "document_type": "printed_receipt | handwritten_bill | gst_invoice | invoice | utility_bill | payment_screenshot | menu | id_card | other",
  "legibility": "high | medium | low",
  "vendor_name": "the SELLER / shop / merchant who issued the document",
  "vendor_gstin": "seller's 15-character GSTIN, or null",
  "invoice_number": "invoice / bill number, or null",
  "date": "the invoice or transaction date exactly as printed, or null",
  "total": 0.00,
  "tax_total": 0.00,
  "discount_total": 0.00,
  "currency": "INR",
  "category": "one of: Groceries, Food & Dining, Transport, Shopping, Bills & Utilities, Health, Entertainment, Education, Other",
  "page_number": null,
  "page_count": null,
  "is_partial_page": false,
  "items": [
    {
      "name": "product or service name",
      "quantity": 1,
      "unit": "Pcs / Pac / Kg / Set ... or null",
      "unit_price": 0.00,
      "discount": 0.00,
      "taxable_value": 0.00,
      "tax_rate": 0.0,
      "tax_amount": 0.00,
      "total_price": 0.00,
      "hsn_code": "or null"
    }
  ],
  "raw_text": "all visible text, line by line"
}

Rules:
- document_type: "menu" = price list with no transaction; "id_card" = Aadhaar/PAN/passport etc.;
  "gst_invoice" = tax invoice with GSTIN and CGST/SGST/IGST columns; "other" = anything that is not a bill.
  A handwritten bill on plain paper is "handwritten_bill".
- legibility: "high" if clear print, "medium" if partly readable, "low" if handwritten-and-messy, blurry or damaged.
- vendor_name is the party SELLING. Never use the "Bill to" / "Ship to" / customer name.
- date is the invoice/transaction date, NOT the due date or payment date.
- total is the final payable amount (grand total), not a subtotal or cash tendered.
  If the invoice continues on another page ("Continued...", "Page 1 of 6") set is_partial_page=true,
  fill page_number/page_count, and put THIS PAGE's total in "total".
- Items: exclude tax rows, subtotals, round-off and the grand total row. Keep names clean:
  drop notes such as "MRP - 10/-" but keep the product and pack size.
  quantity defaults to 1.
  unit_price = rate per unit BEFORE discount and tax.
  discount = discount AMOUNT in currency (not a percent), 0 if none.
  taxable_value = line amount after discount, before tax (0 if not shown).
  tax_rate = combined GST percent (CGST% + SGST%, or IGST%), 0 if none.
  tax_amount = total tax on the line (CGST + SGST + IGST), 0 if none.
  total_price = the final amount of the line INCLUDING tax (the line's "Total" column).
  If there are no tax columns, total_price = quantity x unit_price - discount.
- Use null for text you cannot read; never invent values.
- Reply with ONLY valid JSON: no markdown fences, no explanation.
"""


# ═════════════════════════════════════════════════════════════════════════
#  Image helpers
# ═════════════════════════════════════════════════════════════════════════

def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Open, EXIF-rotate, convert to RGB, and downscale an image.
    Raises PIL.UnidentifiedImageError / OSError for files that are not images.
    """
    image = Image.open(io.BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)   # fixes phone photos that carry EXIF
    image = image.convert("RGB")

    w, h = image.size
    if max(w, h) > _MAX_IMAGE_DIM:
        scale = _MAX_IMAGE_DIM / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return image


def save_upload(image_bytes: bytes, upload_dir: str) -> tuple[str, str, str]:
    """
    Pre-process and save an uploaded image + thumbnail to disk.
    Returns (upload_id, image_path, thumbnail_path), paths relative to upload_dir.
    Decoding happens before anything is written, so a bad file leaves no debris.
    """
    image = preprocess_image(image_bytes)

    upload_id = str(uuid.uuid4())
    base_dir = Path(upload_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    image_path = f"{upload_id}.jpg"
    image.save(base_dir / image_path, format="JPEG", quality=85)

    thumb = image.copy()
    thumb.thumbnail(_THUMB_SIZE, Image.LANCZOS)
    thumb_path = f"{upload_id}_thumb.jpg"
    thumb.save(base_dir / thumb_path, format="JPEG", quality=75)

    return upload_id, image_path, thumb_path


# ═════════════════════════════════════════════════════════════════════════
#  Gemini engine
# ═════════════════════════════════════════════════════════════════════════

def _is_retryable(exc: BaseException) -> bool:
    """Retry on 503 (overloaded) and 429 (rate limited) Gemini API errors."""
    msg = str(exc)
    return "503" in msg or "429" in msg or "UNAVAILABLE" in msg or "RESOURCE_EXHAUSTED" in msg


def _parse_json(raw: str | None) -> dict:
    """Parse the model's reply, tolerating code fences, chatter around the JSON, or a one-item list."""
    if not raw or not raw.strip():
        raise RuntimeError("Gemini returned an empty response")
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise RuntimeError(f"Gemini returned non-JSON response: {raw[:300]}")
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini returned non-JSON response: {raw[:300]}") from exc
    if isinstance(data, list) and data and isinstance(data[0], dict):
        data = data[0]
    if not isinstance(data, dict):
        raise RuntimeError(f"Gemini returned unexpected JSON: {raw[:300]}")
    return data


class OcrEngine:
    """
    Receipt extractor backed by Google Gemini Flash (google-genai SDK).

    One multimodal call returns the document type, seller, dates, totals, tax,
    line items and raw text. Retries up to 4 times on 503/429 errors with
    exponential backoff (2 s → 4 s → 8 s → 16 s).
    """

    def __init__(self, api_key: str, model: str = "gemini-3.6-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _call_gemini(self, jpeg_bytes: bytes) -> str | None:
        image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
        response = self.client.models.generate_content(
            model=self.model,
            contents=[_EXTRACTION_PROMPT, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        return response.text

    def extract_receipt(self, image_bytes: bytes) -> dict:
        """Run extraction and return the normalized dict (see app.normalize)."""
        image = preprocess_image(image_bytes)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)

        data = _parse_json(self._call_gemini(buf.getvalue()))
        data["engine"] = "gemini"
        return normalize_extraction(data)

# Receipts
A high-performance FastAPI backend for receipt scanning ,expense tracking ,financial analytics and GST claim support.We can process local/domestic receipts processing pipeline supporting  both multimodal AI extraction and a privacy mode.
---

## Tech Stack

* **Framework:** FastAPI
* **Database & ORM:** PostgreSQL, SQLAlchemy
* **Validation & Settings:** Pydantic
* **Cloud OCR:** Google Gemini Flash 
* **Offline OCR:** RapidOCR
* **Image Processing:** Pillow 

---

## Current Project State:

1. **Upload (`POST /receipts/upload`)**: Uploads a receipt image, handles EXIF rotation and downscaling, saves the full image and thumbnail to disk, and returns a unique `upload_id` without incurring OCR costs.
2. **Process (`POST /receipts/{upload_id}/process`)**: Runs OCR on the uploaded image. Supports a 
  Privacy Mode :
   * `privacy_mode=false` (default): Uses Google Gemini Flash to extract structured JSON (vendor, date, total, category, items, and Indian GST/invoice numbers).
   * `privacy_mode=true`: Runs 100% offline using RapidOCR and local regex parsing (`parser.py`) for total privacy.
3. **Save (`POST /receipts`)**: Commits the reviewed and verified receipt and its line items to PostgreSQL.
4. **GET** (list, detail, image, thumbnail), PATCH, and DELETE are the CRUD endpoints. List has pagination, category filter, and sort. Delete also removes the image files.
5. **GET** /analytics/monthly and GET /analytics/categories give the monthly summary (with daily breakdown and 
previous-month comparison) and the category breakdown.

---

## TO-DO:
0. Test Edge Cases and fix bugs
1. Test on more receipts
2. GST claim service
3. Auth
4. Deploy


---
## API Endpoints Summary

### Receipts (`/receipts`)
* `POST /receipts/upload` — Upload an image file to get an `upload_id`.
* `POST /receipts/{upload_id}/process` — Run OCR extraction (supports `?privacy_mode=true`).
* `POST /receipts` — Save a confirmed receipt to the database.
* `GET /receipts` — List receipts with pagination, sorting, and category filters.
* `GET /receipts/{id}` — Get details for a single receipt.
* `PATCH /receipts/{id}` — Update specific receipt fields or line items.
* `DELETE /receipts/{id}` — Delete a receipt and its associated files from disk.
* `GET /receipts/{id}/image` — Serve the full-resolution receipt JPEG.
* `GET /receipts/{id}/thumbnail` — Serve the compressed receipt thumbnail.

### Analytics (`/analytics`)
* `GET /analytics/monthly` — Get spending summary, receipt counts, averages, and daily breakdowns for a given month.
* `GET /analytics/categories` — Get spending grouped by category with percentages and counts.

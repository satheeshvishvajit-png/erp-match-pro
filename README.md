# ERP Match Pro — 3-Way Matching Portal

A Streamlit + Odoo portal for Accounts Payable: upload a vendor invoice, OCR
pulls out its fields, the app fetches the linked PO and GRN from Odoo (or
reads them directly if you upload those documents too), compares Price
across all three, and either flags it ready for a human to click
**Submit to ERP** (on match) or routes it to a human for correction (on
mismatch). Built against the spec in `ERP_3Way_Matching_UseCase.pdf`, with
the match → validate → submit flow adjusted to mirror the company's
reference implementation ("CATNIP INFOTECH || ERP Automation Three-Way
Matching") rather than fully auto-exporting.

## Tech stack

Python, Streamlit, SQLAlchemy (SQLite by default, Postgres-ready), Odoo
(XML-RPC), EasyOCR, Plotly, openpyxl/xlsxwriter, fpdf2.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional (only if you want PDF invoice uploads, not just images):
# install poppler — macOS: brew install poppler | Ubuntu: apt install poppler-utils

streamlit run app.py
```

The app creates a local SQLite database (`data/erp_match_pro.db`) and seeds
demo users + a handful of invoices run through the real matching pipeline
on first launch, so the dashboard isn't empty.

**Demo logins** (also shown on the login screen):

| Role              | Email                     | Password  |
|-------------------|----------------------------|-----------|
| Admin             | admin@erpmatchpro.com      | admin123  |
| Accounts Payable  | ap@erpmatchpro.com         | ap12345   |
| Manager           | manager@erpmatchpro.com    | mgr12345  |

## How the workflow maps to the spec

Login → Dashboard → Upload Invoice → OCR Extraction → Fetch PO → Fetch GRN →
Compare → Match → Submit to ERP (manual) → Save History → Generate Reports.

1. **Upload Invoice** — drag & drop a PDF/image, or use the "Paste invoice
   text" tab if you don't want to install EasyOCR. OCR confidence is shown
   per extraction; you review/edit fields before saving. There's also an
   optional "attach PO / GRN documents" expander — upload those files
   directly instead of relying on the Odoo auto-fetch, matching the
   reference implementation's "upload all three documents" flow.
2. **3-Way Matching** — pulls the PO and GRN for the invoice's PO/GRN number
   from Odoo (mock or live, see below), or reads them from the documents you
   attached, and shows a green/yellow/red comparison table plus a per-field
   validation checklist (PO No / GRN No / Vendor / Quantity / Price). If
   `PO price == GRN price == Invoice price`, the invoice is marked `Matched`
   and a **Submit to ERP** button appears — export only happens once you
   click it, it is never automatic. Otherwise, the mismatch is highlighted
   and you must enter a correction reason to fix and re-validate, or skip
   and save it as `Pending Review` (not exported).
3. **Review Center** — searchable/filterable/paginated table of every
   invoice, bulk re-match, CSV export, and a per-invoice audit trail.
4. **Reports** — filter by date range / invoice no / PO no / price /
   status, then export Excel, CSV, or a PDF summary.
5. **Analytics** — vendor performance, monthly trend, mismatch reasons,
   processing time, and an upload-activity heatmap.
6. **Audit trail** — every upload, match run, correction, pending-review,
   export, login/logout is logged (`modules/utils/audit.py`, `AuditLog`
   table) and visible per-invoice in Review Center.

## Odoo integration

No live Odoo instance was available while building this, so it ships in
**mock mode** by default (`ODOO_MODE=mock` in `config.py`), backed by seeded
PO/GRN data in `modules/odoo/mock_data.py` — the app is fully demoable with
zero external setup.

To connect a real Odoo instance:

1. In Odoo, create the POs/GRNs you want to test against (Purchase app →
   Purchase Orders; the matching GRN is the linked `stock.picking`). Per the
   assignment's Test Data step: load 20-30 PO/GRN pairs first, with the same
   PO number/vendor/price you'll use on your sample invoices.
2. Set env vars (copy `.env.example` → `.env`):
   ```
   ODOO_MODE=live
   ODOO_URL=https://your-company.odoo.com
   ODOO_DB=your-db-name
   ODOO_USERNAME=api-user@yourcompany.com
   ODOO_API_KEY=your-api-key
   ```
3. Restart the app. `modules/odoo/client.py` implements the same interface
   as the mock client (`fetch_purchase_order`, `fetch_grn`,
   `export_vendor_bill`, `test_connection`) over standard XML-RPC — no
   custom Odoo module required. Test the connection from Settings →
   Odoo Connection.

Swapping mock → live requires no code changes anywhere else in the app;
everything goes through `modules/odoo/factory.get_odoo_client()`.

## OCR

`OCR_ENGINE=easyocr` (default) uses EasyOCR + pdf2image (PDFs are rendered
to images first, so `poppler` must be installed). First run downloads
EasyOCR's model weights (~100MB, needs internet once).

If you don't want the heavy EasyOCR/torch install, the field parser
(`modules/ocr/extractor.py:parse_invoice_text`) works standalone against any
text — use the Upload page's "Paste invoice text" tab.

## Project structure

```
app.py                     # login + navigation entry point
config.py                  # env-driven settings, color palette
modules/
  database.py               # SQLAlchemy engine/session
  models.py                 # Users, Invoices, POs, GRNs, MatchingResults,
                             # AuditLogs, Exports, Notifications, Settings
  auth.py                   # login/session/role checks
  seed.py                   # demo users + invoices run through real matching
  matching/engine.py        # 3-way match decision logic + correction flow
  odoo/                     # base interface, mock client, live XML-RPC client
  ocr/extractor.py          # EasyOCR pipeline + regex field parser
  reports/                  # Excel/CSV/PDF export
  utils/                    # CSS/design system, reusable components, audit log
pages/                      # one file per sidebar page (Streamlit multipage)
tests/                      # pytest unit tests (matching engine, OCR parser)
data/sample_invoices/       # drop test invoices here
```

## Running tests

```bash
pip install pytest
pytest
```

`tests/test_ocr_parser.py` covers the regex field parser (no OCR engine
needed). `tests/test_matching_engine.py` covers the match/mismatch/
correction/pending-review decision logic end-to-end against a temp SQLite
DB and the mock Odoo client.

## Notes on scope

This was built to match the actual assignment spec (`ERP_3Way_Matching_UseCase.pdf`):
Price is the field that gates the match/mismatch decision, exactly as in the
PDF's worked example. Vendor and Quantity are also compared and shown in the
UI (green/yellow/red) as supporting context, since Review Center lists them.

Two things were adjusted after comparing against the company's reference demo
video ("CATNIP INFOTECH || ERP Automation Three-Way Matching"):
- **Export is a manual "Submit to ERP" step**, not automatic. A match sets
  status `Matched`; a human clicks Submit to ERP to actually create the
  Odoo Vendor Bill (`modules/matching/engine.py:submit_to_erp`).
- **PO/GRN can be uploaded directly** as an alternative to the Odoo
  auto-fetch, via the Upload page's optional "attach PO / GRN documents"
  expander (`run_match(..., po_override=..., grn_override=...)`).

The reference video also validates a few more fields per-document (HSN
codes, line-item descriptions, CGST/SGST split) than this build does —
those weren't in the written assignment spec, so they were left out, but
the matching engine's field_results dict is structured so more fields could
be added the same way Vendor/Quantity/Price are today.

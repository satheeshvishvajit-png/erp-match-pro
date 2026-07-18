"""
Invoice OCR + field extraction.

Two-stage pipeline:
  1. `run_ocr(file_bytes, filename)`      -> raw text + a confidence score,
                                              using EasyOCR (falls back to a
                                              clear error message if EasyOCR
                                              isn't installed).
  2. `parse_invoice_text(raw_text)`        -> structured fields via regex.
     This stage has zero dependency on OCR and is fully unit-testable.

`extract_invoice_fields()` glues both stages together for the Upload page.
"""
import io
import re
from datetime import datetime

import config

_EASYOCR_READER = None
_EASYOCR_IMPORT_ERROR = None


def _get_easyocr_reader():
    """Lazily import + cache the EasyOCR reader. Heavy (torch) import, so we
    only pay for it the first time OCR actually runs."""
    global _EASYOCR_READER, _EASYOCR_IMPORT_ERROR
    if _EASYOCR_READER is not None:
        return _EASYOCR_READER
    if _EASYOCR_IMPORT_ERROR is not None:
        return None
    try:
        import easyocr
        _EASYOCR_READER = easyocr.Reader(config.OCR_LANGUAGES, gpu=False, verbose=False)
        return _EASYOCR_READER
    except Exception as exc:  # noqa: BLE001
        _EASYOCR_IMPORT_ERROR = str(exc)
        return None


def _pdf_to_images(file_bytes: bytes):
    from pdf2image import convert_from_bytes
    kwargs = {"dpi": 250}
    if config.POPPLER_PATH:
        # PATH lookup failed or was unreliable (common on Windows after a
        # fresh PATH edit) -- point pdf2image straight at the poppler bin
        # folder we auto-detected in config.py instead of relying on PATH.
        kwargs["poppler_path"] = config.POPPLER_PATH
    return convert_from_bytes(file_bytes, **kwargs)


def run_ocr(file_bytes: bytes, filename: str):
    """Returns (raw_text: str, confidence: float 0-100, engine: str, error: str|None)."""
    import numpy as np
    from PIL import Image

    reader = _get_easyocr_reader()
    if reader is None:
        return "", 0.0, "none", (
            _EASYOCR_IMPORT_ERROR
            or "OCR engine not available. Install EasyOCR (see requirements.txt) or paste invoice text manually."
        )

    try:
        images = []
        if filename.lower().endswith(".pdf"):
            images = _pdf_to_images(file_bytes)
        else:
            images = [Image.open(io.BytesIO(file_bytes)).convert("RGB")]

        all_text_lines = []
        all_confidences = []
        for img in images:
            result = reader.readtext(np.array(img))
            for _bbox, text, conf in result:
                all_text_lines.append(text)
                all_confidences.append(conf)

        raw_text = "\n".join(all_text_lines)
        avg_conf = (sum(all_confidences) / len(all_confidences) * 100) if all_confidences else 0.0
        return raw_text, round(avg_conf, 1), "easyocr", None
    except Exception as exc:  # noqa: BLE001
        return "", 0.0, "easyocr", f"OCR failed: {exc}"


# --------------------------------------------------------------------------
# Regex-based field parser (no OCR dependency -- unit tested directly)
# --------------------------------------------------------------------------
_PATTERNS = {
    "invoice_number": [
        r"invoice\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9\-\/]{4,20})",
        r"\bINV[\-\/]?\d{2,4}[\-\/]?\d{2,6}\b",
    ],
    "po_number": [
        r"(?:p\.?o\.?|purchase\s*order)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9\-\/]{4,20})",
        r"\bPO[\-\/]?\d{2,4}[\-\/]?\d{2,6}\b",
    ],
    "grn_number": [
        r"(?:g\.?r\.?n\.?|goods\s*receipt)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9\-\/]{4,20})",
        r"\bGRN[\-\/]?\d{2,4}[\-\/]?\d{2,6}\b",
    ],
    "vendor_name": [
        r"(?:vendor|supplier|from|bill\s*from)\s*[:\-]?\s*([A-Za-z0-9 &.,'\-]{3,60})",
    ],
    "invoice_date": [
        r"(?:invoice\s*date|date)\s*[:\-]?\s*(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})",
    ],
    "currency": [
        r"\b(INR|USD|EUR|GBP)\b",
        r"(₹|\$|€|£)",
    ],
    "grand_total": [
        r"(?:grand\s*total|total\s*amount|invoice\s*total|amount\s*due)\s*[:\-]?\s*[₹$€£]?\s*([\d,]+\.?\d*)",
    ],
    "gst": [
        r"(?:gst|tax|vat)\s*(?:amount)?\s*[:\-]?\s*[₹$€£]?\s*([\d,]+\.?\d*)",
    ],
    "unit_price": [
        r"(?:unit\s*price|price|rate)\s*[:\-]?\s*[₹$€£]?\s*([\d,]+\.?\d*)",
    ],
    "quantity": [
        r"(?:qty|quantity)\s*[:\-]?\s*(\d+)",
    ],
}

_CURRENCY_SYMBOLS = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP"}


def _first_match(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        m = re.search(pattern, text, flags)
        if m:
            return (m.group(1) if m.groups() else m.group(0)).strip()
    return None


def _to_float(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _to_date(value):
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_invoice_text(raw_text: str) -> dict:
    """Pure function: text in, structured invoice fields out. No I/O, fully
    unit-testable without an OCR engine installed."""
    text = raw_text or ""

    currency_raw = _first_match(_PATTERNS["currency"], text)
    currency = _CURRENCY_SYMBOLS.get(currency_raw, currency_raw) if currency_raw else "INR"

    fields = {
        "invoice_number": _first_match(_PATTERNS["invoice_number"], text),
        "po_number": _first_match(_PATTERNS["po_number"], text),
        "grn_number": _first_match(_PATTERNS["grn_number"], text),
        "vendor_name": _first_match(_PATTERNS["vendor_name"], text),
        "invoice_date": _to_date(_first_match(_PATTERNS["invoice_date"], text)),
        "currency": currency,
        "grand_total": _to_float(_first_match(_PATTERNS["grand_total"], text)),
        "gst": _to_float(_first_match(_PATTERNS["gst"], text)),
        "unit_price": _to_float(_first_match(_PATTERNS["unit_price"], text)),
        "quantity": _to_float(_first_match(_PATTERNS["quantity"], text)),
    }

    # If no explicit unit price was found but a grand total was, use total as
    # the price a 3-way match will compare (matches the spec's "Price" field).
    if fields["unit_price"] is None and fields["grand_total"] is not None:
        fields["unit_price"] = fields["grand_total"]

    return fields


def extract_invoice_fields(file_bytes: bytes, filename: str) -> dict:
    """Full pipeline used by the Upload page: OCR -> parse -> field dict
    (+ ocr metadata)."""
    raw_text, confidence, engine, error = run_ocr(file_bytes, filename)
    fields = parse_invoice_text(raw_text)
    fields.update({
        "ocr_raw_text": raw_text,
        "ocr_confidence": confidence,
        "ocr_engine": engine,
        "ocr_error": error,
    })
    return fields

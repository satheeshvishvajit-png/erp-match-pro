"""Unit tests for the regex-based invoice field parser (no OCR engine
required -- tests parse_invoice_text() directly)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.ocr.extractor import parse_invoice_text


SAMPLE_TEXT = """
INVOICE

Invoice No: INV-2024-007
Invoice Date: 15/03/2024
Vendor: Acme Trading Co
PO No: PO-2024-007
GRN No: GRN-2024-007

Qty: 40
Unit Price: 2500
GST Amount: 18000
Grand Total: 118000
Currency: INR
"""


def test_parses_invoice_number():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["invoice_number"] == "INV-2024-007"


def test_parses_po_number():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["po_number"] == "PO-2024-007"


def test_parses_grn_number():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["grn_number"] == "GRN-2024-007"


def test_parses_grand_total():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["grand_total"] == 118000.0


def test_parses_gst():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["gst"] == 18000.0


def test_parses_currency():
    fields = parse_invoice_text(SAMPLE_TEXT)
    assert fields["currency"] == "INR"


def test_handles_empty_text():
    fields = parse_invoice_text("")
    assert fields["invoice_number"] is None
    assert fields["grand_total"] is None


def test_falls_back_total_to_unit_price_when_missing():
    text = "Invoice No: INV-1\nGrand Total: 5000"
    fields = parse_invoice_text(text)
    assert fields["unit_price"] == 5000.0

"""Unit tests for the 3-way matching decision logic, using a temp SQLite DB
and the mock Odoo client (no network / external services needed)."""
import os
import sys
import tempfile
from pathlib import Path

TEST_DB_FD, TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["ODOO_MODE"] = "mock"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from modules.database import init_db, get_session  # noqa: E402
from modules.models import Invoice, InvoiceStatus  # noqa: E402
from modules.matching.engine import run_match, apply_correction, mark_pending_review, submit_to_erp  # noqa: E402

init_db()


def _make_invoice(**overrides):
    defaults = dict(
        invoice_number="TEST-INV-1",
        vendor_name="Tech Supplies Inc",
        po_number="PO-2024-001",
        grn_number="GRN-2024-001",
        currency="INR",
        unit_price=1000.0,
        quantity=100,
        tax_amount=18000.0,
        grand_total=118000.0,
        status=InvoiceStatus.UPLOADED,
    )
    defaults.update(overrides)
    session = get_session()
    try:
        inv = Invoice(**defaults)
        session.add(inv)
        session.commit()
        session.refresh(inv)
        return inv.id
    finally:
        session.close()


def test_exact_price_match_sets_matched_status():
    # PO-2024-001 / GRN-2024-001 total is exactly 118000 in the mock data.
    # A match no longer auto-exports -- it waits for an explicit
    # submit_to_erp() call, mirroring the reference implementation's
    # manual "Submit to ERP" button.
    invoice_id = _make_invoice(invoice_number="TEST-MATCH-1", grand_total=118000.0)
    result = run_match(invoice_id)
    assert result["is_match"] is True
    assert result["status"] == "Matched"


def test_submit_to_erp_exports_a_matched_invoice():
    invoice_id = _make_invoice(invoice_number="TEST-MATCH-2", grand_total=118000.0)
    run_match(invoice_id)
    outcome = submit_to_erp(invoice_id)
    assert outcome["status"] == "Exported"
    assert outcome["export_info"]["success"] is True


def test_submit_to_erp_rejects_a_non_matched_invoice():
    # Never run_match()'d, so it's still sitting in "Uploaded" status.
    invoice_id = _make_invoice(invoice_number="TEST-NOTMATCHED-1", grand_total=118000.0)
    outcome = submit_to_erp(invoice_id)
    assert "error" in outcome


def test_price_mismatch_flagged():
    invoice_id = _make_invoice(invoice_number="TEST-MISMATCH-1", grand_total=125000.0)
    result = run_match(invoice_id)
    assert result["is_match"] is False
    assert result["status"] == "Mismatch"
    assert result["field_results"]["price"]["status"] == "red"


def test_correction_requires_reason():
    invoice_id = _make_invoice(invoice_number="TEST-CORR-1", grand_total=125000.0)
    run_match(invoice_id)
    outcome = apply_correction(invoice_id, 118000.0, "", user_id=None)
    assert "error" in outcome


def test_correction_with_reason_revalidates_to_matched():
    invoice_id = _make_invoice(invoice_number="TEST-CORR-2", grand_total=125000.0)
    run_match(invoice_id)
    outcome = apply_correction(invoice_id, 118000.0, "Vendor billed wrong rate; corrected to PO price.", user_id=None)
    assert outcome["is_match"] is True
    assert outcome["status"] == "Matched"
    # and it can now be submitted
    export_outcome = submit_to_erp(invoice_id)
    assert export_outcome["status"] == "Exported"


def test_skip_correction_marks_pending_review():
    invoice_id = _make_invoice(invoice_number="TEST-PENDING-1", grand_total=125000.0)
    run_match(invoice_id)
    outcome = mark_pending_review(invoice_id)
    assert outcome["status"] == "Pending Review"


def test_unknown_po_number_does_not_match():
    invoice_id = _make_invoice(invoice_number="TEST-NOPO-1", po_number="PO-DOES-NOT-EXIST", grand_total=100.0)
    result = run_match(invoice_id)
    assert result["is_match"] is False
    assert result["po_data"] is None


def test_po_override_skips_odoo_lookup():
    # Simulate uploading a PO document directly instead of relying on the
    # Odoo auto-fetch -- the override's price should be what's compared.
    invoice_id = _make_invoice(invoice_number="TEST-OVERRIDE-1", po_number="PO-CUSTOM-999",
                                grn_number="GRN-CUSTOM-999", grand_total=50000.0)
    po_override = {
        "po_number": "PO-CUSTOM-999", "vendor_name": "Tech Supplies Inc", "quantity": 10,
        "unit_price": 5000.0, "tax_amount": 0.0, "total_price": 50000.0, "currency": "INR",
        "order_date": None, "status": "Confirmed",
    }
    grn_override = {
        "grn_number": "GRN-CUSTOM-999", "po_number": "PO-CUSTOM-999", "vendor_name": "Tech Supplies Inc",
        "quantity_received": 10, "unit_price": 5000.0, "total_price": 50000.0, "currency": "INR",
        "delivery_date": None, "status": "Received",
    }
    result = run_match(invoice_id, po_override=po_override, grn_override=grn_override)
    assert result["is_match"] is True
    assert result["po_data"]["po_number"] == "PO-CUSTOM-999"


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        os.remove(TEST_DB_PATH)
    except OSError:
        pass

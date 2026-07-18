"""
3-Way Matching engine.

Per the spec: the pass/fail decision is driven by Price agreement across
PO / GRN / Invoice (within PRICE_MATCH_TOLERANCE, to absorb rounding).
  PO price == GRN price == Invoice price  -> MATCH -> ready to export
  otherwise                                -> MISMATCH -> user must correct
                                               (with a reason) or the record
                                               is saved as Pending Review.

Export to Odoo is a separate, explicit step (see submit_to_erp()) rather
than automatic -- a matched invoice sits in "Matched" status until a human
clicks "Submit to ERP", mirroring how the reference implementation works.

We additionally compare Vendor and Quantity as informational fields (shown
as green/yellow/red in the Review UI) since the comparison table in the
spec lists them, but only Price gates the match decision -- exactly
matching the PDF's worked example.
"""
import json
from datetime import datetime

import config
from modules.database import get_session
from modules.models import Invoice, PurchaseOrder, GRN, MatchingResult, InvoiceStatus, Export
from modules.odoo.factory import get_odoo_client
from modules.utils.audit import log_action


def _status(a, b, numeric=True, tolerance=0.0):
    """Returns 'green' | 'yellow' | 'red' for a single field comparison."""
    if a is None or b is None:
        return "yellow"  # can't compare -> needs human eyes
    if numeric:
        try:
            return "green" if abs(float(a) - float(b)) <= tolerance else "red"
        except (TypeError, ValueError):
            return "yellow"
    return "green" if str(a).strip().lower() == str(b).strip().lower() else "red"


def fetch_po_and_grn(po_number: str, grn_number: str, po_override: dict = None, grn_override: dict = None):
    """Pulls PO + GRN and upserts local mirror rows (PurchaseOrder / GRN
    tables) so Review Center can display them without re-hitting Odoo.

    If po_override / grn_override dicts are supplied (built from a directly
    uploaded PO/GRN document instead of an Odoo lookup -- see the Upload
    page), those are used as-is and Odoo is not queried for that document.
    This mirrors the reference implementation's "upload all three documents"
    flow as an alternative to the Odoo auto-fetch."""
    client = get_odoo_client()
    po_data = po_override if po_override else (client.fetch_purchase_order(po_number) if po_number else None)
    grn_data = grn_override if grn_override else (client.fetch_grn(grn_number, po_number) if grn_number else None)

    session = get_session()
    try:
        if po_data:
            po_row = session.query(PurchaseOrder).filter_by(po_number=po_data["po_number"]).first()
            if not po_row:
                po_row = PurchaseOrder(po_number=po_data["po_number"])
                session.add(po_row)
            for k, v in po_data.items():
                setattr(po_row, k, v)
            session.commit()

        if grn_data:
            grn_row = session.query(GRN).filter_by(grn_number=grn_data["grn_number"]).first()
            if not grn_row:
                grn_row = GRN(grn_number=grn_data["grn_number"])
                session.add(grn_row)
            for k, v in grn_data.items():
                setattr(grn_row, k, v)
            session.commit()
    finally:
        session.close()

    return po_data, grn_data


def run_match(invoice_id: str, user_id: str = None, po_override: dict = None, grn_override: dict = None) -> dict:
    """Runs (or re-runs) the 3-way match for an invoice. On success the
    invoice is marked "Matched" and waits for an explicit submit_to_erp()
    call -- it is not exported automatically. Returns a UI-ready result dict."""
    session = get_session()
    try:
        invoice = session.query(Invoice).filter_by(id=invoice_id).first()
        if invoice is None:
            return {"error": "Invoice not found."}

        po_data, grn_data = fetch_po_and_grn(invoice.po_number, invoice.grn_number,
                                              po_override=po_override, grn_override=grn_override)

        po_price = po_data["total_price"] if po_data else None
        grn_price = grn_data["total_price"] if grn_data else None
        invoice_price = invoice.grand_total

        tolerance = config.PRICE_MATCH_TOLERANCE
        price_variance = None
        if po_price is not None and invoice_price is not None:
            price_variance = round(invoice_price - po_price, 2)

        is_match = (
            po_data is not None and grn_data is not None and
            _status(po_price, grn_price, tolerance=tolerance) == "green" and
            _status(grn_price, invoice_price, tolerance=tolerance) == "green"
        )

        field_results = {
            "vendor": {
                "po": po_data["vendor_name"] if po_data else None,
                "grn": grn_data["vendor_name"] if grn_data else None,
                "invoice": invoice.vendor_name,
                "status": _status(
                    po_data["vendor_name"] if po_data else None,
                    invoice.vendor_name, numeric=False,
                ),
            },
            "quantity": {
                "po": po_data["quantity"] if po_data else None,
                "grn": grn_data["quantity_received"] if grn_data else None,
                "invoice": invoice.quantity,
                "status": _status(po_data["quantity"] if po_data else None, invoice.quantity, tolerance=0.01),
            },
            "price": {
                "po": po_price,
                "grn": grn_price,
                "invoice": invoice_price,
                "status": "green" if is_match else ("yellow" if (po_price is None or grn_price is None) else "red"),
            },
        }

        result = MatchingResult(
            invoice_id=invoice.id,
            po_price=po_price,
            grn_price=grn_price,
            invoice_price=invoice_price,
            price_variance=price_variance,
            is_match=is_match,
            field_results_json=json.dumps(field_results, default=str),
        )
        session.add(result)

        log_action(invoice.id, user_id, "MATCH_RUN",
                    f"PO={po_price} GRN={grn_price} INV={invoice_price} -> {'MATCH' if is_match else 'MISMATCH'}")

        if is_match:
            # Matched, but NOT exported yet -- waits for an explicit
            # "Submit to ERP" action (see submit_to_erp() below).
            invoice.status = InvoiceStatus.MATCHED
        else:
            # Only downgrade to Mismatch if not already sitting in Pending Review
            if invoice.status != InvoiceStatus.PENDING_REVIEW:
                invoice.status = InvoiceStatus.MISMATCH

        session.commit()

        return {
            "invoice_id": invoice.id,
            "is_match": is_match,
            "status": invoice.status.value if hasattr(invoice.status, "value") else invoice.status,
            "field_results": field_results,
            "po_data": po_data,
            "grn_data": grn_data,
        }
    finally:
        session.close()


def submit_to_erp(invoice_id: str, user_id: str = None) -> dict:
    """Explicit, human-triggered step: pushes a Matched invoice to Odoo as a
    Vendor Bill. Mirrors the reference implementation's "Submit to ERP"
    button -- export is never automatic. Only allowed once the invoice's
    latest match was a success (status == Matched)."""
    session = get_session()
    try:
        invoice = session.query(Invoice).filter_by(id=invoice_id).first()
        if invoice is None:
            return {"error": "Invoice not found."}
        if invoice.status != InvoiceStatus.MATCHED:
            current_status = invoice.status.value if hasattr(invoice.status, "value") else invoice.status
            return {"error": f"Invoice is not in Matched status (currently {current_status}). "
                              f"Run the match again before submitting."}

        client = get_odoo_client()
        export_result = client.export_vendor_bill({
            "invoice_number": invoice.invoice_number,
            "vendor_name": invoice.vendor_name,
            "po_number": invoice.po_number,
            "quantity": invoice.quantity,
            "unit_price": invoice.unit_price,
        })

        if export_result.get("success"):
            invoice.status = InvoiceStatus.EXPORTED
            invoice.exported_at = datetime.utcnow()
            session.add(Export(
                invoice_id=invoice.id,
                odoo_vendor_bill_id=export_result.get("odoo_bill_id"),
                odoo_vendor_bill_ref=export_result.get("reference"),
                exported_by=user_id,
            ))
            session.commit()
            log_action(invoice.id, user_id, "EXPORTED", export_result.get("message"))
        else:
            session.commit()
            log_action(invoice.id, user_id, "EXPORT_FAILED", export_result.get("message"))

        return {
            "invoice_id": invoice.id,
            "status": invoice.status.value if hasattr(invoice.status, "value") else invoice.status,
            "export_info": export_result,
        }
    finally:
        session.close()


def apply_correction(invoice_id: str, corrected_price: float, reason: str, user_id: str = None) -> dict:
    """User edits the mismatched price and supplies a mandatory reason.
    The record is re-validated automatically afterward."""
    if not reason or not reason.strip():
        return {"error": "A correction reason is required."}

    session = get_session()
    try:
        invoice = session.query(Invoice).filter_by(id=invoice_id).first()
        if invoice is None:
            return {"error": "Invoice not found."}
        old_price = invoice.grand_total
        invoice.grand_total = corrected_price
        invoice.correction_reason = reason.strip()
        invoice.status = InvoiceStatus.UPLOADED  # reset so run_match re-evaluates cleanly
        session.commit()

        log_action(invoice.id, user_id, "CORRECTED",
                    f"Price changed {old_price} -> {corrected_price}. Reason: {reason.strip()}")
    finally:
        session.close()

    return run_match(invoice_id, user_id=user_id)


def mark_pending_review(invoice_id: str, user_id: str = None) -> dict:
    """User chooses to skip correction: record is saved as Pending Review,
    not exported."""
    session = get_session()
    try:
        invoice = session.query(Invoice).filter_by(id=invoice_id).first()
        if invoice is None:
            return {"error": "Invoice not found."}
        invoice.status = InvoiceStatus.PENDING_REVIEW
        session.commit()
        log_action(invoice.id, user_id, "PENDING_REVIEW", "User skipped correction; saved for later review.")
        return {"invoice_id": invoice.id, "status": invoice.status.value}
    finally:
        session.close()

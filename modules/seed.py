"""
Seeds demo data (users + invoices run through the real matching pipeline,
including the explicit Submit-to-ERP step) so the app isn't an empty shell
on first launch. Idempotent: only runs when the relevant tables are empty.
"""
from datetime import datetime, timedelta

from modules.database import get_session
from modules.models import User, Invoice, InvoiceStatus
from modules import auth
from modules.matching.engine import run_match, apply_correction, mark_pending_review, submit_to_erp


def seed_demo_users():
    session = get_session()
    try:
        if session.query(User).count() > 0:
            return
    finally:
        session.close()

    from modules.models import UserRole
    demo_users = [
        ("Alex Morgan", "admin@erpmatchpro.com", "admin123", UserRole.ADMIN, "#2563EB"),
        ("Priya Sharma", "ap@erpmatchpro.com", "ap12345", UserRole.ACCOUNTS_PAYABLE, "#10B981"),
        ("Daniel Cole", "manager@erpmatchpro.com", "mgr12345", UserRole.MANAGER, "#F59E0B"),
    ]
    for name, email, pwd, role, color in demo_users:
        auth.create_user(name, email, pwd, role, color)


DEMO_INVOICES = [
    # invoice_number, vendor, po, grn, qty, unit_price, tax, grand_total (matches PO -> auto exports)
    dict(invoice_number="INV-2024-001", vendor_name="Tech Supplies Inc", po_number="PO-2024-001",
         grn_number="GRN-2024-001", quantity=100, unit_price=1000.0, tax_amount=18000.0,
         grand_total=118000.0, days_ago=6, confidence=96.4),
    dict(invoice_number="INV-2024-003", vendor_name="Engineering Co", po_number="PO-2024-003",
         grn_number="GRN-2024-003", quantity=20, unit_price=11500.0, tax_amount=41400.0,
         grand_total=271400.0, days_ago=5, confidence=91.2),
    dict(invoice_number="INV-2024-004", vendor_name="Supplies Hub", po_number="PO-2024-004",
         grn_number="GRN-2024-004", quantity=35, unit_price=1300.0, tax_amount=8190.0,
         grand_total=53690.0, days_ago=4, confidence=98.1),
    # mismatch -> will get corrected in the seed flow
    dict(invoice_number="INV-2024-002", vendor_name="Office Products Ltd", po_number="PO-2024-002",
         grn_number="GRN-2024-002", quantity=50, unit_price=1590.0, tax_amount=13500.0,
         grand_total=93000.0, days_ago=3, confidence=88.7, correct_after=True),
    # mismatch -> left as pending review
    dict(invoice_number="INV-2024-005", vendor_name="Paper Co", po_number="PO-2024-005",
         grn_number="GRN-2024-005", quantity=200, unit_price=520.0, tax_amount=17640.0,
         grand_total=121640.0, days_ago=1, confidence=79.5, pending=True),
]


def seed_demo_invoices():
    session = get_session()
    try:
        if session.query(Invoice).count() > 0:
            return
        ap_user = session.query(User).filter_by(email="ap@erpmatchpro.com").first()
        ap_user_id = ap_user.id if ap_user else None
    finally:
        session.close()

    for spec in DEMO_INVOICES:
        session = get_session()
        try:
            inv = Invoice(
                invoice_number=spec["invoice_number"],
                vendor_name=spec["vendor_name"],
                po_number=spec["po_number"],
                grn_number=spec["grn_number"],
                invoice_date=datetime.utcnow() - timedelta(days=spec["days_ago"]),
                currency="INR",
                unit_price=spec["unit_price"],
                quantity=spec["quantity"],
                tax_amount=spec["tax_amount"],
                grand_total=spec["grand_total"],
                ocr_confidence=spec["confidence"],
                status=InvoiceStatus.UPLOADED,
                uploaded_by=ap_user_id,
                created_at=datetime.utcnow() - timedelta(days=spec["days_ago"]),
            )
            session.add(inv)
            session.commit()
            invoice_id = inv.id
        finally:
            session.close()

        outcome = run_match(invoice_id, user_id=ap_user_id)

        if spec.get("correct_after"):
            # simulate the AP user fixing the mismatched price with a reason
            outcome = apply_correction(invoice_id, 88500.0, "Vendor issued a corrected invoice matching the PO rate.",
                                        user_id=ap_user_id)
        elif spec.get("pending"):
            mark_pending_review(invoice_id, user_id=ap_user_id)
            outcome = None

        # Matched invoices still need an explicit "Submit to ERP" click in
        # the real UI -- do that here too so demo data shows Exported
        # entries rather than everything stuck on Matched.
        if outcome and outcome.get("is_match"):
            submit_to_erp(invoice_id, user_id=ap_user_id)


def seed_all():
    seed_demo_users()
    seed_demo_invoices()

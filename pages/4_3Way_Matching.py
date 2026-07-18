"""3-Way Matching: live PO/GRN fetch, comparison table, decision logic,
mismatch correction with mandatory reason + revalidation, and an explicit
"Submit to ERP" step on a successful match (export is never automatic --
mirrors the reference implementation)."""
import json
import time

import streamlit as st

from modules import auth
from modules.database import get_session
from modules.models import Invoice, MatchingResult, InvoiceStatus
from modules.matching.engine import run_match, apply_correction, mark_pending_review, submit_to_erp
from modules.utils.components import (
    page_header, match_comparison_table, status_badge_html, success_celebration, validation_checklist,
)
from modules.utils.styling import inject_css

auth.require_login()
inject_css()
user = auth.current_user()

page_header("3-Way Matching", "Compare Purchase Order, Goods Receipt Note, and Invoice values.")

session = get_session()
try:
    open_invoices = (
        session.query(Invoice)
        .filter(Invoice.status.in_([
            InvoiceStatus.UPLOADED, InvoiceStatus.MISMATCH, InvoiceStatus.PENDING_REVIEW,
            InvoiceStatus.MATCHED, InvoiceStatus.EXPORTED,
        ]))
        .order_by(Invoice.created_at.desc())
        .all()
    )
    options = {f"{i.invoice_number} — {i.vendor_name or 'Unknown vendor'} ({i.status.value})": i.id for i in open_invoices}
finally:
    session.close()

if not options:
    st.info("No invoices yet. Upload one first.")
    st.stop()

default_id = st.session_state.get("selected_invoice_id")
default_label = next((k for k, v in options.items() if v == default_id), list(options.keys())[0])

selected_label = st.selectbox("Select invoice", list(options.keys()),
                               index=list(options.keys()).index(default_label))
invoice_id = options[selected_label]
st.session_state["selected_invoice_id"] = invoice_id

auto_run = st.session_state.pop("run_match_on_load", False)
po_override = st.session_state.pop("po_override", None) if auto_run else None
grn_override = st.session_state.pop("grn_override", None) if auto_run else None

col_a, col_b = st.columns([1, 5])
with col_a:
    run_clicked = st.button("\U0001F504 Fetch & Match", type="primary", use_container_width=True)

if auto_run or run_clicked:
    fetch_label = "Reading uploaded PO document..." if po_override else "\U0001F4E1 Fetching Purchase Order from Odoo..."
    grn_label = "Reading uploaded GRN document..." if grn_override else "\U0001F4E1 Fetching Goods Receipt Note from Odoo..."
    with st.status("Running 3-way match...", expanded=True) as status_box:
        st.write(fetch_label)
        time.sleep(0.25)
        st.write(grn_label)
        time.sleep(0.25)
        st.write("\U0001F50E Comparing values...")
        result = run_match(invoice_id, user_id=user["id"], po_override=po_override, grn_override=grn_override)
        time.sleep(0.2)
        status_box.update(label="Match complete", state="complete")
    st.session_state["last_match_result"] = result

result = st.session_state.get("last_match_result")
if not result or result.get("invoice_id") != invoice_id:
    # Load the most recent stored result instead of forcing a re-run
    session = get_session()
    try:
        mr = (
            session.query(MatchingResult)
            .filter(MatchingResult.invoice_id == invoice_id)
            .order_by(MatchingResult.run_at.desc())
            .first()
        )
        inv = session.query(Invoice).filter_by(id=invoice_id).first()
        if mr:
            result = {
                "invoice_id": invoice_id,
                "is_match": mr.is_match,
                "status": inv.status.value if inv else None,
                "field_results": json.loads(mr.field_results_json),
            }
    finally:
        session.close()

st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

if result and result.get("field_results"):
    fr = result["field_results"]

    with st.container(border=True):
        st.markdown("#### Comparison")
        match_comparison_table(fr)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Re-check the invoice's live status -- it may already have been
    # exported in an earlier visit to this page.
    session = get_session()
    try:
        inv = session.query(Invoice).filter_by(id=invoice_id).first()
        current_status = inv.status.value if inv and hasattr(inv.status, "value") else (inv.status if inv else None)
        po_no = inv.po_number if inv else None
        grn_no = inv.grn_number if inv else None
    finally:
        session.close()

    if current_status == "Exported":
        session = get_session()
        try:
            from modules.models import Export
            exp = (
                session.query(Export)
                .filter(Export.invoice_id == invoice_id)
                .order_by(Export.exported_at.desc())
                .first()
            )
            ref = exp.odoo_vendor_bill_ref if exp else None
        finally:
            session.close()
        success_celebration(f"Vendor bill {ref or ''} created in Odoo.".strip())

    elif result.get("is_match"):
        with st.container(border=True):
            st.markdown("#### Validation Results")
            validation_checklist([
                (f"PO No matched and validated ({po_no})", True),
                (f"GRN No matched and validated ({grn_no})", True),
                ("Vendor matched and validated", fr.get("vendor", {}).get("status") == "green"),
                ("Quantity matched across documents", fr.get("quantity", {}).get("status") == "green"),
                ("Price matched and validated", fr.get("price", {}).get("status") == "green"),
            ])
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            if st.button("\U0001F527 Submit to ERP", type="primary", use_container_width=True):
                outcome = submit_to_erp(invoice_id, user_id=user["id"])
                if outcome.get("error"):
                    st.error(outcome["error"])
                else:
                    st.session_state["last_match_result"] = None
                    st.rerun()

    else:
        st.markdown(f"""
        <div class="emp-card" style="border-color:#EF4444; background:#FEF2F2;">
            <div style="font-weight:800; color:#991B1B; font-size:16px;">⚠️ MISMATCH DETECTED</div>
            <div class="emp-caption" style="margin-top:4px;">Price disagrees across PO / GRN / Invoice. Correct the value below with a reason, or save for later review.</div>
        </div>
        """, unsafe_allow_html=True)

        price_row = fr.get("price", {})
        session = get_session()
        try:
            inv = session.query(Invoice).filter_by(id=invoice_id).first()
            current_total = inv.grand_total
        finally:
            session.close()

        with st.form("correction_form"):
            st.markdown(f"**PO Price:** {price_row.get('po')}  |  **GRN Price:** {price_row.get('grn')}  |  **Current Invoice Price:** {price_row.get('invoice')}")
            corrected_price = st.number_input("Corrected Invoice Price", value=float(current_total or 0), min_value=0.0)
            reason = st.text_area("Correction reason *", placeholder="e.g. Vendor applied wrong unit rate; corrected per PO agreement.")
            col1, col2 = st.columns(2)
            with col1:
                save_correct = st.form_submit_button("✅ Save Correction & Revalidate", type="primary", use_container_width=True)
            with col2:
                skip = st.form_submit_button("⏭ Skip — Save as Pending Review", use_container_width=True)

        if save_correct:
            outcome = apply_correction(invoice_id, corrected_price, reason, user_id=user["id"])
            if outcome.get("error"):
                st.error(outcome["error"])
            else:
                st.session_state["last_match_result"] = outcome
                st.success("Correction saved and re-validated.")
                st.rerun()

        if skip:
            mark_pending_review(invoice_id, user_id=user["id"])
            st.warning("Saved as Pending Review. It won't be exported until corrected.")
            time.sleep(0.3)
            st.rerun()
else:
    st.info("Click **Fetch & Match** to pull the PO/GRN from Odoo (or use uploaded PO/GRN documents) and compare against this invoice.")

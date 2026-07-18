"""Upload Invoice: drag & drop, OCR extraction, confidence-highlighted
review form, then hand off to the matching engine."""
import time
from datetime import datetime

import streamlit as st

import config
from modules import auth
from modules.database import get_session
from modules.models import Invoice, InvoiceStatus
from modules.ocr.extractor import extract_invoice_fields, parse_invoice_text
from modules.utils.components import page_header
from modules.utils.styling import inject_css
from modules.utils.audit import log_action

auth.require_login()
inject_css()
user = auth.current_user()

page_header("Upload Invoice", "Drop a vendor invoice (PDF or image) and let OCR pull out the key fields.")

if "ocr_fields" not in st.session_state:
    st.session_state["ocr_fields"] = None
if "ocr_filename" not in st.session_state:
    st.session_state["ocr_filename"] = None

tab_upload, tab_paste = st.tabs(["\U0001F4C4 Upload file", "\U0001F4DD Paste invoice text (no OCR install needed)"])

with tab_upload:
  with st.container(border=True):
    file = st.file_uploader(
        "Drag and drop invoice here",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Accepted formats: PDF, PNG, JPG. Max 25MB.",
    )

    if file is not None:
        col_prev, col_meta = st.columns([1, 1.3])
        with col_prev:
            if file.type.startswith("image"):
                st.image(file, use_container_width=True, caption=file.name)
            else:
                st.markdown(f"""
                <div style="border:1px solid #E5E7EB; border-radius:12px; padding: 40px 20px; text-align:center;">
                    <div style="font-size:40px;">\U0001F4C4</div>
                    <div style="font-weight:700; margin-top:8px;">{file.name}</div>
                    <div class="emp-caption">{round(file.size/1024, 1)} KB</div>
                </div>
                """, unsafe_allow_html=True)
        with col_meta:
            st.markdown(f"**File:** {file.name}")
            st.markdown(f"**Size:** {round(file.size/1024, 1)} KB")
            run = st.button("⚡ Run OCR Extraction", type="primary", use_container_width=True)
            if run:
                progress = st.progress(0, text="Preparing document...")
                for pct, label in [(20, "Loading OCR engine..."), (45, "Reading text regions..."),
                                    (70, "Parsing invoice fields..."), (95, "Finalizing...")]:
                    time.sleep(0.15)
                    progress.progress(pct, text=label)
                fields = extract_invoice_fields(file.getvalue(), file.name)
                progress.progress(100, text="Done")
                time.sleep(0.1)
                progress.empty()

                if fields.get("ocr_error"):
                    st.warning(f"{fields['ocr_error']}")
                st.session_state["ocr_fields"] = fields
                st.session_state["ocr_filename"] = file.name
                # Keep the actual file bytes so we can save them to disk once
                # the invoice is saved below (only the filename was ever
                # persisted before -- the file itself was discarded).
                st.session_state["ocr_file_bytes"] = file.getvalue()

with tab_paste:
  with st.container(border=True):
    st.caption("Paste raw invoice text (e.g. copied from a PDF) to test field extraction without an OCR engine installed.")
    pasted = st.text_area("Invoice text", height=180, placeholder="Invoice No: INV-2024-006\nVendor: Acme Corp\nPO No: PO-2024-006\n...")
    if st.button("Parse text", use_container_width=True):
        fields = parse_invoice_text(pasted)
        fields.update({"ocr_raw_text": pasted, "ocr_confidence": 100.0, "ocr_engine": "manual", "ocr_error": None})
        st.session_state["ocr_fields"] = fields
        st.session_state["ocr_filename"] = "pasted-text.txt"
        st.session_state["ocr_file_bytes"] = None


def confidence_color(pct):
    if pct is None:
        return "#9CA3AF"
    if pct >= 90:
        return "#10B981"
    if pct >= 70:
        return "#F59E0B"
    return "#EF4444"


fields = st.session_state.get("ocr_fields")
if fields:
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    conf = fields.get("ocr_confidence") or 0.0
    st.markdown(f"""
    <div class="emp-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h4 style="margin:0;">Extracted Fields</h4>
            <span class="badge" style="background:{confidence_color(conf)}22; color:{confidence_color(conf)};">
                AI Confidence: {conf}%
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("\U0001F4CE Optionally attach PO / GRN documents (skip to auto-fetch from Odoo instead)"):
        st.caption(
            "If you already have the Purchase Order and GRN as separate files, upload them here \u2014 the "
            "app reads them directly instead of looking the PO/GRN number up in Odoo. Leave blank to use "
            "the Odoo auto-fetch (default)."
        )
        po_doc = st.file_uploader("Purchase Order document", type=["pdf", "png", "jpg", "jpeg"], key="po_doc_uploader")
        grn_doc = st.file_uploader("GRN document", type=["pdf", "png", "jpg", "jpeg"], key="grn_doc_uploader")

    with st.form("review_form"):
        c1, c2 = st.columns(2)
        with c1:
            invoice_number = st.text_input("Invoice Number *", value=fields.get("invoice_number") or "")
            vendor_name = st.text_input("Vendor *", value=fields.get("vendor_name") or "")
            po_number = st.text_input("PO Number *", value=fields.get("po_number") or "")
            grn_number = st.text_input("GRN Number", value=fields.get("grn_number") or "")
            currency = st.selectbox("Currency", ["INR", "USD", "EUR", "GBP"],
                                     index=["INR", "USD", "EUR", "GBP"].index(fields.get("currency") or "INR")
                                     if fields.get("currency") in ["INR", "USD", "EUR", "GBP"] else 0)
        with c2:
            inv_date = fields.get("invoice_date")
            invoice_date = st.date_input("Invoice Date", value=inv_date if inv_date else datetime.today())
            quantity = st.number_input("Quantity", value=float(fields.get("quantity") or 1), min_value=0.0)
            unit_price = st.number_input("Unit Price", value=float(fields.get("unit_price") or 0), min_value=0.0)
            gst = st.number_input("GST / Tax Amount", value=float(fields.get("gst") or 0), min_value=0.0)
            grand_total = st.number_input("Invoice Total (Grand Total) *",
                                           value=float(fields.get("grand_total") or fields.get("unit_price") or 0),
                                           min_value=0.0)

        submitted = st.form_submit_button("✅ Save & Run 3-Way Match", type="primary", use_container_width=True)

    if submitted:
        if not invoice_number or not po_number:
            st.error("Invoice Number and PO Number are required.")
        else:
            session = get_session()
            try:
                inv = Invoice(
                    invoice_number=invoice_number,
                    vendor_name=vendor_name,
                    po_number=po_number,
                    grn_number=grn_number or None,
                    invoice_date=datetime.combine(invoice_date, datetime.min.time()),
                    currency=currency,
                    unit_price=unit_price,
                    quantity=quantity,
                    tax_amount=gst,
                    grand_total=grand_total,
                    file_name=st.session_state.get("ocr_filename"),
                    ocr_confidence=conf,
                    ocr_raw_text=fields.get("ocr_raw_text"),
                    status=InvoiceStatus.UPLOADED,
                    uploaded_by=user["id"],
                )
                session.add(inv)
                session.commit()
                invoice_id = inv.id
            finally:
                session.close()

            # Save the actual uploaded file to disk (previously only the
            # filename was stored in the DB -- the file itself was dropped).
            file_bytes = st.session_state.get("ocr_file_bytes")
            if file_bytes:
                import re as _re
                safe_name = _re.sub(r"[^A-Za-z0-9_.\-]", "_", st.session_state.get("ocr_filename") or "invoice")
                dest_path = config.UPLOAD_DIR / f"{invoice_id}_{safe_name}"
                dest_path.write_bytes(file_bytes)
                session = get_session()
                try:
                    saved_inv = session.query(Invoice).filter_by(id=invoice_id).first()
                    saved_inv.file_path = str(dest_path)
                    session.commit()
                finally:
                    session.close()

            log_action(invoice_id, user["id"], "UPLOADED", f"Invoice {invoice_number} uploaded via "
                       f"{fields.get('ocr_engine', 'manual')} (confidence {conf}%).")

            po_override = None
            if po_doc is not None:
                po_fields = extract_invoice_fields(po_doc.getvalue(), po_doc.name)
                po_override = {
                    "po_number": po_fields.get("po_number") or po_number,
                    "vendor_name": po_fields.get("vendor_name") or vendor_name,
                    "quantity": po_fields.get("quantity") or quantity,
                    "unit_price": po_fields.get("unit_price") or 0.0,
                    "tax_amount": po_fields.get("gst") or 0.0,
                    "total_price": po_fields.get("grand_total") or po_fields.get("unit_price") or 0.0,
                    "currency": po_fields.get("currency") or currency,
                    "order_date": po_fields.get("invoice_date"),
                    "status": "Confirmed",
                }
                log_action(invoice_id, user["id"], "PO_UPLOADED", f"PO document {po_doc.name} attached directly.")

            grn_override = None
            if grn_doc is not None:
                grn_fields = extract_invoice_fields(grn_doc.getvalue(), grn_doc.name)
                grn_override = {
                    "grn_number": grn_fields.get("grn_number") or grn_number or f"GRN-{invoice_number}",
                    "po_number": (po_override or {}).get("po_number", po_number),
                    "vendor_name": grn_fields.get("vendor_name") or vendor_name,
                    "quantity_received": grn_fields.get("quantity") or quantity,
                    "unit_price": grn_fields.get("unit_price") or 0.0,
                    "total_price": grn_fields.get("grand_total") or grn_fields.get("unit_price") or 0.0,
                    "currency": grn_fields.get("currency") or currency,
                    "delivery_date": grn_fields.get("invoice_date"),
                    "status": "Received",
                }
                log_action(invoice_id, user["id"], "GRN_UPLOADED", f"GRN document {grn_doc.name} attached directly.")

            st.session_state["ocr_fields"] = None
            st.session_state["selected_invoice_id"] = invoice_id
            st.session_state["run_match_on_load"] = True
            st.session_state["po_override"] = po_override
            st.session_state["grn_override"] = grn_override
            st.success(f"Invoice {invoice_number} saved. Running 3-way match...")
            time.sleep(0.4)
            st.switch_page("pages/4_3Way_Matching.py")
else:
    st.info("Upload a file or paste invoice text above, then run extraction to continue.")

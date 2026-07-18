"""Invoice Queue: quick worklist of everything in the pipeline."""
import pandas as pd
import streamlit as st

from modules import auth
from modules.database import get_session
from modules.models import Invoice
from modules.utils.components import page_header, status_badge_html, empty_state
from modules.utils.styling import inject_css

auth.require_login()
inject_css()

page_header("Invoice Queue", "Everything currently uploaded, matching, or awaiting export.")

session = get_session()
try:
    rows = session.query(Invoice).order_by(Invoice.created_at.desc()).all()
    data = [{
        "id": r.id,
        "Invoice No": r.invoice_number,
        "Vendor": r.vendor_name,
        "PO No": r.po_number,
        "Total": r.grand_total,
        "Confidence": r.ocr_confidence,
        "Status": r.status.value if hasattr(r.status, "value") else r.status,
        "Uploaded": r.created_at.strftime("%d %b %Y %H:%M") if r.created_at else "",
    } for r in rows]
finally:
    session.close()

if not data:
    empty_state("\U0001F4ED", "Queue is empty", "Upload an invoice to get started.")
    st.stop()

status_filter = st.multiselect("Filter by status", sorted(set(d["Status"] for d in data)))
filtered = [d for d in data if not status_filter or d["Status"] in status_filter]

with st.container(border=True):
    header_cols = st.columns([1.3, 1.3, 1, 1, 1, 1.2, 1])
    for col, label in zip(header_cols, ["Invoice No", "Vendor", "PO No", "Total", "Confidence", "Status", ""]):
        col.markdown(f"<span class='emp-caption'>{label}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:6px 0 10px 0;'>", unsafe_allow_html=True)

    for d in filtered:
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.3, 1.3, 1, 1, 1, 1.2, 1])
        c1.markdown(f"**{d['Invoice No']}**")
        c2.write(d["Vendor"] or "—")
        c3.write(d["PO No"] or "—")
        c4.write(f"{d['Total']:,.2f}" if d["Total"] is not None else "—")
        c5.write(f"{d['Confidence']}%" if d["Confidence"] else "—")
        c6.markdown(status_badge_html(d["Status"]), unsafe_allow_html=True)
        if c7.button("Open →", key=f"open_{d['id']}"):
            st.session_state["selected_invoice_id"] = d["id"]
            st.switch_page("pages/4_3Way_Matching.py")

"""Review Center: filterable/searchable/paginated table, bulk actions,
per-invoice detail + audit trail."""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from modules import auth
from modules.database import get_session
from modules.models import Invoice, InvoiceStatus, Export
from modules.matching.engine import run_match
from modules.utils.components import page_header, status_badge_html, empty_state
from modules.utils.audit import get_audit_trail
from modules.utils.styling import inject_css

auth.require_login()
inject_css()
user = auth.current_user()

page_header("Review Center", "Search, filter, and act on invoices across the pipeline.")

# ---- Filters -----------------------------------------------------------
with st.expander("\U0001F50D Filters & Search", expanded=True):
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        search = st.text_input("Search (Invoice No / Vendor / PO No)")
    with f2:
        status_filter = st.multiselect("Approval Status", [s.value for s in InvoiceStatus])
    with f3:
        date_range = st.date_input("Date range", value=())
    with f4:
        vendor_filter = st.text_input("Vendor")

session = get_session()
try:
    rows = session.query(Invoice).order_by(Invoice.created_at.desc()).all()
    df = pd.DataFrame([{
        "id": r.id,
        "Invoice No": r.invoice_number,
        "Vendor": r.vendor_name,
        "PO No": r.po_number,
        "GRN No": r.grn_number,
        "Total": r.grand_total,
        "Status": r.status.value if hasattr(r.status, "value") else r.status,
        "Confidence": r.ocr_confidence,
        "Uploaded": r.created_at,
        "Correction Reason": r.correction_reason,
    } for r in rows])
finally:
    session.close()

if df.empty:
    empty_state("\U0001F4ED", "Nothing to review yet")
    st.stop()

filtered = df.copy()
if search:
    s = search.lower()
    filtered = filtered[
        filtered["Invoice No"].str.lower().str.contains(s, na=False) |
        filtered["Vendor"].str.lower().str.contains(s, na=False) |
        filtered["PO No"].str.lower().str.contains(s, na=False)
    ]
if status_filter:
    filtered = filtered[filtered["Status"].isin(status_filter)]
if vendor_filter:
    filtered = filtered[filtered["Vendor"].str.lower().str.contains(vendor_filter.lower(), na=False)]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[
        (filtered["Uploaded"].dt.date >= start) & (filtered["Uploaded"].dt.date <= end)
    ]

st.caption(f"{len(filtered)} of {len(df)} invoices match your filters.")

# ---- Pagination ----------------------------------------------------------
page_size = st.selectbox("Rows per page", [10, 25, 50], index=0)
total_pages = max(1, -(-len(filtered) // page_size))
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
page_df = filtered.iloc[(page - 1) * page_size: page * page_size]

display_df = page_df.drop(columns=["id", "Correction Reason"]).copy()
display_df["Uploaded"] = display_df["Uploaded"].dt.strftime("%d %b %Y %H:%M")

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    key="review_table",
)

selected_idx = event.selection.rows if hasattr(event, "selection") else []
selected_ids = page_df.iloc[selected_idx]["id"].tolist() if selected_idx else []

# ---- Bulk actions ----------------------------------------------------------
b1, b2, b3 = st.columns(3)
with b1:
    if st.button(f"\U0001F504 Re-run Match ({len(selected_ids)} selected)", disabled=not selected_ids, use_container_width=True):
        for inv_id in selected_ids:
            run_match(inv_id, user_id=user["id"])
        st.success(f"Re-ran matching for {len(selected_ids)} invoice(s).")
        st.rerun()
with b2:
    csv_bytes = page_df.drop(columns=["id"]).to_csv(index=False).encode("utf-8")
    st.download_button("\U0001F4E5 Export view as CSV", data=csv_bytes, file_name="review_center_export.csv",
                        mime="text/csv", use_container_width=True)
with b3:
    if st.button("\U0001F441 View Details / Audit Log", disabled=len(selected_ids) != 1, use_container_width=True):
        st.session_state["review_detail_id"] = selected_ids[0]

# ---- Detail / audit trail ---------------------------------------------------
detail_id = st.session_state.get("review_detail_id")
if detail_id:
    session = get_session()
    try:
        inv = session.query(Invoice).filter_by(id=detail_id).first()
    finally:
        session.close()

    if inv:
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"#### {inv.invoice_number} — {inv.vendor_name}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PO No", inv.po_number or "—")
            c2.metric("GRN No", inv.grn_number or "—")
            c3.metric("Total", f"{inv.grand_total:,.2f}" if inv.grand_total else "—")
            c4.markdown(status_badge_html(inv.status.value if hasattr(inv.status, "value") else inv.status),
                         unsafe_allow_html=True)
            if inv.correction_reason:
                st.info(f"**Correction reason:** {inv.correction_reason}")

            st.markdown("##### Audit Trail")
            trail = get_audit_trail(detail_id)
            if trail:
                for t in trail:
                    st.markdown(f"- `{t['created_at'].strftime('%d %b %Y %H:%M')}` **{t['action']}** — {t['details'] or ''}")
            else:
                st.caption("No audit entries yet.")

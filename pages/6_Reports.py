"""Reports: filterable export screen (Excel / CSV / PDF) per the spec."""
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from modules import auth
from modules.reports.excel_export import query_invoices, to_excel_bytes, to_csv_bytes, generate_report_filename
from modules.reports.pdf_export import build_pdf_report
from modules.utils.components import page_header, empty_state
from modules.utils.styling import inject_css

auth.require_login()
inject_css()

page_header("Reports", "Filter processed invoices and export a report.")

with st.expander("\U0001F50D Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        date_from = st.date_input("From", value=datetime.now() - timedelta(days=30))
        invoice_number = st.text_input("Invoice No contains")
    with c2:
        date_to = st.date_input("To", value=datetime.now())
        po_number = st.text_input("PO No contains")
    with c3:
        min_price = st.number_input("Min price", value=0.0, min_value=0.0)
        vendor = st.text_input("Vendor contains")
    with c4:
        max_price = st.number_input("Max price", value=0.0, min_value=0.0, help="0 = no upper limit")
        status = st.selectbox("Status", ["", "Uploaded", "Matched", "Exported", "Mismatch", "Pending Review", "Rejected"])

df = query_invoices(
    date_from=date_from, date_to=date_to,
    invoice_number=invoice_number or None, po_number=po_number or None,
    min_price=min_price or None, max_price=max_price or None,
    status=status or None, vendor=vendor or None,
)

st.caption(f"{len(df)} invoice(s) match your filters.")

if df.empty:
    empty_state("\U0001F4C4", "No invoices match these filters")
    st.stop()

with st.container(border=True):
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.markdown("#### Matches by Status")
        counts = df["Status"].value_counts().reset_index()
        counts.columns = ["Status", "Count"]
        fig = px.bar(counts, x="Status", y="Count", color="Status",
                     color_discrete_map={"Matched": "#10B981", "Exported": "#2563EB", "Mismatch": "#EF4444",
                                          "Pending Review": "#F59E0B", "Uploaded": "#9CA3AF"})
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=260,
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
with right:
    with st.container(border=True):
        st.markdown("#### Grand Total by Vendor")
        by_vendor = df.groupby("Vendor")["Grand Total"].sum().reset_index().sort_values("Grand Total", ascending=False)
        fig2 = px.bar(by_vendor.head(10), x="Vendor", y="Grand Total", color_discrete_sequence=["#2563EB"])
        fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
st.markdown("#### Export")
e1, e2, e3 = st.columns(3)
with e1:
    st.download_button("\U0001F4D7 Download Excel", data=to_excel_bytes(df),
                        file_name=generate_report_filename("xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True, type="primary")
with e2:
    st.download_button("\U0001F4C4 Download CSV", data=to_csv_bytes(df),
                        file_name=generate_report_filename("csv"), mime="text/csv", use_container_width=True)
with e3:
    kpis = {
        "Total Invoices": len(df),
        "Matched": int((df["Status"].isin(["Matched", "Exported"])).sum()),
        "Pending Review": int((df["Status"] == "Pending Review").sum()),
        "Total Value": f"{df['Grand Total'].sum():,.0f}",
    }
    pdf_bytes = build_pdf_report(kpis, df)
    st.download_button("\U0001F5C2 Download PDF Report", data=pdf_bytes,
                        file_name=generate_report_filename("pdf"), mime="application/pdf",
                        use_container_width=True)

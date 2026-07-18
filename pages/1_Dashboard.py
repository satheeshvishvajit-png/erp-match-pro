"""Landing dashboard: KPIs, recent activity, charts, quick actions."""
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import func

from modules import auth
from modules.database import get_session
from modules.models import Invoice, InvoiceStatus, AuditLog, User
from modules.utils.components import kpi_card, page_header, status_badge_html, timeline, empty_state
from modules.utils.styling import inject_css

auth.require_login()
inject_css()

user = auth.current_user()
page_header(f"Welcome back, {user['full_name'].split()[0]} \U0001F44B", "Here's what's happening with your invoices today.")

session = get_session()
try:
    total = session.query(Invoice).count()
    matched = session.query(Invoice).filter(Invoice.status.in_([InvoiceStatus.MATCHED, InvoiceStatus.EXPORTED])).count()
    exported = session.query(Invoice).filter(Invoice.status == InvoiceStatus.EXPORTED).count()
    pending = session.query(Invoice).filter(Invoice.status == InvoiceStatus.PENDING_REVIEW).count()
    mismatch = session.query(Invoice).filter(Invoice.status == InvoiceStatus.MISMATCH).count()
    today_uploads = session.query(Invoice).filter(func.date(Invoice.created_at) == datetime.utcnow().date()).count()
    success_rate = round((matched / total) * 100, 1) if total else 0.0

    rows = session.query(Invoice).order_by(Invoice.created_at.desc()).limit(400).all()
    df = pd.DataFrame([{
        "date": r.created_at.date() if r.created_at else None,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "vendor": r.vendor_name,
        "total": r.grand_total,
    } for r in rows])

    audit_rows = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(8).all()
    user_map = {u.id: u.full_name for u in session.query(User).all()}
finally:
    session.close()

# ---- KPI row ---------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi_card("Invoices Processed", total, icon="\U0001F4C4")
with c2:
    kpi_card("Matched", matched, delta=f"{success_rate}%", delta_up=True, icon="✅")
with c3:
    kpi_card("Pending Review", pending, delta=None, icon="⏳")
with c4:
    kpi_card("Mismatches", mismatch, delta=None, delta_up=False, icon="⚠️")
with c5:
    kpi_card("Today's Uploads", today_uploads, icon="\U0001F4E4")

st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

# ---- Charts row --------------------------------------------------------
left, right = st.columns([1.4, 1])

with left:
    with st.container(border=True):
        st.markdown("#### Invoice Trend (last 14 days)")
        if not df.empty:
            trend = df.dropna(subset=["date"]).groupby("date").size().reset_index(name="count")
            # backfill last 14 days so the chart always has a sensible x-axis
            date_range = pd.date_range(end=datetime.utcnow().date(), periods=14).date
            trend = trend.set_index("date").reindex(date_range, fill_value=0).rename_axis("date").reset_index()
            fig = px.area(trend, x="date", y="count", markers=True)
            fig.update_traces(line_color="#2563EB", fillcolor="rgba(37,99,235,0.12)")
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=280,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis_title=None, yaxis_title=None,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            empty_state("\U0001F4C8", "No data yet", "Upload your first invoice to see trends.")

with right:
    with st.container(border=True):
        st.markdown("#### Status Breakdown")
        if not df.empty:
            counts = df["status"].value_counts().reset_index()
            counts.columns = ["status", "count"]
            color_map = {"Matched": "#10B981", "Exported": "#2563EB", "Mismatch": "#EF4444",
                         "Pending Review": "#F59E0B", "Uploaded": "#9CA3AF", "Rejected": "#991B1B"}
            fig = go.Figure(data=[go.Pie(
                labels=counts["status"], values=counts["count"], hole=0.62,
                marker=dict(colors=[color_map.get(s, "#9CA3AF") for s in counts["status"]]),
                textinfo="label+percent",
            )])
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, showlegend=False,
                               paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            empty_state("\U0001F4CA", "No data yet")

st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

# ---- Recent activity + quick actions ---------------------------------------
left2, right2 = st.columns([1.4, 1])

with left2:
    with st.container(border=True):
        st.markdown("#### Recent Activity")
        if audit_rows:
            items = [{
                "title": r.action.replace("_", " ").title(),
                "subtitle": (r.details or "")[:110] + (" (" + user_map.get(r.user_id, "System") + ")" if r.user_id else ""),
                "time": r.created_at.strftime("%d %b %Y, %H:%M"),
            } for r in audit_rows]
            timeline(items)
        else:
            empty_state("\U0001F553", "No recent activity")

with right2:
    with st.container(border=True):
        st.markdown("#### Quick Actions")
        if st.button("\U0001F4E4  Upload Invoice", use_container_width=True, type="primary"):
            st.switch_page("pages/2_Upload_Invoice.py")
        if st.button("\U0001F50D  Review Center", use_container_width=True):
            st.switch_page("pages/5_Review_Center.py")
        if st.button("\U0001F4CA  Generate Report", use_container_width=True):
            st.switch_page("pages/6_Reports.py")
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="emp-caption" style="margin-top:8px;">Monthly success rate</div>
        <div style="font-size:28px; font-weight:800; color:#10B981;">{success_rate}%</div>
        """, unsafe_allow_html=True)
        st.progress(min(success_rate / 100, 1.0))

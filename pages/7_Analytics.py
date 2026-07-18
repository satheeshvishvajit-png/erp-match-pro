"""Analytics: vendor performance, monthly trend, mismatch reasons,
processing time, heatmap."""
import pandas as pd
import plotly.express as px
import streamlit as st

from modules import auth
from modules.database import get_session
from modules.models import Invoice, InvoiceStatus
from modules.utils.components import page_header, empty_state
from modules.utils.styling import inject_css

auth.require_login()
inject_css()

page_header("Analytics", "Deeper trends across vendors, time, and match quality.")

session = get_session()
try:
    rows = session.query(Invoice).all()
    df = pd.DataFrame([{
        "vendor": r.vendor_name,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "created_at": r.created_at,
        "exported_at": r.exported_at,
        "grand_total": r.grand_total,
        "correction_reason": r.correction_reason,
    } for r in rows])
finally:
    session.close()

if df.empty:
    empty_state("\U0001F4C8", "No data yet")
    st.stop()

df["month"] = df["created_at"].dt.strftime("%b %Y")
df["dow"] = df["created_at"].dt.day_name()
df["hour"] = df["created_at"].dt.hour
df["is_matched"] = df["status"].isin(["Matched", "Exported"])
df["processing_hours"] = (df["exported_at"] - df["created_at"]).dt.total_seconds() / 3600

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown("#### Vendor Performance (match rate)")
        perf = df.groupby("vendor").agg(total=("status", "count"), matched=("is_matched", "sum")).reset_index()
        perf["match_rate"] = (perf["matched"] / perf["total"] * 100).round(1)
        fig = px.bar(perf.sort_values("match_rate"), x="match_rate", y="vendor", orientation="h",
                     color="match_rate", color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"], range_color=[0, 100])
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, coloraxis_showscale=False,
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Match rate (%)", yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with c2:
    with st.container(border=True):
        st.markdown("#### Monthly Matches")
        monthly = df.groupby("month").agg(total=("status", "count"), matched=("is_matched", "sum")).reset_index()
        fig2 = px.line(monthly, x="month", y=["total", "matched"], markers=True,
                        color_discrete_sequence=["#9CA3AF", "#2563EB"])
        fig2.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, legend_title=None,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

c3, c4 = st.columns(2)
with c3:
    with st.container(border=True):
        st.markdown("#### Mismatch Reasons")
        reasons = df["correction_reason"].dropna()
        if not reasons.empty:
            reason_counts = reasons.value_counts().reset_index()
            reason_counts.columns = ["reason", "count"]
            fig3 = px.pie(reason_counts, names="reason", values="count", hole=0.5)
            fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        else:
            empty_state("\U0001F44D", "No mismatches recorded")

with c4:
    with st.container(border=True):
        st.markdown("#### Processing Time (upload → export)")
        proc = df.dropna(subset=["processing_hours"])
        if not proc.empty:
            fig4 = px.histogram(proc, x="processing_hours", nbins=10, color_discrete_sequence=["#2563EB"])
            fig4.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280,
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                xaxis_title="Hours", yaxis_title="Invoices")
            st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})
        else:
            empty_state("⏱️", "No exported invoices yet")

with st.container(border=True):
    st.markdown("#### Upload Activity Heatmap (day of week × hour)")
    heat = df.groupby(["dow", "hour"]).size().reset_index(name="count")
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = heat.pivot(index="dow", columns="hour", values="count").reindex(dow_order).fillna(0)
    fig5 = px.imshow(pivot, color_continuous_scale=["#F5F7FA", "#2563EB"], aspect="auto")
    fig5.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=260, paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})

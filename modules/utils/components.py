"""Small reusable Streamlit render helpers shared across pages."""
import streamlit as st

STATUS_BADGE_MAP = {
    "Matched": ("badge-green", "✓"),
    "Exported": ("badge-blue", "↗"),
    "Uploaded": ("badge-gray", "•"),
    "Mismatch": ("badge-red", "✕"),
    "Pending Review": ("badge-yellow", "⏳"),
    "Rejected": ("badge-red", "✕"),
    "green": ("badge-green", "✓"),
    "yellow": ("badge-yellow", "!"),
    "red": ("badge-red", "✕"),
}


def status_badge_html(status: str) -> str:
    cls, icon = STATUS_BADGE_MAP.get(status, ("badge-gray", "•"))
    return f'<span class="badge {cls}"><span class="badge-dot"></span>{status}</span>'


def kpi_card(label: str, value, delta: str = None, delta_up: bool = True, icon: str = ""):
    delta_html = ""
    if delta:
        arrow = "↑" if delta_up else "↓"
        cls = "up" if delta_up else "down"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {delta}</div>'
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{icon} {label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.markdown(f"""
    <div style="margin-bottom: 28px;">
        <h1 style="margin-bottom: 4px;">{title}</h1>
        <div class="emp-caption">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def empty_state(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="empty-state">
        <div style="font-size: 42px; margin-bottom: 10px;">{icon}</div>
        <div style="font-size: 16px; font-weight: 700;">{title}</div>
        <div class="emp-caption">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def match_comparison_table(field_results: dict):
    """Renders the PO / GRN / Invoice / Result comparison table with
    green/yellow/red indicators, per the spec's Matching Engine section."""
    st.markdown("""
    <div class="match-row header">
        <div>Field</div><div>PO</div><div>GRN</div><div>Invoice</div><div>Result</div>
    </div>
    """, unsafe_allow_html=True)

    labels = {"vendor": "Vendor", "quantity": "Quantity", "price": "Price"}
    for key, label in labels.items():
        row = field_results.get(key, {})
        st.markdown(f"""
        <div class="match-row">
            <div class="match-cell field-name">{label}</div>
            <div class="match-cell">{row.get('po', '-')}</div>
            <div class="match-cell">{row.get('grn', '-')}</div>
            <div class="match-cell">{row.get('invoice', '-')}</div>
            <div class="match-cell">{status_badge_html(row.get('status', 'yellow'))}</div>
        </div>
        """, unsafe_allow_html=True)


def timeline(items):
    """items: list of dicts with 'title', 'subtitle', 'time'."""
    html = ""
    for item in items:
        html += f"""
        <div class="timeline-item">
            <div>
                <div style="font-weight:600; font-size:14px;">{item.get('title','')}</div>
                <div class="emp-caption">{item.get('subtitle','')}</div>
                <div class="emp-caption" style="font-size:11px; margin-top:2px;">{item.get('time','')}</div>
            </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


def success_celebration(message: str):
    st.markdown(f"""
    <div class="emp-card celebrate" style="border-color:#10B981; background:#F0FDF9; text-align:center; padding: 32px;">
        <div style="font-size:44px;">\U0001F389</div>
        <div style="font-size:20px; font-weight:800; color:#065F46; margin-top:8px;">EXPORTED TO ERP</div>
        <div class="emp-caption" style="margin-top:6px;">{message}</div>
    </div>
    """, unsafe_allow_html=True)
    st.balloons()


def validation_checklist(checks):
    """Renders a stack of green-check / red-cross validation rows, one per
    field -- e.g. "PO No matched and validated" -- matching the reference
    implementation's per-field validation list (PO No, Description, HSN
    Code, Rate, Quantity all checked individually rather than a single
    pass/fail)."""
    html = ""
    for label, passed in checks:
        icon = "✅" if passed else "❌"
        bg = "#ECFDF5" if passed else "#FEF2F2"
        color = "#065F46" if passed else "#991B1B"
        html += f"""
        <div style="background:{bg}; color:{color}; border-radius:10px; padding:12px 16px;
                     margin-bottom:8px; font-weight:600; font-size:14px;">
            {icon} &nbsp;{label}
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)

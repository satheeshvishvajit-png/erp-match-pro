"""
Injects the enterprise design system as custom CSS on top of Streamlit's
default chrome. Keeping all of this in one place means every page gets a
consistent Fiori/Dynamics/Stripe-dashboard feel for free.
"""
import streamlit as st

import config


def _palette():
    dark = st.session_state.get("dark_mode", False)
    return config.DARK_COLORS if dark else config.COLORS


def inject_css():
    c = _palette()
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}

    /* ---- App shell ---------------------------------------------------- */
    .stApp {{
        background: {c['background']};
    }}
    [data-testid="stHeader"] {{
        background: transparent;
    }}
    .block-container {{
        padding-top: 1.6rem;
        padding-bottom: 3rem;
        max-width: 1360px;
    }}

    /* ---- Sidebar -------------------------------------------------------*/
    [data-testid="stSidebar"] {{
        background: {c['surface']};
        border-right: 1px solid {c['border']};
    }}
    [data-testid="stSidebar"] .block-container {{
        padding-top: 1.2rem;
    }}

    /* ---- Typography ------------------------------------------------- */
    h1, h2, h3, h4 {{
        color: {c['text']};
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }}
    p, span, label, div {{
        color: {c['text']};
    }}
    .emp-caption {{
        color: {c['text_secondary']};
        font-size: 0.85rem;
        font-weight: 500;
    }}

    /* ---- Buttons ------------------------------------------------------ */
    div.stButton > button, .stDownloadButton > button {{
        border-radius: 10px;
        border: 1px solid {c['border']};
        font-weight: 600;
        padding: 0.5rem 1.1rem;
        transition: all 0.15s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}
    div.stButton > button:hover, .stDownloadButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18);
        border-color: {c['primary']};
        color: {c['primary']};
    }}
    div.stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {c['primary']} 0%, {c['primary_dark']} 100%);
        color: white;
        border: none;
    }}
    div.stButton > button[kind="primary"]:hover {{
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
        color: white;
    }}

    /* ---- Cards ---------------------------------------------------------*/
    /* Streamlit's own st.container(border=True) -- the real, working way to
       wrap native widgets (charts, buttons, forms) in a card. Styling this
       instead of a hand-rolled <div class="emp-card"> across separate
       st.markdown() calls, since separate calls each render into their own
       isolated DOM fragment and can't actually wrap sibling elements. */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: {c['surface']} !important;
        border-radius: 16px !important;
        border: 1px solid {c['border']} !important;
        box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04), 0 1px 2px rgba(16, 24, 40, 0.03) !important;
        animation: empFadeIn 0.35s ease both;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] > div {{
        padding: 6px 4px;
    }}

    .emp-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04), 0 1px 2px rgba(16, 24, 40, 0.03);
        animation: empFadeIn 0.35s ease both;
    }}
    .emp-card-glass {{
        background: rgba(255,255,255,0.6);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255,255,255,0.4);
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: 0 8px 32px rgba(16, 24, 40, 0.08);
    }}

    /* ---- KPI stat cards -------------------------------------------------*/
    .kpi-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(16,24,40,0.05);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
        animation: empFadeIn 0.4s ease both;
        height: 100%;
    }}
    .kpi-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 24px rgba(16,24,40,0.10);
    }}
    .kpi-label {{
        font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
        text-transform: uppercase; color: {c['text_secondary']}; margin-bottom: 10px;
    }}
    .kpi-value {{ font-size: 32px; font-weight: 800; color: {c['text']}; line-height: 1.1; }}
    .kpi-delta {{ font-size: 13px; font-weight: 600; margin-top: 8px; }}
    .kpi-delta.up {{ color: {c['success']}; }}
    .kpi-delta.down {{ color: {c['danger']}; }}

    /* ---- Status badges ---------------------------------------------------*/
    .badge {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 700;
        letter-spacing: 0.01em;
    }}
    .badge-dot {{ width: 7px; height: 7px; border-radius: 50%; }}
    .badge-green {{ background: {c['success_light']}; color: #065F46; }}
    .badge-green .badge-dot {{ background: {c['success']}; }}
    .badge-yellow {{ background: {c['warning_light']}; color: #92400E; }}
    .badge-yellow .badge-dot {{ background: {c['warning']}; }}
    .badge-red {{ background: {c['danger_light']}; color: #991B1B; }}
    .badge-red .badge-dot {{ background: {c['danger']}; }}
    .badge-blue {{ background: {c['primary_light']}; color: #1E3A8A; }}
    .badge-blue .badge-dot {{ background: {c['primary']}; }}
    .badge-gray {{ background: #F3F4F6; color: #374151; }}
    .badge-gray .badge-dot {{ background: #9CA3AF; }}

    /* ---- Matching comparison table ---------------------------------------*/
    .match-row {{
        display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr 0.8fr;
        align-items: center; padding: 14px 16px; border-radius: 12px;
        background: {c['surface']}; border: 1px solid {c['border']}; margin-bottom: 8px;
        animation: empSlideIn 0.3s ease both;
    }}
    .match-row.header {{ background: transparent; border: none; font-size: 11px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.05em; color: {c['text_secondary']}; padding-bottom: 4px; }}
    .match-cell {{ font-size: 14px; font-weight: 500; color: {c['text']}; }}
    .match-cell.field-name {{ font-weight: 700; }}

    /* ---- Timeline ------------------------------------------------------*/
    .timeline-item {{
        display: flex; gap: 14px; padding: 10px 0; border-left: 2px solid {c['border']};
        margin-left: 9px; padding-left: 20px; position: relative;
    }}
    .timeline-item::before {{
        content: ''; position: absolute; left: -7px; top: 14px; width: 12px; height: 12px;
        border-radius: 50%; background: {c['primary']}; border: 2px solid {c['surface']};
    }}

    /* ---- Empty states ----------------------------------------------------*/
    .empty-state {{
        text-align: center; padding: 60px 20px; color: {c['text_secondary']};
    }}

    /* ---- Animations -----------------------------------------------------*/
    @keyframes empFadeIn {{ from {{ opacity: 0; transform: translateY(6px);}} to {{ opacity: 1; transform: translateY(0);}} }}
    @keyframes empSlideIn {{ from {{ opacity: 0; transform: translateX(-8px);}} to {{ opacity: 1; transform: translateX(0);}} }}
    @keyframes empPulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0.4);}} 70% {{ box-shadow: 0 0 0 14px rgba(16,185,129,0);}} 100% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0);}} }}
    .celebrate {{ animation: empPulse 1.4s ease-out 2; }}

    /* ---- Misc widget polish ----------------------------------------------*/
    [data-testid="stFileUploaderDropzone"] {{
        border-radius: 14px !important;
        border: 2px dashed {c['border']} !important;
        background: {c['surface']} !important;
    }}
    [data-testid="stMetric"] {{
        background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 14px; padding: 14px 18px;
    }}
    hr {{ border-color: {c['border']}; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

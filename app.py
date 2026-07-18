"""
ERP Match Pro - entry point.

Handles login (Streamlit has no built-in auth) and, once authenticated,
builds the sidebar navigation via st.navigation so we control page
grouping/icons/branding exactly as specified rather than relying on the
default pages/ auto-sidebar.
"""
import streamlit as st

import config
from modules.database import init_db
from modules import auth, seed
from modules.utils.styling import inject_css

st.set_page_config(
    page_title=f"{config.APP_NAME} | {config.APP_TAGLINE}",
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
inject_css()


seed.seed_all()


def render_login():
    left, mid, right = st.columns([1, 1.1, 1])
    with mid:
        st.markdown(f"""
        <div style="text-align:center; margin-top: 8vh; margin-bottom: 28px;">
            <div style="font-size:40px;">{config.APP_ICON}</div>
            <h1 style="margin-bottom:2px;">{config.APP_NAME}</h1>
            <div class="emp-caption">{config.APP_TAGLINE}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("#### Sign in")
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submit = st.button("Sign in", type="primary", use_container_width=True)

            if submit:
                if auth.login(email, password):
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

            with st.expander("Demo credentials"):
                st.code(
                    "admin@erpmatchpro.com   / admin123   (Admin)\n"
                    "ap@erpmatchpro.com      / ap12345    (Accounts Payable)\n"
                    "manager@erpmatchpro.com / mgr12345   (Manager)",
                    language="text",
                )
        st.markdown(
            '<div class="emp-caption" style="text-align:center; margin-top:18px;">'
            'Odoo mode: <b>%s</b> &nbsp;•&nbsp; OCR engine: <b>%s</b></div>' % (
                config.ODOO_MODE.upper(), config.OCR_ENGINE.upper()
            ),
            unsafe_allow_html=True,
        )


def render_app():
    user = auth.current_user()

    with st.sidebar:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; padding: 4px 4px 18px 4px;">
            <div style="font-size:26px;">{config.APP_ICON}</div>
            <div>
                <div style="font-weight:800; font-size:17px; line-height:1.1;">{config.APP_NAME}</div>
                <div class="emp-caption" style="font-size:11px;">{config.APP_TAGLINE}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    pages = [
        st.Page("pages/1_Dashboard.py", title="Dashboard", icon="🏠", default=True),
        st.Page("pages/2_Upload_Invoice.py", title="Upload Invoice", icon="📤"),
        st.Page("pages/3_Invoice_Queue.py", title="Invoice Queue", icon="📋"),
        st.Page("pages/4_3Way_Matching.py", title="3-Way Matching", icon="🔗"),
        st.Page("pages/5_Review_Center.py", title="Review Center", icon="🔍"),
        st.Page("pages/6_Reports.py", title="Reports", icon="📊"),
        st.Page("pages/7_Analytics.py", title="Analytics", icon="📈"),
        st.Page("pages/8_Settings.py", title="Settings", icon="⚙️"),
    ]
    pg = st.navigation(pages)

    with st.sidebar:
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        st.toggle("🌙 Dark mode", key="dark_mode", value=st.session_state.get("dark_mode", False))

        st.markdown("---")
        avatar_color = user.get("avatar_color", "#2563EB")
        initials = "".join([p[0] for p in user["full_name"].split()[:2]]).upper()
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:10px; padding: 6px 4px;">
            <div style="width:36px; height:36px; border-radius:50%; background:{avatar_color};
                        color:white; display:flex; align-items:center; justify-content:center;
                        font-weight:700; font-size:13px;">{initials}</div>
            <div>
                <div style="font-weight:700; font-size:13.5px;">{user['full_name']}</div>
                <div class="emp-caption" style="font-size:11px;">{user['role']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            auth.logout()
            st.rerun()

    pg.run()


if auth.is_authenticated():
    render_app()
else:
    render_login()

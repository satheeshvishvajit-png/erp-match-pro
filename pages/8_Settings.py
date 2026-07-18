"""Settings: profile, Odoo connection, appearance, and (Admin only) user
management."""
import streamlit as st

import config
from modules import auth
from modules.database import get_session
from modules.models import User, UserRole
from modules.odoo.factory import get_odoo_client
from modules.utils.components import page_header
from modules.utils.styling import inject_css

auth.require_login()
inject_css()
user = auth.current_user()

page_header("Settings", "Profile, integrations, and appearance.")

tab_profile, tab_odoo, tab_appearance, tab_users = st.tabs(
    ["\U0001F464 Profile", "\U0001F517 Odoo Connection", "\U0001F3A8 Appearance", "\U0001F465 Users (Admin)"]
)

with tab_profile:
    with st.container(border=True):
        st.markdown(f"**Name:** {user['full_name']}")
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**Role:** {user['role']}")

with tab_odoo:
    with st.container(border=True):
        st.markdown(f"**Current mode:** `{config.ODOO_MODE.upper()}`")
        if config.ODOO_MODE == "mock":
            st.info(
                "Running against seeded mock PO/GRN data — no live Odoo server is configured. "
                "To connect a real instance, set these environment variables and restart the app:\n\n"
                "`ODOO_MODE=live`, `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_API_KEY`."
            )
        else:
            st.markdown(f"**URL:** {config.ODOO_URL}  \n**Database:** {config.ODOO_DB}  \n**User:** {config.ODOO_USERNAME}")

        if st.button("\U0001F50C Test Connection"):
            client = get_odoo_client()
            result = client.test_connection()
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["message"])

with tab_appearance:
    with st.container(border=True):
        st.toggle("Dark mode", key="dark_mode", value=st.session_state.get("dark_mode", False))
        st.caption("Also available from the sidebar for quick access.")

with tab_users:
    if not auth.has_role(UserRole.ADMIN):
        st.warning("Only Admins can manage users.")
    else:
        session = get_session()
        try:
            users = session.query(User).order_by(User.created_at.asc()).all()
            rows = [{"Name": u.full_name, "Email": u.email, "Role": u.role.value,
                     "Active": u.is_active, "Last login": u.last_login_at} for u in users]
        finally:
            session.close()

        with st.container(border=True):
            st.dataframe(rows, use_container_width=True, hide_index=True)

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("##### Add user")
            with st.form("add_user_form"):
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("Full name")
                    new_email = st.text_input("Email")
                with c2:
                    new_role = st.selectbox("Role", [r.value for r in UserRole])
                    new_password = st.text_input("Temporary password", type="password")
                add_submit = st.form_submit_button("Add user", type="primary")
            if add_submit:
                if not (new_name and new_email and new_password):
                    st.error("All fields are required.")
                else:
                    try:
                        auth.create_user(new_name, new_email, new_password, UserRole(new_role))
                        st.success(f"User {new_email} created.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not create user: {exc}")

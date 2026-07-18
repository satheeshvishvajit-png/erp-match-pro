"""Returns the active Odoo client based on config.ODOO_MODE. Cached so we
don't reconnect on every Streamlit rerun."""
import streamlit as st

import config
from modules.odoo.mock_client import MockOdooClient


@st.cache_resource(show_spinner=False)
def get_odoo_client():
    if config.ODOO_MODE == "live":
        from modules.odoo.client import OdooClient
        return OdooClient(config.ODOO_URL, config.ODOO_DB, config.ODOO_USERNAME, config.ODOO_API_KEY)
    return MockOdooClient()

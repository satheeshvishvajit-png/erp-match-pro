"""
Central configuration for ERP Match Pro.

Everything that a deployer might want to change (DB location, Odoo mode,
color palette, app metadata) lives here so the rest of the codebase never
hardcodes these values.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# App metadata
# --------------------------------------------------------------------------
APP_NAME = "ERP Match Pro"
APP_TAGLINE = "3-Way Matching Portal"
APP_ICON = "\U0001F9FE"  # receipt emoji, used as browser tab icon

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# Defaults to a local SQLite file so the app runs with zero external
# dependencies. Point DATABASE_URL at Postgres in production, e.g.:
#   postgresql+psycopg2://user:pass@host:5432/erp_match_pro
DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'erp_match_pro.db'}"
)

# Where uploaded invoice/PO/GRN files are saved to disk. The DB only ever
# stores the path (Invoice.file_path), never the file bytes themselves.
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "data" / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Odoo integration
# --------------------------------------------------------------------------
# ODOO_MODE = "mock"  -> uses modules/odoo/mock_client.py, seeded with demo
#                        PO/GRN data. Safe default, no external server needed.
# ODOO_MODE = "live"  -> uses modules/odoo/client.py (XML-RPC) against a real
#                        Odoo instance. Requires the four ODOO_* vars below.
ODOO_MODE = os.environ.get("ODOO_MODE", "mock")
ODOO_URL = os.environ.get("ODOO_URL", "")
ODOO_DB = os.environ.get("ODOO_DB", "")
ODOO_USERNAME = os.environ.get("ODOO_USERNAME", "")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY", "")

# --------------------------------------------------------------------------
# OCR
# --------------------------------------------------------------------------
# "easyocr" uses the deep-learning EasyOCR engine (better accuracy, heavier
# install). "regex" skips OCR entirely and only runs the field parser on
# text you paste/type -- useful for quick demos on machines without EasyOCR
# installed. The app auto-falls-back to "regex" if EasyOCR import fails.
OCR_ENGINE = os.environ.get("OCR_ENGINE", "easyocr")
OCR_LANGUAGES = ["en"]

# Path to poppler's "bin" folder (needed by pdf2image to rasterize PDF pages
# before OCR). Normally poppler just needs to be on the system PATH, but
# Windows PATH edits are unreliable to pick up (require a full restart of
# whatever launched the terminal, not just a new terminal tab) -- so as a
# fallback, auto-detect a poppler bin folder under the user's Downloads/home
# directory if PATH lookup would otherwise fail. Set POPPLER_PATH explicitly
# to override.
def _find_poppler_bin():
    import shutil
    if shutil.which("pdftoppm"):
        return None  # already on PATH, nothing extra needed
    search_roots = [Path.home() / "Downloads", Path.home(), BASE_DIR]
    for root in search_roots:
        if not root.exists():
            continue
        try:
            for candidate in root.glob("**/poppler-*/Library/bin"):
                if (candidate / "pdftoppm.exe").exists():
                    return str(candidate)
        except (PermissionError, OSError):
            continue
    return None


POPPLER_PATH = os.environ.get("POPPLER_PATH") or _find_poppler_bin()

# --------------------------------------------------------------------------
# Matching engine
# --------------------------------------------------------------------------
# Per the ERP AUTOMATION - 3-WAY MATCHING spec: match decision is driven by
# Price agreement across PO / GRN / Invoice. A small tolerance absorbs
# rounding differences from OCR/currency formatting.
PRICE_MATCH_TOLERANCE = float(os.environ.get("PRICE_MATCH_TOLERANCE", "0.01"))

# --------------------------------------------------------------------------
# Design system (matches the enterprise UI spec)
# --------------------------------------------------------------------------
COLORS = {
    "background": "#F5F7FA",
    "surface": "#FFFFFF",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "primary_light": "#DBEAFE",
    "success": "#10B981",
    "success_light": "#D1FAE5",
    "warning": "#F59E0B",
    "warning_light": "#FEF3C7",
    "danger": "#EF4444",
    "danger_light": "#FEE2E2",
    "text": "#111827",
    "text_secondary": "#6B7280",
    "border": "#E5E7EB",
}

DARK_COLORS = {
    "background": "#0B0F19",
    "surface": "#151B2B",
    "primary": "#3B82F6",
    "primary_dark": "#2563EB",
    "primary_light": "#1E3A5F",
    "success": "#34D399",
    "success_light": "#0F3D2E",
    "warning": "#FBBF24",
    "warning_light": "#4A3208",
    "danger": "#F87171",
    "danger_light": "#4C1D1D",
    "text": "#F3F4F6",
    "text_secondary": "#9CA3AF",
    "border": "#293045",
}

ROLES = ["Admin", "Accounts Payable", "Manager"]

"""
Common interface both the mock and live Odoo clients implement, so the rest
of the app (matching engine, upload page) never has to know which one is
active. Swap by setting ODOO_MODE=live and the four ODOO_* env vars in
config.py / .env.
"""
from abc import ABC, abstractmethod


class OdooClientBase(ABC):
    @abstractmethod
    def fetch_purchase_order(self, po_number: str):
        """Return a dict with keys: po_number, vendor_name, quantity, unit_price,
        tax_amount, total_price, currency, order_date, status. None if not found."""

    @abstractmethod
    def fetch_grn(self, grn_number: str, po_number: str = None):
        """Return a dict with keys: grn_number, po_number, vendor_name,
        quantity_received, unit_price, total_price, currency, delivery_date,
        status. None if not found."""

    @abstractmethod
    def export_vendor_bill(self, invoice: dict) -> dict:
        """Push a matched invoice to Odoo as a Vendor Bill.
        Returns {"success": bool, "odoo_bill_id": int|None, "reference": str|None, "message": str}."""

    @abstractmethod
    def test_connection(self) -> dict:
        """Returns {"success": bool, "message": str} - used by the Settings page."""

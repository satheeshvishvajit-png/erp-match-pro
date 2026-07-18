"""
Mock Odoo client. Implements the exact same interface as the live XML-RPC
client (modules/odoo/client.py) so it's a drop-in stand-in while no live
Odoo instance is configured. Backed by modules/odoo/mock_data.py.
"""
import random
import time

from modules.odoo.base_client import OdooClientBase
from modules.odoo.mock_data import PURCHASE_ORDERS, GRNS


class MockOdooClient(OdooClientBase):
    def __init__(self):
        # Simulated "network" latency so the UI's loading states have
        # something real to show during a demo.
        self._latency = (0.3, 0.8)

    def _simulate_latency(self):
        time.sleep(random.uniform(*self._latency))

    def fetch_purchase_order(self, po_number: str):
        self._simulate_latency()
        po = PURCHASE_ORDERS.get((po_number or "").strip().upper())
        return dict(po) if po else None

    def fetch_grn(self, grn_number: str, po_number: str = None):
        self._simulate_latency()
        grn = GRNS.get((grn_number or "").strip().upper())
        if grn and po_number and grn["po_number"] != po_number:
            return None
        return dict(grn) if grn else None

    def export_vendor_bill(self, invoice: dict) -> dict:
        self._simulate_latency()
        fake_bill_id = random.randint(10000, 99999)
        return {
            "success": True,
            "odoo_bill_id": fake_bill_id,
            "reference": f"BILL/{fake_bill_id}",
            "message": f"Vendor bill BILL/{fake_bill_id} created in Odoo (mock) and linked to "
                       f"{invoice.get('po_number', 'N/A')}.",
        }

    def test_connection(self) -> dict:
        return {"success": True, "message": "Connected to mock Odoo data source (no live server configured)."}

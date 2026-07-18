"""
Live Odoo client using standard XML-RPC (works against any Odoo Online,
Odoo.sh, or self-hosted instance -- no extra Odoo modules required).

To activate: set in your environment (or .env)
    ODOO_MODE=live
    ODOO_URL=https://your-company.odoo.com
    ODOO_DB=your-db-name
    ODOO_USERNAME=api-user@yourcompany.com
    ODOO_API_KEY=xxxxxxxxxxxxxxxx

Assumed Odoo models (standard Odoo Purchase + Inventory apps):
  purchase.order          -> Purchase Orders
  stock.picking            -> Goods Receipt Notes (incoming shipments)
  account.move (move_type='in_invoice') -> Vendor Bills, used for export
"""
import xmlrpc.client

from modules.odoo.base_client import OdooClientBase


class OdooClient(OdooClientBase):
    def __init__(self, url: str, db: str, username: str, api_key: str):
        if not all([url, db, username, api_key]):
            raise ValueError(
                "Live Odoo mode requires ODOO_URL, ODOO_DB, ODOO_USERNAME and ODOO_API_KEY to be set."
            )
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.api_key = api_key
        self._uid = None

    # -- connection -----------------------------------------------------
    def _common(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    def _models(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def _authenticate(self):
        if self._uid is None:
            self._uid = self._common().authenticate(self.db, self.username, self.api_key, {})
            if not self._uid:
                raise ConnectionError("Odoo authentication failed - check ODOO_DB/USERNAME/API_KEY.")
        return self._uid

    def _execute(self, model, method, *args, **kwargs):
        uid = self._authenticate()
        return self._models().execute_kw(self.db, uid, self.api_key, model, method, list(args), kwargs)

    def test_connection(self) -> dict:
        try:
            uid = self._authenticate()
            return {"success": True, "message": f"Connected to Odoo at {self.url} (uid={uid})."}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "message": str(exc)}

    # -- reads ------------------------------------------------------------
    def fetch_purchase_order(self, po_number: str):
        try:
            records = self._execute(
                "purchase.order", "search_read",
                [[["name", "=", po_number]]],
                fields=["name", "partner_id", "amount_untaxed", "amount_tax", "amount_total",
                        "currency_id", "date_order", "state"],
                limit=1,
            )
        except Exception:
            return None
        if not records:
            return None
        rec = records[0]
        return {
            "po_number": rec["name"],
            "vendor_name": rec["partner_id"][1] if rec.get("partner_id") else "Unknown Vendor",
            "quantity": 1,  # header-level PO; line-level quantity would need purchase.order.line
            "unit_price": rec.get("amount_untaxed", 0.0),
            "tax_amount": rec.get("amount_tax", 0.0),
            "total_price": rec.get("amount_total", 0.0),
            "currency": rec["currency_id"][1] if rec.get("currency_id") else "INR",
            "order_date": rec.get("date_order"),
            "status": rec.get("state"),
        }

    def fetch_grn(self, grn_number: str, po_number: str = None):
        try:
            records = self._execute(
                "stock.picking", "search_read",
                [[["name", "=", grn_number]]],
                fields=["name", "partner_id", "origin", "scheduled_date", "state"],
                limit=1,
            )
        except Exception:
            return None
        if not records:
            return None
        rec = records[0]
        return {
            "grn_number": rec["name"],
            "po_number": rec.get("origin") or po_number,
            "vendor_name": rec["partner_id"][1] if rec.get("partner_id") else "Unknown Vendor",
            "quantity_received": None,  # would need stock.move.line for exact qty
            "unit_price": None,
            "total_price": None,
            "currency": "INR",
            "delivery_date": rec.get("scheduled_date"),
            "status": rec.get("state"),
        }

    # -- writes -----------------------------------------------------------
    def export_vendor_bill(self, invoice: dict) -> dict:
        try:
            partner_ids = self._execute(
                "res.partner", "search", [[["name", "=", invoice.get("vendor_name")]]], limit=1
            )
            partner_id = partner_ids[0] if partner_ids else False

            bill_vals = {
                "move_type": "in_invoice",
                "partner_id": partner_id,
                "ref": invoice.get("invoice_number"),
                "invoice_line_ids": [(0, 0, {
                    "name": f"Invoice {invoice.get('invoice_number')} / PO {invoice.get('po_number')}",
                    "quantity": invoice.get("quantity") or 1,
                    "price_unit": invoice.get("unit_price") or 0,
                })],
            }
            bill_id = self._execute("account.move", "create", bill_vals)
            return {
                "success": True,
                "odoo_bill_id": bill_id,
                "reference": invoice.get("invoice_number"),
                "message": f"Vendor bill (account.move id={bill_id}) created in Odoo.",
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "odoo_bill_id": None, "reference": None, "message": str(exc)}

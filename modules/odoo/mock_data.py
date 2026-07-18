"""
Seed data standing in for a real Odoo instance.

Per the spec's "Test Data" step, in a real rollout you'd load 20-30 sample
POs/GRNs into Odoo first, matching the vendor/PO number/price on invoices
you plan to test with. This module is that same idea, just in-memory, so
the whole app is demoable with zero external setup.

Three POs are deliberately seeded to produce all three outcomes:
  PO-2024-001 / GRN-2024-001  -> exact match          (auto-export)
  PO-2024-002 / GRN-2024-002  -> price mismatch        (needs correction)
  PO-2024-003 / GRN-2024-003  -> exact match, different vendor
"""
from datetime import datetime

PURCHASE_ORDERS = {
    "PO-2024-001": {
        "po_number": "PO-2024-001",
        "vendor_name": "Tech Supplies Inc",
        "quantity": 100,
        "unit_price": 1000.0,
        "tax_amount": 18000.0,
        "total_price": 118000.0,
        "currency": "INR",
        "order_date": datetime(2024, 1, 15),
        "status": "Confirmed",
    },
    "PO-2024-002": {
        "po_number": "PO-2024-002",
        "vendor_name": "Office Products Ltd",
        "quantity": 50,
        "unit_price": 1500.0,
        "tax_amount": 13500.0,
        "total_price": 88500.0,
        "currency": "INR",
        "order_date": datetime(2024, 1, 20),
        "status": "Confirmed",
    },
    "PO-2024-003": {
        "po_number": "PO-2024-003",
        "vendor_name": "Engineering Co",
        "quantity": 20,
        "unit_price": 11500.0,
        "tax_amount": 41400.0,
        "total_price": 271400.0,
        "currency": "INR",
        "order_date": datetime(2024, 2, 1),
        "status": "Confirmed",
    },
    "PO-2024-004": {
        "po_number": "PO-2024-004",
        "vendor_name": "Supplies Hub",
        "quantity": 35,
        "unit_price": 1300.0,
        "tax_amount": 8190.0,
        "total_price": 53690.0,
        "currency": "INR",
        "order_date": datetime(2024, 2, 10),
        "status": "Confirmed",
    },
    "PO-2024-005": {
        "po_number": "PO-2024-005",
        "vendor_name": "Paper Co",
        "quantity": 200,
        "unit_price": 490.0,
        "tax_amount": 17640.0,
        "total_price": 115640.0,
        "currency": "INR",
        "order_date": datetime(2024, 2, 18),
        "status": "Confirmed",
    },
}

GRNS = {
    "GRN-2024-001": {
        "grn_number": "GRN-2024-001",
        "po_number": "PO-2024-001",
        "vendor_name": "Tech Supplies Inc",
        "quantity_received": 100,
        "unit_price": 1000.0,
        "total_price": 118000.0,
        "currency": "INR",
        "delivery_date": datetime(2024, 1, 16),
        "status": "Received",
    },
    "GRN-2024-002": {
        "grn_number": "GRN-2024-002",
        "po_number": "PO-2024-002",
        "vendor_name": "Office Products Ltd",
        "quantity_received": 50,
        "unit_price": 1500.0,
        "total_price": 88500.0,
        "currency": "INR",
        "delivery_date": datetime(2024, 1, 22),
        "status": "Received",
    },
    "GRN-2024-003": {
        "grn_number": "GRN-2024-003",
        "po_number": "PO-2024-003",
        "vendor_name": "Engineering Co",
        "quantity_received": 20,
        "unit_price": 11500.0,
        "total_price": 271400.0,
        "currency": "INR",
        "delivery_date": datetime(2024, 2, 3),
        "status": "Received",
    },
    "GRN-2024-004": {
        "grn_number": "GRN-2024-004",
        "po_number": "PO-2024-004",
        "vendor_name": "Supplies Hub",
        "quantity_received": 35,
        "unit_price": 1300.0,
        "total_price": 53690.0,
        "currency": "INR",
        "delivery_date": datetime(2024, 2, 12),
        "status": "Received",
    },
    "GRN-2024-005": {
        "grn_number": "GRN-2024-005",
        "po_number": "PO-2024-005",
        "vendor_name": "Paper Co",
        "quantity_received": 200,
        "unit_price": 490.0,
        "total_price": 115640.0,
        "currency": "INR",
        "delivery_date": datetime(2024, 2, 20),
        "status": "Received",
    },
}

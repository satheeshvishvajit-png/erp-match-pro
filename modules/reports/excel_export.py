"""
Excel/CSV export for the Reports page, per the spec: "user filters by date
range, Invoice No, PO No, or Price, and downloads an Excel file listing all
processed invoices with their match status."
"""
import io
from datetime import datetime

import pandas as pd

from modules.database import get_session
from modules.models import Invoice


def query_invoices(date_from=None, date_to=None, invoice_number=None, po_number=None,
                    min_price=None, max_price=None, status=None, vendor=None):
    session = get_session()
    try:
        q = session.query(Invoice)
        if date_from:
            q = q.filter(Invoice.created_at >= date_from)
        if date_to:
            q = q.filter(Invoice.created_at <= date_to)
        if invoice_number:
            q = q.filter(Invoice.invoice_number.ilike(f"%{invoice_number}%"))
        if po_number:
            q = q.filter(Invoice.po_number.ilike(f"%{po_number}%"))
        if min_price is not None:
            q = q.filter(Invoice.grand_total >= min_price)
        if max_price is not None:
            q = q.filter(Invoice.grand_total <= max_price)
        if status:
            q = q.filter(Invoice.status == status)
        if vendor:
            q = q.filter(Invoice.vendor_name.ilike(f"%{vendor}%"))
        rows = q.order_by(Invoice.created_at.desc()).all()

        return pd.DataFrame([{
            "Invoice No": r.invoice_number,
            "Vendor": r.vendor_name,
            "PO No": r.po_number,
            "GRN No": r.grn_number,
            "Invoice Date": r.invoice_date,
            "Quantity": r.quantity,
            "Unit Price": r.unit_price,
            "Tax / GST": r.tax_amount,
            "Grand Total": r.grand_total,
            "Currency": r.currency,
            "Status": r.status.value if hasattr(r.status, "value") else r.status,
            "OCR Confidence %": r.ocr_confidence,
            "Correction Reason": r.correction_reason,
            "Uploaded At": r.created_at,
            "Exported At": r.exported_at,
        } for r in rows])
    finally:
        session.close()


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Invoices", index=False)
        workbook = writer.book
        sheet = writer.sheets["Invoices"]

        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#2563EB", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        for col_idx, col_name in enumerate(df.columns):
            sheet.write(0, col_idx, col_name, header_fmt)
            width = max(14, min(32, int(df[col_name].astype(str).str.len().max() or 14) + 2))
            sheet.set_column(col_idx, col_idx, width)

        status_formats = {
            "Matched": workbook.add_format({"bg_color": "#D1FAE5", "font_color": "#065F46"}),
            "Exported": workbook.add_format({"bg_color": "#DBEAFE", "font_color": "#1E3A8A"}),
            "Mismatch": workbook.add_format({"bg_color": "#FEE2E2", "font_color": "#991B1B"}),
            "Pending Review": workbook.add_format({"bg_color": "#FEF3C7", "font_color": "#92400E"}),
        }
        if "Status" in df.columns:
            status_col = df.columns.get_loc("Status")
            for row_idx, status in enumerate(df["Status"], start=1):
                fmt = status_formats.get(status)
                if fmt:
                    sheet.write(row_idx, status_col, status, fmt)

        sheet.freeze_panes(1, 0)

    return buffer.getvalue()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def generate_report_filename(ext: str) -> str:
    return f"ERP_Match_Pro_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"

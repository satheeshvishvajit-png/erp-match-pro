"""Simple one-page PDF summary report (KPIs + top rows table) for the
Reports page's "PDF Report" export option."""
from datetime import datetime

from fpdf import FPDF

import config


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(17, 24, 39)
        self.cell(0, 10, config.APP_NAME, ln=1)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(107, 114, 128)
        self.cell(0, 6, f"3-Way Matching Report - generated {datetime.now().strftime('%d %b %Y %H:%M')}", ln=1)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def build_pdf_report(kpis: dict, df) -> bytes:
    pdf = ReportPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()

    # KPI strip
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(17, 24, 39)
    col_w = 277 / max(len(kpis), 1)
    for label, value in kpis.items():
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.set_fill_color(245, 247, 250)
        pdf.rect(x, y, col_w - 3, 18, style="F")
        pdf.set_xy(x + 2, y + 2)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(col_w - 6, 5, label.upper(), ln=2)
        pdf.set_x(x + 2)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(col_w - 6, 8, str(value), ln=0)
        pdf.set_xy(x + col_w, y)
    pdf.ln(24)

    # Table
    if df is not None and not df.empty:
        cols = ["Invoice No", "Vendor", "PO No", "Grand Total", "Status"]
        cols = [c for c in cols if c in df.columns]
        widths = {c: 277 / len(cols) for c in cols}

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(37, 99, 235)
        pdf.set_text_color(255, 255, 255)
        for c in cols:
            pdf.cell(widths[c], 8, c, border=0, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(17, 24, 39)
        fill = False
        for _, row in df.head(35).iterrows():
            pdf.set_fill_color(245, 247, 250) if fill else pdf.set_fill_color(255, 255, 255)
            for c in cols:
                val = row[c]
                text = f"{val:,.2f}" if isinstance(val, float) else str(val)
                pdf.cell(widths[c], 7, text[:40], border=0, fill=True)
            pdf.ln()
            fill = not fill

    return bytes(pdf.output())

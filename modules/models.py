"""
ORM models for ERP Match Pro.

Table map (per the spec's DATABASE TABLES section):
  Users, Invoices, PurchaseOrders, GRNs, MatchingResults, AuditLogs,
  Exports, Notifications. (Reports and Settings are generated on the fly /
  stored as simple key-value rows rather than needing their own heavy
  tables -- see Setting below.)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship

from modules.database import Base


def gen_id(prefix):
    def _gen():
        return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"
    return _gen


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    ACCOUNTS_PAYABLE = "Accounts Payable"
    MANAGER = "Manager"


class InvoiceStatus(str, enum.Enum):
    UPLOADED = "Uploaded"          # OCR done, not yet matched
    MATCHED = "Matched"            # 3-way match succeeded
    EXPORTED = "Exported"          # pushed to Odoo as a Vendor Bill
    MISMATCH = "Mismatch"          # awaiting user correction
    PENDING_REVIEW = "Pending Review"  # user skipped correction
    REJECTED = "Rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id("USR"))
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ACCOUNTS_PAYABLE, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    avatar_color = Column(String, default="#2563EB")

    invoices = relationship("Invoice", back_populates="uploaded_by_user")


class PurchaseOrder(Base):
    """Mirrors a PO pulled from Odoo (or the mock Odoo client)."""
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, default=gen_id("PO"))
    po_number = Column(String, unique=True, nullable=False, index=True)
    vendor_name = Column(String, nullable=False)
    odoo_partner_id = Column(Integer, nullable=True)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    order_date = Column(DateTime, nullable=True)
    status = Column(String, default="Confirmed")


class GRN(Base):
    """Goods Receipt Note pulled from Odoo (or the mock client)."""
    __tablename__ = "grns"

    id = Column(String, primary_key=True, default=gen_id("GRN"))
    grn_number = Column(String, unique=True, nullable=False, index=True)
    po_number = Column(String, ForeignKey("purchase_orders.po_number"), nullable=False)
    vendor_name = Column(String, nullable=False)
    quantity_received = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    delivery_date = Column(DateTime, nullable=True)
    status = Column(String, default="Received")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=gen_id("INV"))
    invoice_number = Column(String, nullable=False, index=True)
    vendor_name = Column(String, nullable=True)
    po_number = Column(String, nullable=True, index=True)
    grn_number = Column(String, nullable=True, index=True)

    invoice_date = Column(DateTime, nullable=True)
    currency = Column(String, default="INR")
    unit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    tax_amount = Column(Float, default=0.0)
    grand_total = Column(Float, nullable=True)

    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    ocr_confidence = Column(Float, default=0.0)
    ocr_raw_text = Column(Text, nullable=True)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.UPLOADED, nullable=False)
    correction_reason = Column(Text, nullable=True)

    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    exported_at = Column(DateTime, nullable=True)

    uploaded_by_user = relationship("User", back_populates="invoices")
    matching_results = relationship("MatchingResult", back_populates="invoice", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="invoice", cascade="all, delete-orphan")


class MatchingResult(Base):
    __tablename__ = "matching_results"

    id = Column(String, primary_key=True, default=gen_id("MR"))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)

    po_price = Column(Float, nullable=True)
    grn_price = Column(Float, nullable=True)
    invoice_price = Column(Float, nullable=True)

    price_variance = Column(Float, nullable=True)
    is_match = Column(Boolean, default=False)
    field_results_json = Column(Text, nullable=True)  # per-field green/yellow/red detail

    run_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="matching_results")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_id("LOG"))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)        # e.g. "UPLOADED", "MATCH_RUN", "CORRECTED", "EXPORTED"
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="audit_logs")


class Export(Base):
    __tablename__ = "exports"

    id = Column(String, primary_key=True, default=gen_id("EXP"))
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    odoo_vendor_bill_id = Column(Integer, nullable=True)
    odoo_vendor_bill_ref = Column(String, nullable=True)
    exported_at = Column(DateTime, default=datetime.utcnow)
    exported_by = Column(String, ForeignKey("users.id"), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=gen_id("NTF"))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # null = broadcast
    title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    level = Column(String, default="info")  # info | success | warning | danger
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Setting(Base):
    """Simple key-value store backing the Settings page (Odoo mode, theme, etc.)."""
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)

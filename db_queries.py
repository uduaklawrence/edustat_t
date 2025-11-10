import pandas as pd
from db_connection import create_connection
import streamlit as st
import json
import uuid
from datetime import datetime
from sqlalchemy import text
 
# =========================================================
# 🔁 CACHING SETUP
# =========================================================
 
@st.cache_data(ttl=300)  # cache query results for 5 minutes
 
def fetch_data(query, params=None):
    engine = create_connection()
    if engine:
        try:
            df = pd.read_sql(query, engine, params=params)
            return df
        except Exception as e:
            st.error(f"Query execution error: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()
 
# ---------------------------------------------------------
# Update user payment status
# ---------------------------------------------------------
def update_payment_status(email: str):
    """Updates the user's payment status to True (1) in the database."""
    query = text("UPDATE users SET payment = 1 WHERE email_address = :email")
    engine = create_connection()
    try:
        with engine.begin() as conn:
            conn.execute(query, {"email": email})
        print(f"✅ DATABASE: Updated payment status for {email}")
        # clear relevant cache since data changed
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"❌ DATABASE ERROR: Failed to update payment status for {email}. Error: {e}")
        return False
 
# =========================================================
# 🧾 INVOICE FUNCTIONS (SQLAlchemy text() FIXED)
# =========================================================
 
def create_invoice_record(user_id: int, total: int, data_dict: dict) -> str:
    """Create an invoice record and return its unique ref."""
    engine = create_connection()
    inv_ref = f"INV-{uuid.uuid4().hex[:8].upper()}"
    data_json = json.dumps(data_dict, default=str)
 
    insert_query = text("""
        INSERT INTO invoices (user_id, ref, total, data)
        VALUES (:user_id, :ref, :total, :data_json)
    """)
 
    try:
        with engine.begin() as conn:
            conn.execute(insert_query, {
                "user_id": user_id,
                "ref": inv_ref,
                "total": total,
                "data_json": data_json
            })
        print(f"✅ Invoice created: {inv_ref}")
         # clear cache since new invoice added
        st.cache_data.clear()
        return inv_ref
    except Exception as e:
        st.error(f"❌ Failed to create invoice: {e}")
        return None
 
def attach_paystack_ref_to_invoice(invoice_ref: str, paystack_ref: str):
    """Attach Paystack reference and set status to pending."""
    if not invoice_ref:
        st.error("❌ No valid invoice reference provided.")
        return
 
    engine = create_connection()
    update_query = text("""
        UPDATE invoices
        SET invoice_data =
            CASE
                WHEN invoice_data IS NULL THEN JSON_OBJECT('paystack_reference', :paystack_ref, 'status', 'pending')
                ELSE JSON_SET(invoice_data, '$.paystack_reference', :paystack_ref, '$.status', 'pending')
            END
        WHERE ref = :invoice_ref
    """)
 
    try:
        with engine.begin() as conn:
            conn.execute(update_query, {
                "paystack_ref": paystack_ref,
                "invoice_ref": invoice_ref
            })
        print(f"🔗 Linked Paystack ref {paystack_ref} to invoice {invoice_ref}")
        st.cache_data.clear()  # clear cache
    except Exception as e:
        st.error(f"❌ Failed to attach Paystack ref: {e}")
 
def mark_invoice_paid_by_paystack_ref(paystack_ref: str):
    """Mark invoice as paid using Paystack reference."""
    engine = create_connection()
    update_query = text("""
        UPDATE invoices
        SET invoice_data =
            CASE
                WHEN invoice_data IS NULL THEN JSON_OBJECT('status', 'paid')
                ELSE JSON_SET(invoice_data, '$.status', 'paid')
            END,
            updated_at = NOW()
        WHERE JSON_EXTRACT(invoice_data, '$.paystack_reference') = :paystack_ref
    """)
 
    try:
        with engine.begin() as conn:
            conn.execute(update_query, {"paystack_ref": paystack_ref})
        print(f"💰 Invoice with Paystack ref {paystack_ref} marked as paid.")
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ Failed to mark invoice as paid: {e}")
 
def update_invoice_pdf_path(invoice_ref: str, pdf_path: str):
    """Update PDF file path for an invoice."""
    engine = create_connection()
    update_query = text("UPDATE invoices SET pdf = :pdf_path WHERE ref = :invoice_ref")
 
    try:
        with engine.begin() as conn:
            conn.execute(update_query, {"pdf_path": pdf_path, "invoice_ref": invoice_ref})
        print(f"📄 Stored PDF path for invoice {invoice_ref}: {pdf_path}")
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ Failed to update PDF path: {e}")
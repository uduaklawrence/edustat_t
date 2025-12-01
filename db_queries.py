import pandas as pd
from db_connection import create_connection
import streamlit as st
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
 
# =========================================================
# 🔁 CACHING SETUP
# =========================================================
 
@st.cache_data(ttl=300)  # cache for 5 minutes
def fetch_data(query, params=None):
    engine = create_connection()
    if engine is None:
        return pd.DataFrame()
 
    try:
        df = pd.read_sql(text(query), engine, params=params)
        return df
    except Exception as e:
        st.error(f"Query execution error: {e}")
        return pd.DataFrame()
 
 
# =========================================================
# LOW LEVEL EXECUTION HELPER (used by inserts/updates)
# =========================================================
def execute_query(query, params=None):
    """Executes INSERT / UPDATE / DELETE queries."""
    engine = create_connection()
    if engine is None:
        st.error("Database connection failed.")
        return None
 
    try:
        with engine.begin() as conn:
            conn.execute(text(query), params or {})
        st.cache_data.clear()  # clear cache because DB changed
        return True
    except Exception as e:
        st.error(f"❌ Database execution error: {e}")
        return None
 
 
# =========================================================
# ✅ Update user payment status
# =========================================================
def update_payment_status(email):
    query = text("UPDATE users SET payment = 1 WHERE email_address = :email")
 
    engine = create_connection()
    if engine is None:
        return False
 
    try:
        with engine.begin() as conn:
            conn.execute(query, {"email": email})
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Failed to update payment status: {e}")
        return False
 
 
# =========================================================
# 🧾 INVOICE FUNCTIONS
# =========================================================
def create_invoice_record(user_id, total, data_dict):
    """Creates a new invoice and returns invoice_ref."""
    engine = create_connection()
    if engine is None:
        return None
 
    invoice_ref = f"INV-{uuid.uuid4().hex[:8].upper()}"
    data_json = json.dumps(data_dict, default=str)
 
    query = text("""
        INSERT INTO invoices (user_id, ref, total, data)
        VALUES (:user_id, :ref, :total, :data_json)
    """)
 
    try:
        with engine.begin() as conn:
            conn.execute(query, {
                "user_id": user_id,
                "ref": invoice_ref,
                "total": total,
                "data_json": data_json
            })
        st.cache_data.clear()
        return invoice_ref
    except Exception as e:
        st.error(f"Failed to create invoice: {e}")
        return None
 
 
def attach_paystack_ref_to_invoice(invoice_ref, paystack_ref):
    if not invoice_ref:
        st.error("Missing invoice reference.")
        return
 
    engine = create_connection()
    if engine is None:
        return
 
    query = text("""
        UPDATE invoices
        SET invoice_data =
            CASE
                WHEN invoice_data IS NULL THEN JSON_OBJECT('paystack_reference', :p_ref, 'status', 'pending')
                ELSE JSON_SET(invoice_data, '$.paystack_reference', :p_ref, '$.status', 'pending')
            END
        WHERE ref = :invoice_ref
    """)
 
    try:
        with engine.begin() as conn:
            conn.execute(query, {
                "p_ref": paystack_ref,
                "invoice_ref": invoice_ref
            })
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to attach paystack ref: {e}")
 
 
def mark_invoice_paid_by_paystack_ref(paystack_ref):
    engine = create_connection()
    if engine is None:
        return
 
    query = text("""
        UPDATE invoices
        SET invoice_data =
            CASE
                WHEN invoice_data IS NULL THEN JSON_OBJECT('status', 'paid')
                ELSE JSON_SET(invoice_data, '$.status', 'paid')
            END,
            updated_at = NOW()
        WHERE JSON_EXTRACT(invoice_data, '$.paystack_reference') = :p_ref
    """)
 
    try:
        with engine.begin() as conn:
            conn.execute(query, {"p_ref": paystack_ref})
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to mark invoice paid: {e}")
 
 
def update_invoice_pdf_path(invoice_ref, pdf_path):
    engine = create_connection()
    if engine is None:
        return
 
    query = text("UPDATE invoices SET pdf = :pdf_path WHERE ref = :invoice_ref")
 
    try:
        with engine.begin() as conn:
            conn.execute(query, {"pdf_path": pdf_path, "invoice_ref": invoice_ref})
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Failed to update invoice PDF path: {e}")
 
 
# =========================================================
# 📁 SAVE USER REPORT (Option A — auto expires_at)
# =========================================================
def save_user_report(user_id, invoice_ref, report_group, filters, charts, pdf_path):
    """
    Saves a paid user report.
    ⚠ expires_at is auto-generated by MySQL from created_at + INTERVAL 30 DAY
    """
 
    query = """
        INSERT INTO user_reports (
            user_id,
            invoice_ref,
            report_group,
            filters,
            charts,
            pdf_path,
            created_at
        )
        VALUES (
            :user_id,
            :invoice_ref,
            :report_group,
            :filters,
            :charts,
            :pdf_path,
            NOW()
        )
    """
 
    params = {
        "user_id": user_id,
        "invoice_ref": invoice_ref,
        "report_group": report_group,
        "filters": json.dumps(filters or {}),
        "charts": json.dumps(charts or []),
        "pdf_path": pdf_path
    }
 
    return execute_query(query, params)
 
 
# =========================================================
# 📁 Fetch User Reports (not expired)
# =========================================================
def fetch_user_reports(user_id):
    query = """
        SELECT *
        FROM user_reports
        WHERE user_id = :uid
        AND expires_at > NOW()
        ORDER BY created_at DESC
    """
    return fetch_data(query, {"uid": user_id})
 
 
# =========================================================
# 📁 Fetch Single Report
# =========================================================
def fetch_single_report(report_id, user_id):
    query = """
        SELECT *
        FROM user_reports
        WHERE report_id = :rid
        AND user_id = :uid
    """
    return fetch_data(query, {"rid": report_id, "uid": user_id})
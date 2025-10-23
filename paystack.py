# paystack.py
import streamlit as st
import requests
from sqlalchemy import text
from db_connection import create_connection

# ---------------------------------------------------------
# Paystack Configuration
# ---------------------------------------------------------
try:
    SECRET_KEY = st.secrets["PAYSTACK_SECRET_KEY"]
except (FileNotFoundError, KeyError) as e:
    st.error(f"⚠️ Paystack API credentials not found in secrets.toml: {e}")
    SECRET_KEY = None

BASE_URL = "https://api.paystack.co"


# ---------------------------------------------------------
# Save Payment Record to Database
# ---------------------------------------------------------
def save_payment_record(email_address, reference, trxref, status, amount, gateway_response, response, redirect_url):
    """
    Inserts or updates a payment record in the 'payments' table.
    Uses 'reference' as the unique key.
    """
    engine = create_connection()
    if not engine:
        st.error("❌ Unable to connect to database.")
        return

    try:
        with engine.begin() as conn:
            query = text("""
                INSERT INTO payments (
                    email_address, reference, trxref, status, amount, gateway_response, response, redirect_url
                )
                VALUES (
                    :email_address, :reference, :trxref, :status, :amount, :gateway_response, :response, :redirect_url
                )
                ON DUPLICATE KEY UPDATE
                    trxref = VALUES(trxref),
                    status = VALUES(status),
                    amount = VALUES(amount),
                    gateway_response = VALUES(gateway_response),
                    response = VALUES(response),
                    redirect_url = VALUES(redirect_url)
            """)
            conn.execute(query, {
                "email_address": email_address,
                "reference": reference,
                "trxref": trxref,
                "status": status,
                "amount": amount,
                "gateway_response": gateway_response,
                "response": response,
                "redirect_url": redirect_url
            })
    except Exception as e:
        st.error(f"💥 Database write error: {e}")


# ---------------------------------------------------------
# Initialize Paystack Transaction
# ---------------------------------------------------------
def initialize_transaction(email_address: str, amount: float):
    """
    Starts a Paystack transaction and logs it to the DB.
    Returns authorization_url and reference on success.
    """
    if not SECRET_KEY:
        st.error("⚠️ Paystack API key is not configured.")
        return None

    url = f"{BASE_URL}/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {SECRET_KEY}",
        "Content-Type": "application/json"
    }

    amount_in_kobo = int(amount * 100)
    payload = {"email": email_address, "amount": amount_in_kobo}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get("status"):
            transaction_data = data.get("data", {})
            reference = transaction_data.get("reference")
            authorization_url = transaction_data.get("authorization_url")

            # ✅ Save the initialized transaction
            save_payment_record(
                email_address=email_address,
                reference=reference,
                trxref=None,
                status="initialized",
                amount=amount,
                gateway_response="Transaction initialized",
                response=str(data),
                redirect_url=authorization_url
            )

            return {
                "authorization_url": authorization_url,
                "reference": reference
            }

        else:
            msg = data.get("message", "Transaction initialization failed")
            save_payment_record(
                email_address=email_address,
                reference=None,
                trxref=None,
                status="failed",
                amount=amount,
                gateway_response=msg,
                response=str(data),
                redirect_url=None
            )
            st.error(f"Paystack Error: {msg}")
            return None

    except requests.exceptions.RequestException as e:
        st.error(f"Network error during payment initialization: {e}")
        save_payment_record(
            email_address=email_address,
            reference=None,
            trxref=None,
            status="network_error",
            amount=amount,
            gateway_response="Request failed",
            response=str(e),
            redirect_url=None
        )
        return None


# ---------------------------------------------------------
# Verify Transaction
# ---------------------------------------------------------
def verify_transaction(reference: str):
    """
    Verifies a Paystack transaction and updates both
    the payments and users tables.
    """
    if not SECRET_KEY:
        st.error("⚠️ Paystack API key is not configured.")
        return None

    url = f"{BASE_URL}/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {SECRET_KEY}"}
    engine = create_connection()

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("status"):
            data = result.get("data", {})
            email_address = data.get("customer", {}).get("email", None)
            trxref = data.get("trxref", reference)
            status = data.get("status", "unknown")
            amount = float(data.get("amount", 0)) / 100  # Convert from kobo to NGN
            gateway_response = data.get("gateway_response", "No message")
            redirect_url = f"?trxref={trxref}&reference={reference}"
            message = result.get("message", "Verification completed")

            # ✅ Update the existing payment record instead of inserting a new one
            if engine:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE payments
                        SET 
                            status = :status,
                            trxref = :trxref,
                            gateway_response = :gateway_response,
                            response = :response,
                            redirect_url = :redirect_url,
                            paid_at = CURRENT_TIMESTAMP
                        WHERE reference = :reference AND email_address = :email_address
                    """), {
                        "status": status,
                        "trxref": trxref,
                        "gateway_response": gateway_response,
                        "response": message,
                        "redirect_url": redirect_url,
                        "reference": reference,
                        "email_address": email_address
                    })

                # ✅ If payment succeeded, update user's payment flag
                if status == "success":
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE users
                            SET payment = TRUE
                            WHERE email_address = :email_address
                        """), {"email_address": email_address})
                    st.success("✅ Payment verified and user status updated.")
            else:
                st.error("❌ Database connection not established.")

        else:
            st.warning("⚠️ Paystack verification failed.")
        return result

    except requests.exceptions.RequestException as e:
        st.error(f"Verification error: {e}")
        return None


            # ✅ If payment succeeded, update users.payment = TRUE
        if status == "success" and engine:
                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE users
                        SET payment = TRUE
                        WHERE email_address = :email_address
                    """), {"email_address": email_address})
                st.success("✅ Payment verified and user status updated.")
        else:
            st.warning("⚠️ Paystack verification failed.")
        return result

    except requests.exceptions.RequestException as e:
        st.error(f"Verification error: {e}")
        return None

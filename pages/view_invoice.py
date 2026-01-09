# ==============================
# 📄 VIEW INVOICE - PAGE 2
# ==============================

import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from datetime import datetime
from db_queries import (
    fetch_data,
    update_payment_status,
    attach_paystack_ref_to_invoice,
    mark_invoice_paid_by_paystack_ref,
    save_user_report,
)
from paystack import initialize_transaction, verify_transaction
from invoice_pdf import generate_invoice_pdf

# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # ₦
WATERMARK_PATH = r"altered_edustat.jpg"

def get_base64_image(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# ------------------ AUTH CHECK ------------------
if not st.session_state.get("logged_in", False):
    st.warning("Please sign in to view the invoice.")
    st.stop()

st.set_page_config(page_title="Invoice & Payment", layout="wide")
st.title("🧾 Invoice & Payment")

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# Check if invoice data exists
if not st.session_state.get("invoice_ref"):
    st.error("❌ No invoice found. Please create a report first.")
    if st.button("← Go Back to Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

# Retrieve saved data
invoice_ref = st.session_state.invoice_ref
saved_group = st.session_state.get("saved_group")
saved_columns = st.session_state.get("saved_columns", [])
saved_description = st.session_state.get("saved_description", "Custom Report")
payment_verified = st.session_state.get("payment_verified", False)

# ============================================================
# DISPLAY PENDING INVOICE (if not paid)
# ============================================================
if not payment_verified:
    st.subheader("📄 Pending Invoice")
    
    # Generate pending invoice PDF
    pdf_path = generate_invoice_pdf(
        invoice_ref=invoice_ref,
        user_email=user_email,
        amount=SUBSCRIPTION_AMOUNT,
        description=saved_description,
        selected_group=saved_group,
        selected_columns=saved_columns,
        status="Pending Payment",
    )

    # Display pending invoice with watermark
    watermark_base64 = get_base64_image(WATERMARK_PATH)
    user_display = user_email.split("@")[0].replace(".", " ").title()
    invoice_date = datetime.now().strftime("%B %d, %Y")

    invoice_html = f"""
    <h2 style="text-align:center;">INVOICE</h2>
    <p><b>Name:</b> {user_display}</p>
    <p><b>Invoice No:</b> {invoice_ref}</p>
    <p><b>Date:</b> {invoice_date}</p>
    <p><b>Report Group:</b> {saved_group}</p>
    <p><b>Report Description:</b></p>
    <p>{saved_description}</p>
    <hr>
    <table style="width:100%; border-collapse:collapse;">
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th style="padding:8px; border:1px solid #ddd;">Item</th>
                <th style="padding:8px; border:1px solid #ddd;">Qty</th>
                <th style="padding:8px; border:1px solid #ddd;">Amount (₦)</th>
            </tr>
        </thead>
        <tbody>
    """

    for col in saved_columns:
        invoice_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">{col}</td>
            <td style="padding:8px; border:1px solid #ddd;">1</td>
            <td style="padding:8px; border:1px solid #ddd;">-</td>
        </tr>
        """

    invoice_html += f"""
        <tr>
            <td colspan="2" style="text-align:right; padding:8px; border:1px solid #ddd;"><b>Total</b></td>
            <td style="padding:8px; border:1px solid #ddd;"><b>₦{SUBSCRIPTION_AMOUNT:,.2f}</b></td>
        </tr>
        </tbody>
    </table>
    <p><b>Status:</b> Pending Payment ⏳</p>
    """

    container = f"""
    <div style="
        background:white;
        padding:25px;
        border-radius:10px;
        box-shadow:0 0 10px rgba(0,0,0,0.1);
        background-image:url('data:image/jpeg;base64,{watermark_base64}');
        background-repeat:no-repeat;
        background-position:center;
        background-size:45%;
    ">{invoice_html}</div>
    """

    components.html(container, height=680, scrolling=True)

    # Download pending invoice
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Download Pending Invoice PDF",
            f,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
            key="pending_invoice_download",
        )

    # ============================================================
    # PAYMENT GATEWAY
    # ============================================================
    st.markdown("---")
    st.subheader("💳 Payment Gateway")
    
    if not st.session_state.get("paystack_reference"):
        if st.button("Proceed to Payment", type="primary", key="pay_btn"):
            with st.spinner("Connecting to Paystack..."):
                try:
                    api_response = initialize_transaction(
                        email_address=user_email, 
                        amount=SUBSCRIPTION_AMOUNT
                    )
                    
                    if api_response and api_response.get("authorization_url"):
                        paystack_ref = api_response.get("reference")
                        st.session_state.paystack_reference = paystack_ref
                        
                        # Attach paystack reference to invoice
                        attach_paystack_ref_to_invoice(invoice_ref, paystack_ref)

                        checkout_url = api_response.get("authorization_url")
                        components.html(f"<script>window.open('{checkout_url}', '_blank');</script>")
                        st.success("✅ Paystack checkout opened in a new tab.")
                        st.warning("⚠️ After payment, return here and click **Verify My Payment** below.")
                    else:
                        st.error("Failed to connect to Paystack. Please try again.")
                except Exception as e:
                    st.error(f"Payment initialization error: {str(e)}")

    # ============================================================
    # VERIFY PAYMENT
    # ============================================================
    if st.session_state.get("paystack_reference"):
        st.markdown("---")
        st.subheader("✔️ Verify Payment")

        if st.button("Verify My Payment", type="primary", key="verify_btn"):
            paystack_ref = st.session_state.get("paystack_reference")
            
            with st.spinner("Verifying payment with Paystack..."):
                try:
                    verification_response = verify_transaction(paystack_ref)

                    if (
                        verification_response
                        and verification_response.get("status") is True
                        and verification_response.get("data", {}).get("status") == "success"
                    ):
                        # Update payment status in users table
                        update_payment_status(user_email)
                        st.session_state.payment_verified = True
                        
                        # Mark invoice as PAID
                        mark_invoice_paid_by_paystack_ref(paystack_ref)
                        
                        st.success("✅ Payment verified successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Payment verification failed. Please contact support if payment was deducted.")
                except Exception as e:
                    st.error(f"Verification error: {str(e)}")

# ============================================================
# DISPLAY PAID INVOICE + SAVE REPORT
# ============================================================
if payment_verified:
    st.subheader("✅ Payment Successful - Invoice Paid")
    
    # Retrieve saved values
    saved_group = st.session_state.get("saved_group")
    saved_columns = st.session_state.get("saved_columns", [])
    saved_filters = st.session_state.get("saved_filters", {})
    saved_charts = st.session_state.get("saved_charts", [])
    saved_where = st.session_state.get("saved_where_clause", "1=1")
    
    # Generate paid invoice PDF
    if not st.session_state.get("paid_pdf_generated", False):
        try:
            paid_pdf_path = generate_invoice_pdf(
                invoice_ref=invoice_ref,
                user_email=user_email,
                amount=SUBSCRIPTION_AMOUNT,
                description=saved_description,
                selected_group=saved_group,
                selected_columns=saved_columns,
                status="PAID ✅",
            )
            st.session_state.paid_pdf_path = paid_pdf_path
            st.session_state.paid_pdf_generated = True
        except Exception as e:
            st.error(f"❌ Error generating invoice PDF: {str(e)}")
            st.stop()
    
    # Display paid invoice
    watermark_base64 = get_base64_image(WATERMARK_PATH)
    user_display = user_email.split("@")[0].replace(".", " ").title()
    invoice_date = datetime.now().strftime("%B %d, %Y")
    
    paid_html = f"""
    <h2 style="text-align:center;">INVOICE</h2>
    <p><b>Name:</b> {user_display}</p>
    <p><b>Invoice No:</b> {invoice_ref}</p>
    <p><b>Date:</b> {invoice_date}</p>
    <p><b>Report Group:</b> {saved_group}</p>
    <hr>
    <table style="width:100%; border-collapse:collapse;">
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th style="padding:8px; border:1px solid #ddd;">Item</th>
                <th style="padding:8px; border:1px solid #ddd;">Qty</th>
                <th style="padding:8px; border:1px solid #ddd;">Amount (₦)</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for col in saved_columns:
        paid_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">{col}</td>
            <td style="padding:8px; border:1px solid #ddd;">1</td>
            <td style="padding:8px; border:1px solid #ddd;">-</td>
        </tr>
        """
    
    paid_html += f"""
        <tr>
            <td colspan="2" style="text-align:right; padding:8px; border:1px solid #ddd;"><b>Total</b></td>
            <td style="padding:8px; border:1px solid #ddd;"><b>₦{SUBSCRIPTION_AMOUNT:,.2f}</b></td>
        </tr>
        </tbody>
    </table>
    <p><b>Status:</b> PAID ✅</p>
    """
    
    container_paid = f"""
    <div style="
        background:white;
        padding:25px;
        border-radius:10px;
        box-shadow:0 0 10px rgba(0,0,0,0.1);
        background-image:url('data:image/jpeg;base64,{watermark_base64}');
        background-repeat:no-repeat;
        background-position:center;
        background-size:45%;
    ">{paid_html}</div>
    """
    
    components.html(container_paid, height=680, scrolling=True)
    
    # Download paid invoice
    with open(st.session_state.paid_pdf_path, "rb") as f:
        st.download_button(
            "📄 Download Invoice PDF",
            f,
            file_name=os.path.basename(st.session_state.paid_pdf_path),
            mime="application/pdf",
            key="download_paid_invoice"
        )
    
    # ========================================
    # SAVE REPORT
    # ========================================
    st.markdown("---")
    st.subheader("📝 Name Your Report")
    
    default_report_name = f"{saved_group} Report - {datetime.now().strftime('%b %d, %Y')}"
    
    report_name = st.text_input(
        "Enter a name for your report:",
        value=default_report_name,
        key="report_name_input"
    )
    
    if not st.session_state.get("report_saved", False):
        if st.button("💾 Save Report", type="primary"):
            if not report_name.strip():
                st.error("❌ Report name cannot be empty.")
            else:
                try:
                    save_user_report(
                        user_id=st.session_state.user_id,
                        invoice_ref=invoice_ref,
                        report_group=saved_group,
                        report_name=report_name.strip(),
                        filters=saved_filters,
                        charts=saved_charts,
                        pdf_path=st.session_state.paid_pdf_path
                    )
                    st.session_state.report_saved = True
                    st.session_state.report_ready = True
                    st.success("✅ Report saved successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Failed to save report: {str(e)}")
    else:
        st.success("✅ Report already saved to your account!")
        st.session_state.report_ready = True
        
        # View report button
        st.markdown("---")
        if st.button("📊 View Report", type="primary", key="view_report_btn"):
            st.switch_page("pages/view_report.py")
        
        st.info("🗂️ Your report is saved for 30 days in your account.")
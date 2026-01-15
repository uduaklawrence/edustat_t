# ==============================
# 📊 CREATE REPORT - CORRECTED VERSION
# ==============================

import streamlit as st
import streamlit.components.v1 as components
import os
import json
from datetime import datetime
import base64
import pandas as pd 
from Analytics_layer import get_exam_dataset
from db_queries import (
    update_payment_status,
    create_invoice_record,
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
    st.warning("Please sign in to view the report.")
    st.stop()

st.set_page_config(page_title="Create Report", layout="wide")
st.title("📊 Create Custom Reports")

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)


# ------------------ LOAD ANALYTICS DATA (REDIS ONLY) ------------------

@st.cache_data(show_spinner=False)
def load_dataset():
    return get_exam_dataset()

df = load_dataset()

# ------------------ SESSION DEFAULTS ------------------
st.session_state.setdefault("paystack_reference", None)
st.session_state.setdefault("invoice_ref", None)
st.session_state.setdefault("payment_verified", False)
st.session_state.setdefault("saved_group", None)
st.session_state.setdefault("saved_columns", None)
st.session_state.setdefault("saved_filters", None)
st.session_state.setdefault("saved_charts", None)
st.session_state.setdefault("pending_invoice_saved", False)
st.session_state.setdefault("report_saved", False)
st.session_state.setdefault("filtered_df", None)
st.session_state.setdefault("report_ready", False)

# # ============================================================
# # 🔄 AUTO-RESTORE: Resume Pending/Paid Invoice
# # ============================================================
# def restore_user_state():
#     """Load user's last invoice/report state from database."""
#     if st.session_state.get("state_restored", False):
#         return  # Already restored this session
    
#     try:
#         # Get user's most recent invoice
#         latest_invoice_query = f"""
#             SELECT 
#                 invoice_ref,
#                 status,
#                 paystack_reference,
#                 data
#             FROM invoices 
#             WHERE user_id = {user_id}
#             ORDER BY created_at DESC 
#             LIMIT 1
#         """
#         invoice_df = fetch_data(latest_invoice_query)
        
#         if not invoice_df.empty:
#             invoice = invoice_df.iloc[0]
#             invoice_ref = invoice['invoice_ref']
#             status = invoice['status']
            
#             # Show resumption banner
#             if status == 'PENDING':
#                 st.info(f"📋 **Resuming Pending Invoice:** {invoice_ref}")
#             elif status == 'PAID':
#                 st.success(f"✅ **Resuming Paid Invoice:** {invoice_ref}")
            
#             # Restore invoice reference
#             st.session_state.invoice_ref = invoice_ref
#             st.session_state.pending_invoice_saved = True
            
#             # Restore payment status
#             if status == 'PAID':
#                 st.session_state.payment_verified = True
#                 st.session_state.paystack_reference = invoice.get('paystack_reference')
                
#                 # Check if report was already saved
#                 report_check = fetch_data(f"""
#                     SELECT report_id, report_name 
#                     FROM user_reports 
#                     WHERE invoice_ref = '{invoice_ref}'
#                     LIMIT 1
#                 """)
                
#                 if not report_check.empty:
#                     st.session_state.report_saved = True
#                     st.caption(f"📁 Report saved as: **{report_check.iloc[0]['report_name']}**")
            
#             # Restore filters/selections from invoice data JSON
#             if 'data' in invoice and invoice['data']:
#                 try:
#                     data_dict = json.loads(invoice['data']) if isinstance(invoice['data'], str) else invoice['data']
                    
#                     st.session_state.saved_group = data_dict.get('report_group')
#                     st.session_state.saved_filters = data_dict.get('filters', {})
#                     st.session_state.saved_charts = data_dict.get('charts', [])
                    
#                     # Restore where clause
#                     filters = []
#                     for col, values in data_dict.get('filters', {}).items():
#                         if "All" not in values and values:
#                             if col == "Age":
#                                 # Handle age filter restoration
#                                 pass  # You can add age logic here
#                             else:
#                                 value_list = ", ".join(f"'{v}'" for v in values)
#                                 filters.append(f"{col} IN ({value_list})")
                    
#                     st.session_state.saved_where_clause = " AND ".join(filters) if filters else "1=1"
                    
#                 except Exception as parse_err:
#                     st.warning(f"Could not parse saved filters: {parse_err}")
            
#             st.session_state.state_restored = True
            
#             # Show action buttons
#             col1, col2 = st.columns(2)
#             with col1:
#                 if st.button("✏️ Edit & Create New Invoice", type="secondary"):
#                     # Clear session to start fresh
#                     for key in ['invoice_ref', 'payment_verified', 'saved_group', 'saved_filters']:
#                         if key in st.session_state:
#                             del st.session_state[key]
#                     st.session_state.state_restored = False
#                     st.rerun()
            
#             with col2:
#                 if status == 'PENDING':
#                     st.info("👇 Scroll down to proceed with payment")
#                 elif status == 'PAID':
#                     if st.button("📊 View My Report", type="primary"):
#                         st.switch_page("pages/view_report.py")
    
#     except Exception as e:
#         st.warning(f"Could not restore previous session: {str(e)}")

# # 🚀 Call restore function on page load
# restore_user_state()

# ------------------ STEP 1: INSIGHT GROUP SELECTION ------------------
insight_groups = [
    "Demographic Analysis",
    "Geographic & Institutional Insights",
    "Equity & Sponsorship",
    "Temporal & Progression Trends",
]
selected_group = st.selectbox("Select Insight Group", insight_groups)

# ------------------ STEP 2: COLUMN SELECTION ------------------
columns_map = {
    "Demographic Analysis": ["ExamYear", "Sex", "Disability", "Age"],
    "Geographic & Institutional Insights": ["ExamYear", "State", "Centre"],
    "Equity & Sponsorship": ["ExamYear", "Sponsor", "Sex", "Disability"],
    "Temporal & Progression Trends": ["ExamYear"],
}
available_columns = columns_map[selected_group]
selected_columns = st.multiselect(
    "Select Columns to Filter", available_columns, default=available_columns
)

# ------------------ STEP 3: APPLY FILTERS ------------------
st.subheader("Apply Filters")

filter_values = {}
selected_age_groups = []  # Initialize outside loop

for col in selected_columns:
    if col == "Age":
        # Define age groups
        age_groups = ["Below 18", "Above 18"]

        # Allow users to select age groups
        selected_age_groups = st.multiselect(
            "Select Age Groups:",
            age_groups,
            default=age_groups
        )
        filter_values["Age"] = selected_age_groups
    else:
        distinct_vals = sorted(df[col].dropna().unique().tolist())
        filter_values[col] = st.multiselect(
            f"{col}:",
            ["All"] + distinct_vals,
            default=["All"],
        )

# ============================================================
# CHART TYPE SELECTION
# ============================================================
st.markdown("---")
st.subheader("Select Chart Types")
chart_options = ["Table/Matrix", "Bar Chart", "Pie Chart", "Line Chart"]
selected_charts = st.multiselect("Select chart(s):", chart_options, default=["Table/Matrix"])

# ============================================================
# STEP 5: GENERATE PENDING INVOICE
# ============================================================
st.markdown("---")
st.subheader("🧾 Generate Invoice for This Report")

if st.button("Generate Invoice", type="primary"):
    user_has_paid = bool(st.session_state.get("payment_verified", False))

    # Save selections to session state
    st.session_state.saved_group = selected_group
    st.session_state.saved_columns = selected_columns
    st.session_state.saved_filters = filter_values
    st.session_state.saved_charts = selected_charts

    if user_has_paid:
        st.success("✅ You already have an active payment.")
    else:
        # Ensure user_id exists
        user_has_paid = False

        # Prepare report payload
        report_payload = {
            "report_group": selected_group,
            "filters": filter_values,
            "charts": selected_charts,
            "created_at": datetime.now().isoformat(),
        }

        try:
            # STEP 6: Create invoice record with PENDING status
            invoice_ref = create_invoice_record(
                user_id=user_id,
                total=int(SUBSCRIPTION_AMOUNT),
                data_dict=report_payload,
            )

            if not invoice_ref:
                st.error("Failed to create invoice. Please try again.")
                st.stop()

            st.session_state.invoice_ref = invoice_ref
            st.session_state.pending_invoice_saved = True

            # Generate pending invoice PDF
            pdf_path = generate_invoice_pdf(
                invoice_ref=invoice_ref,
                user_email=user_email,
                amount=SUBSCRIPTION_AMOUNT,
                description=f"Custom Report - {selected_group}",
                selected_group=selected_group,
                selected_columns=selected_columns,
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
            <p><b>Report Group:</b> {selected_group}</p>
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

            for col in selected_columns:
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

            # STEP 5: Download pending invoice
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "📄 Download Pending Invoice PDF",
                    f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    key="pending_invoice_download",
                )

            st.info("✅ Invoice saved to database. Proceed to payment below ⬇️")

        except Exception as e:
            st.error(f"Error creating invoice: {str(e)}")
            st.stop()

# ============================================================
# STEP 7: PROCEED TO PAYMENT
# ============================================================
if st.session_state.invoice_ref and not st.session_state.payment_verified:
    st.markdown("---")
    st.subheader("💳 Payment Gateway")
    
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
                    attach_paystack_ref_to_invoice(st.session_state.invoice_ref, paystack_ref)

                    checkout_url = api_response.get("authorization_url")
                    components.html(f"<script>window.open('{checkout_url}', '_blank');</script>")
                    st.success("✅ Paystack checkout opened in a new tab.")
                    st.warning("⚠️ After payment, return here and click **Verify My Payment** below.")
                else:
                    st.error("Failed to connect to Paystack. Please try again.")
            except Exception as e:
                st.error(f"Payment initialization error: {str(e)}")

# ============================================================
# STEP 8: VERIFY PAYMENT
# ============================================================
if st.session_state.paystack_reference and not st.session_state.payment_verified:
    st.markdown("---")
    st.subheader("✔️ Verify Payment")

    if st.button("Verify My Payment", type="primary", key="verify_btn"):
        paystack_ref = st.session_state.get("paystack_reference")
        
        if not paystack_ref:
            st.error("No payment reference found. Please click 'Proceed to Payment' first.")
            st.stop()

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
                    
                    # STEP 9: Mark invoice as PAID
                    mark_invoice_paid_by_paystack_ref(paystack_ref)
                    
                    st.success("✅ Payment verified successfully!")
                    st.rerun()
                else:
                    st.error("❌ Payment verification failed. Please contact support if payment was deducted.")
                    st.stop()
            except Exception as e:
                st.error(f"Verification error: {str(e)}")
                st.stop()

# ============================================================
# POST-PAYMENT: SHOW PAID INVOICE + SAVE REPORT + LOAD DATA
# ============================================================
if st.session_state.payment_verified and st.session_state.invoice_ref:
    
    # ========================================
    # STEP 1: PREPARE SAVED VALUES
    # ========================================
    saved_group = st.session_state.get("saved_group")
    saved_columns = st.session_state.get("saved_columns", [])
    saved_filters = st.session_state.get("saved_filters", {})
    saved_charts = st.session_state.get("saved_charts", [])
    invoice_ref = st.session_state.invoice_ref
    
    if not saved_group:
        st.error("❌ Report configuration lost. Please start over.")
        st.stop()
    
    # ========================================
    # APPLY FILTERS (PANDAS — NO DB)
    # ========================================
    with st.spinner("🔄 Preparing report data..."):
        filtered_df = df.copy()

        for col, values in saved_filters.items():
            if col == "Age":
               age_mask = False
               if "Below 18" in values:
                   age_mask |= filtered_df["Age"] < 18
               if "Above 18" in values:
                   age_mask |= filtered_df["Age"] >= 18
               filtered_df = filtered_df[age_mask]

            elif "All" not in values:
                filtered_df = filtered_df[filtered_df[col].isin(values)]

        if filtered_df.empty:
            st.warning("⚠️ No data matches your filters.")
            st.session_state.filtered_df = None
            st.session_state.report_ready = False
        else:
            st.session_state.filtered_df = filtered_df
            st.session_state.report_ready = True
            st.success(f"✅ Loaded {len(filtered_df):,} records!")
    
    # ========================================
    # STEP 4: GENERATE PAID INVOICE PDF (Once)
    # ========================================
    if not st.session_state.get("paid_pdf_generated", False):
        try:
            paid_pdf_path = generate_invoice_pdf(
                invoice_ref=invoice_ref,
                user_email=user_email,
                amount=SUBSCRIPTION_AMOUNT,
                description=f"Custom Report - {saved_group}",
                selected_group=saved_group,
                selected_columns=saved_columns,
                status="PAID ✅",
            )
            st.session_state.paid_pdf_path = paid_pdf_path
            st.session_state.paid_pdf_generated = True
        except Exception as e:
            st.error(f"❌ Error generating invoice PDF: {str(e)}")
            st.stop()
    
    # ========================================
    # STEP 5: DISPLAY PAID INVOICE
    # ========================================
    st.markdown("---")
    st.subheader("✅ Payment Successful - Invoice Paid")
    
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
    
    # ========================================
    # STEP 6: ASK FOR REPORT NAME
    # ========================================
    st.markdown("---")
    st.subheader("📝 Name Your Report")
    
    default_report_name = f"{saved_group} Report - {datetime.now().strftime('%b %d, %Y')}"
    
    report_name = st.text_input(
        "Enter a name for your report:",
        value=default_report_name,
        key="report_name_input"
    )
    
# ========================================
# STEP 7: SAVE REPORT TO DATABASE
# ========================================
    if not st.session_state.get("report_saved", False):

        if st.button("💾 Save Report", type="primary"):

            if not report_name.strip():
                st.error("❌ Report name cannot be empty.")
            else:
                try:
                    save_user_report(
                        user_id=user_id,
                        invoice_ref=invoice_ref,
                        report_group=saved_group,
                        report_name=report_name.strip(),
                        filters=saved_filters,
                        charts=saved_charts,
                        pdf_path=st.session_state.paid_pdf_path
                    )
                    st.session_state.report_saved = True
                    st.success("✅ Report saved successfully!")
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Failed to save report: {str(e)}")

    else:
        st.success("✅ Report already saved to your account!")
    
    # ========================================
    # STEP 8: DOWNLOAD & VIEW BUTTONS
    # ========================================
        st.markdown("---")
    
        col1, col2 = st.columns(2)
    
        with col1:
            with open(st.session_state.paid_pdf_path, "rb") as f:
                st.download_button(
                    "📄 Download Invoice PDF",
                    f,
                    file_name=os.path.basename(st.session_state.paid_pdf_path),
                    mime="application/pdf",
                    key="download_paid_invoice"
                )
    
        with col2:
            if st.button("📊 View Report", type="primary", key="view_report_btn"):
               st.switch_page("pages/view_report.py")
    
        st.info("🗂️ Your report is saved for 30 days in your account.")
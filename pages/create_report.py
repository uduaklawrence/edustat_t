import streamlit as st
import json
from datetime import datetime
import base64
import pandas as pd 
from Analytics_layer import get_exam_dataset
from db_queries import (
    update_payment_status,
    create_invoice_record,
)
from paystack import initialize_transaction, verify_transaction
from invoice_pdf import generate_invoice_pdf

# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # ₦

# ------------------ AUTH CHECK ------------------
if not st.session_state.get("logged_in", False):
    st.warning("Please sign in to view the report.")
    st.stop()

st.set_page_config(page_title="Create Report", layout="wide")

# Load existing CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional CSS for report selection UI
st.markdown("""
<style>
    /* Header Section */
    .report-selection-header {
        text-align: center;
        margin-bottom: 40px;
    }
    
    .report-selection-title {
        font-size: 36px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }
    
    .report-selection-subtitle {
        font-size: 18px;
        color: var(--text-secondary);
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Group Tabs */
    .group-tabs-container {
        display: flex;
        gap: 12px;
        margin: 40px 0 30px 0;
        flex-wrap: wrap;
        justify-content: center;
    }
    
    .group-tab {
        background: white;
        padding: 14px 28px;
        border-radius: 8px;
        border: 2px solid var(--border-light);
        cursor: pointer;
        font-weight: 600;
        color: var(--text-secondary);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 15px;
    }
    
    .group-tab:hover {
        border-color: var(--primary-blue);
        color: var(--primary-blue);
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    
    .group-tab.active {
        background: var(--primary-navy);
        color: white;
        border-color: var(--primary-navy);
        box-shadow: 0 4px 12px rgba(30, 39, 73, 0.3);
    }
    
    /* Subgroup Cards */
    .subgroup-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 24px;
        margin-top: 40px;
    }
    
    .subgroup-card {
        background: white;
        border-radius: 12px;
        padding: 28px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        min-height: 280px;
    }
    
    .subgroup-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-4px);
        border-color: var(--accent-blue);
    }
    
    .subgroup-card-title {
        font-size: 20px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 16px;
        min-height: 52px;
        display: flex;
        align-items: center;
    }
    
    .subgroup-card-description {
        color: var(--text-secondary);
        font-size: 15px;
        line-height: 1.6;
        flex-grow: 1;
        margin-bottom: 20px;
    }
    
    /* Explore Button */
    div[data-testid="stButton"] button.explore-btn {
        background-color: var(--primary-navy) !important;
        color: white !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        font-size: 15px !important;
    }
    
    div[data-testid="stButton"] button.explore-btn:hover {
        background-color: var(--primary-blue) !important;
        box-shadow: 0 4px 12px rgba(30, 39, 73, 0.3) !important;
        transform: translateY(-2px) !important;
    }
</style>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)


# ------------------ LOAD ANALYTICS DATA (REDIS ONLY) ------------------

@st.cache_data(show_spinner=False)
def load_dataset():
    return get_exam_dataset()

df = load_dataset()

# ------------------ SESSION DEFAULTS ------------------
st.session_state.setdefault("selected_main_group", None)
st.session_state.setdefault("selected_subgroup", None)
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

# ========================================
# GENERATE REPORT DESCRIPTION (Preview)
# ========================================
if selected_columns and selected_charts:
    # Generate description using CURRENT selections
    report_description = generate_report_description(
        report_group=selected_group,
        filters=filter_values,
        charts=selected_charts
    )

    st.markdown("---")
    st.subheader("📄 Report Description Preview")

    with st.expander("📋 View Full Description", expanded=False):
        st.markdown(report_description)
        st.caption("ℹ️ This description will be included in your invoice.")
else:
    report_description = "Report description will be generated based on your selections."


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
        # Save all selections to session state
        st.session_state.saved_group = selected_group
        st.session_state.saved_columns = selected_columns
        st.session_state.saved_filters = filter_values
        st.session_state.saved_charts = selected_charts
        st.session_state.saved_description = report_description
        st.session_state.payment_verified = True
        
        # Navigate to invoice page
        st.switch_page("pages/view_invoice.py")
    else:
        # Ensure user_id exists
        user_has_paid = False

        # Prepare report payload
        report_payload = {
            "report_group": selected_group,
            "filters": filter_values,
            "charts": selected_charts,
            "columns": selected_columns,
            "description": report_description,
            "created_at": datetime.now().isoformat(),
        }

        try:
            # Create invoice record with PENDING status
            invoice_ref = create_invoice_record(
                user_id=user_id,
                total=int(SUBSCRIPTION_AMOUNT),
                data_dict=report_payload,
            )

            if not invoice_ref:
                st.error("Failed to create invoice. Please try again.")
                st.stop()

            # Save all selections to session state
            st.session_state.invoice_ref = invoice_ref
            st.session_state.saved_group = selected_group
            st.session_state.saved_columns = selected_columns
            st.session_state.saved_filters = filter_values
            st.session_state.saved_charts = selected_charts
            st.session_state.saved_description = report_description
            st.session_state.pending_invoice_saved = True
            st.session_state.payment_verified = False

            st.success("✅ Invoice created successfully!")
            st.info("Redirecting to invoice page...")
            
            # Navigate to invoice page
            st.switch_page("pages/view_invoice.py")

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

# ==============================
# 📊 CREATE REPORT - CORRECTED VERSION
# ==============================

import streamlit as st
import streamlit.components.v1 as components
import os
import json
import time
from datetime import datetime, timedelta
import base64
from db_queries import (
    fetch_data,
    update_payment_status,
    create_invoice_record,
    attach_paystack_ref_to_invoice,
    mark_invoice_paid_by_paystack_ref,
    save_user_report,
)
from redis_cache import get_or_set_distinct_values
from paystack import initialize_transaction, verify_transaction
from invoice_pdf import generate_invoice_pdf

# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # ₦
WATERMARK_PATH = r"altered_edustat.jpg"

def get_base64_image(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def generate_report_description(report_group, filters, charts):
    """
    Generates a human-readable report description
    based on report group, filters, and charts.
    """

    years = filters.get("ExamYear", [])
    states = filters.get("State", [])
    centres = filters.get("Centre", [])
    sponsors = filters.get("Sponsor", [])
    genders = filters.get("Sex", [])
    disabilities = filters.get("Disability", [])

    age_desc = ""
    if "Age" in filters:
        age_desc = "with age groups (Under 18 and 18 & above)"

    year_text = ", ".join(map(str, years)) if years else "the selected years"
    chart_text = ", ".join(charts).lower() if charts else "tabular views"

    if report_group == "Geographic & Institutional Insights":
        return f"""
This report shows the number of candidates registered across selected states and examination centres
for school examinations conducted in {year_text}.

The analysis focuses on institutions in {", ".join(states) if states else "the selected states"},
considering gender distribution, special needs status, and candidate age categories {age_desc}.

This report contains tables, statistical summaries (mean, minimum, maximum, variance, and standard deviation),
and visualizations including {chart_text}. The primary chart places states or centres on the horizontal axis
to enable comparison of candidate volumes.
""".strip()

    if report_group == "Demographic Analysis":
        return f"""
This report provides a demographic breakdown of candidates registered for school examinations
during {year_text}.

The analysis examines gender, disability status, and age group distributions {age_desc},
highlighting patterns across candidate populations.

The report includes tables, summary statistics, and visualizations such as {chart_text},
with interpretation guidance provided beneath each chart.
""".strip()

    if report_group == "Equity & Sponsorship":
        return f"""
This report analyses sponsorship participation and equity distribution in school examinations
across {year_text}.

The focus is on sponsor categories, gender inclusion, and special needs representation.
Tables, statistical summaries, and {chart_text} are used to visualize sponsorship reach
and demographic balance.
""".strip()

    if report_group == "Temporal & Progression Trends":
        return f"""
This report evaluates candidate registration trends over time, highlighting progression
patterns across {year_text}.

The analysis uses statistical indicators and visualizations such as {chart_text}
to identify growth patterns, fluctuations, and long-term participation trends.
""".strip()

    return "This report provides analytical insights based on the selected parameters."


# ------------------ AUTH CHECK ------------------
if not st.session_state.get("logged_in", False):
    st.warning("Please sign in to view the report.")
    st.stop()

st.set_page_config(page_title="Create Report", layout="wide")
st.title("📊 Create Custom Reports")

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# ------------------ SESSION DEFAULTS ------------------
st.session_state.setdefault("paystack_reference", None)
st.session_state.setdefault("invoice_ref", None)
st.session_state.setdefault("payment_verified", False)
st.session_state.setdefault("saved_group", None)
st.session_state.setdefault("saved_columns", None)
st.session_state.setdefault("saved_filters", None)
st.session_state.setdefault("saved_charts", None)
st.session_state.setdefault("saved_where_clause", None)
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

# ------------------ FILTERS CACHE ------------------

def fetch_distinct_from_db(column):
    df = fetch_data(f"SELECT DISTINCT {column} FROM exam_candidates")
    return df[column].dropna().tolist()

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
        
        ages = fetch_data(
            "SELECT DISTINCT TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age FROM exam_candidates"
        )["Age"].tolist()
        
        # Filter ages based on selected groups
        selected_ages = []
        if "Below 18" in selected_age_groups:
            selected_ages.extend([age for age in ages if age < 18])
        if "Above 18" in selected_age_groups:
            selected_ages.extend([age for age in ages if age >= 18])
        
        filter_values["Age"] = selected_ages if selected_ages else ages
    else:
        cache_key = f"distinct:{col}"

        distinct_vals = get_or_set_distinct_values(cache_key,lambda: fetch_distinct_from_db(col))
        filter_values[col] = st.multiselect(f"{col}:", ["All"] + distinct_vals, default=["All"])

# ------------------ BUILD WHERE CLAUSE ------------------
filters = []
for col, values in filter_values.items():
    if "All" not in values:
        if col == "Age":
            # Create WHERE clause for age based on selected ranges
            if "Below 18" in selected_age_groups and "Above 18" in selected_age_groups:
                filters.append(
                    f"(TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) < 18 OR TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) >= 18)"
                )
            elif "Below 18" in selected_age_groups:
                filters.append(
                    f"TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) < 18"
                )
            elif "Above 18" in selected_age_groups:
                filters.append(
                    f"TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) >= 18"
                )
        else:
            value_list = ", ".join(f"'{v}'" for v in values)
            filters.append(f"{col} IN ({value_list})")

where_clause = " AND ".join(filters) if filters else "1=1"

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
    # Check existing payment status
    payment_df = fetch_data(f"SELECT payment FROM users WHERE email_address='{user_email}'")
    user_has_paid = not payment_df.empty and payment_df["payment"].values[0]
    
    if st.session_state.payment_verified:
        user_has_paid = True

    # Save all selections to session state
        st.session_state.saved_group = selected_group
        st.session_state.saved_columns = selected_columns
        st.session_state.saved_filters = filter_values
        st.session_state.saved_charts = selected_charts
        st.session_state.saved_where_clause = where_clause
        st.session_state.saved_description = report_description
        st.session_state.payment_verified = True
        
        # Navigate to invoice page
        st.switch_page("pages/view_invoice.py")
    else:
        # Ensure user_id exists
        if not user_id or user_id == 0:
            user_df = fetch_data(f"SELECT user_id FROM users WHERE email_address='{user_email}' LIMIT 1")
            if not user_df.empty:
                user_id = int(user_df["user_id"].iloc[0])
                st.session_state.user_id = user_id
            else:
                st.error("User ID not found. Please re-login.")
                st.stop()

        # Prepare report payload
        report_payload = {
            "report_group": selected_group,
            "filters": filter_values,
            "charts": selected_charts,
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
            st.session_state.saved_where_clause = where_clause
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
   
   
   
#     # Save selections to session state
#     st.session_state.saved_group = selected_group
#     st.session_state.saved_columns = selected_columns
#     st.session_state.saved_filters = filter_values
#     st.session_state.saved_charts = selected_charts
#     st.session_state.saved_where_clause = where_clause
#     st.session_state.saved_description = report_description  # ← ADD THIS LINE

#     if user_has_paid:
#         st.success("✅ You already have an active payment.")
#     else:
#         # Ensure user_id exists
#         if not user_id or user_id == 0:
#             user_df = fetch_data(f"SELECT user_id FROM users WHERE email_address='{user_email}' LIMIT 1")
#             if not user_df.empty:
#                 user_id = int(user_df["user_id"].iloc[0])
#                 st.session_state.user_id = user_id
#             else:
#                 st.error("User ID not found. Please re-login.")
#                 st.stop()

#         # Prepare report payload
#         report_payload = {
#             "report_group": selected_group,
#             "filters": filter_values,
#             "charts": selected_charts,
#             "created_at": datetime.now().isoformat(),
#         }

#         try:
#             # STEP 6: Create invoice record with PENDING status
#             invoice_ref = create_invoice_record(
#                 user_id=user_id,
#                 total=int(SUBSCRIPTION_AMOUNT),
#                 data_dict=report_payload,
#             )

#             if not invoice_ref:
#                 st.error("Failed to create invoice. Please try again.")
#                 st.stop()

#             st.session_state.invoice_ref = invoice_ref
#             st.session_state.pending_invoice_saved = True

#             # Generate pending invoice PDF
#             pdf_path = generate_invoice_pdf(
#                 invoice_ref=invoice_ref,
#                 user_email=user_email,
#                 amount=SUBSCRIPTION_AMOUNT,
#                 description=report_description,  # ← USE THE GENERATED DESCRIPTION
#                 selected_group=selected_group,
#                 selected_columns=selected_columns,
#                 status="Pending Payment",
#             )

#             # Display pending invoice with watermark
#             watermark_base64 = get_base64_image(WATERMARK_PATH)
#             user_display = user_email.split("@")[0].replace(".", " ").title()
#             invoice_date = datetime.now().strftime("%B %d, %Y")

#             invoice_html = f"""
#             <h2 style="text-align:center;">INVOICE</h2>
#             <p><b>Name:</b> {user_display}</p>
#             <p><b>Invoice No:</b> {invoice_ref}</p>
#             <p><b>Date:</b> {invoice_date}</p>
#             <p><b>Report Group:</b> {selected_group}</p>
#             <p><b>Report Description:</b></p>
#             <p>{report_description}</p>
#             <hr>
#             <table style="width:100%; border-collapse:collapse;">
#                 <thead>
#                     <tr style="background-color:#f2f2f2;">
#                         <th style="padding:8px; border:1px solid #ddd;">Item</th>
#                         <th style="padding:8px; border:1px solid #ddd;">Qty</th>
#                         <th style="padding:8px; border:1px solid #ddd;">Amount (₦)</th>
#                     </tr>
#                 </thead>
#                 <tbody>
#             """

#             for col in selected_columns:
#                 invoice_html += f"""
#                 <tr>
#                     <td style="padding:8px; border:1px solid #ddd;">{col}</td>
#                     <td style="padding:8px; border:1px solid #ddd;">1</td>
#                     <td style="padding:8px; border:1px solid #ddd;">-</td>
#                 </tr>
#                 """

#             invoice_html += f"""
#                 <tr>
#                     <td colspan="2" style="text-align:right; padding:8px; border:1px solid #ddd;"><b>Total</b></td>
#                     <td style="padding:8px; border:1px solid #ddd;"><b>₦{SUBSCRIPTION_AMOUNT:,.2f}</b></td>
#                 </tr>
#                 </tbody>
#             </table>
#             <p><b>Status:</b> Pending Payment ⏳</p>
#             """

#             container = f"""
#             <div style="
#                 background:white;
#                 padding:25px;
#                 border-radius:10px;
#                 box-shadow:0 0 10px rgba(0,0,0,0.1);
#                 background-image:url('data:image/jpeg;base64,{watermark_base64}');
#                 background-repeat:no-repeat;
#                 background-position:center;
#                 background-size:45%;
#             ">{invoice_html}</div>
#             """

#             components.html(container, height=680, scrolling=True)

#             # STEP 5: Download pending invoice
#             with open(pdf_path, "rb") as f:
#                 st.download_button(
#                     "📄 Download Pending Invoice PDF",
#                     f,
#                     file_name=os.path.basename(pdf_path),
#                     mime="application/pdf",
#                     key="pending_invoice_download",
#                 )

#             st.info("✅ Invoice saved to database. Proceed to payment below ⬇️")

#         except Exception as e:
#             st.error(f"Error creating invoice: {str(e)}")
#             st.stop()

# # ============================================================
# # STEP 7: PROCEED TO PAYMENT
# # ============================================================
# if st.session_state.invoice_ref and not st.session_state.payment_verified:
#     st.markdown("---")
#     st.subheader("💳 Payment Gateway")
    
#     if st.button("Proceed to Payment", type="primary", key="pay_btn"):
#         with st.spinner("Connecting to Paystack..."):
#             try:
#                 api_response = initialize_transaction(
#                     email_address=user_email, 
#                     amount=SUBSCRIPTION_AMOUNT
#                 )
                
#                 if api_response and api_response.get("authorization_url"):
#                     paystack_ref = api_response.get("reference")
#                     st.session_state.paystack_reference = paystack_ref
                    
#                     # Attach paystack reference to invoice
#                     attach_paystack_ref_to_invoice(st.session_state.invoice_ref, paystack_ref)

#                     checkout_url = api_response.get("authorization_url")
#                     components.html(f"<script>window.open('{checkout_url}', '_blank');</script>")
#                     st.success("✅ Paystack checkout opened in a new tab.")
#                     st.warning("⚠️ After payment, return here and click **Verify My Payment** below.")
#                 else:
#                     st.error("Failed to connect to Paystack. Please try again.")
#             except Exception as e:
#                 st.error(f"Payment initialization error: {str(e)}")

# # ============================================================
# # STEP 8: VERIFY PAYMENT
# # ============================================================
# if st.session_state.paystack_reference and not st.session_state.payment_verified:
#     st.markdown("---")
#     st.subheader("✔️ Verify Payment")

#     if st.button("Verify My Payment", type="primary", key="verify_btn"):
#         paystack_ref = st.session_state.get("paystack_reference")
        
#         if not paystack_ref:
#             st.error("No payment reference found. Please click 'Proceed to Payment' first.")
#             st.stop()

#         with st.spinner("Verifying payment with Paystack..."):
#             try:
#                 verification_response = verify_transaction(paystack_ref)

#                 if (
#                     verification_response
#                     and verification_response.get("status") is True
#                     and verification_response.get("data", {}).get("status") == "success"
#                 ):
#                     # Update payment status in users table
#                     update_payment_status(user_email)
#                     st.session_state.payment_verified = True
                    
#                     # STEP 9: Mark invoice as PAID
#                     mark_invoice_paid_by_paystack_ref(paystack_ref)
                    
#                     st.success("✅ Payment verified successfully!")
#                     st.rerun()
#                 else:
#                     st.error("❌ Payment verification failed. Please contact support if payment was deducted.")
#                     st.stop()
#             except Exception as e:
#                 st.error(f"Verification error: {str(e)}")
#                 st.stop()

# # ============================================================
# # POST-PAYMENT: SHOW PAID INVOICE + SAVE REPORT + LOAD DATA
# # ============================================================
# if st.session_state.payment_verified and st.session_state.invoice_ref:
    
#     # ========================================
#     # STEP 1: PREPARE SAVED VALUES
#     # ========================================
#     saved_group = st.session_state.get("saved_group")
#     saved_columns = st.session_state.get("saved_columns", [])
#     saved_filters = st.session_state.get("saved_filters", {})
#     saved_charts = st.session_state.get("saved_charts", [])
#     saved_where = st.session_state.get("saved_where_clause", "1=1")
#     invoice_ref = st.session_state.invoice_ref
    
#     if not saved_group:
#         st.error("❌ Report configuration lost. Please start over.")
#         st.stop()
    
#     # ========================================
#     # STEP 2: BUILD REPORT QUERY
#     # ========================================
#     if saved_group == "Demographic Analysis":
#         report_query = f"""
#         SELECT ExamYear, Sex, Disability,
#                TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age
#         FROM exam_candidates
#         WHERE {saved_where}
#         """
#     elif saved_group == "Geographic & Institutional Insights":
#         report_query = f"""
#         SELECT ExamYear, State, Centre
#         FROM exam_candidates
#         WHERE {saved_where}
#         """
#     elif saved_group == "Equity & Sponsorship":
#         report_query = f"""
#         SELECT ExamYear, Sponsor, Sex, Disability
#         FROM exam_candidates
#         WHERE {saved_where}
#         """
#     elif saved_group == "Temporal & Progression Trends":
#         report_query = f"""
#         SELECT ExamYear
#         FROM exam_candidates
#         WHERE {saved_where}
#         """
#     else:
#         report_query = f"SELECT * FROM exam_candidates WHERE {saved_where}"
    
#     # ========================================
#     # STEP 3: LOAD DATA (Once)
#     # ========================================
#     if not st.session_state.get("data_loaded", False):
#         with st.spinner("🔄 Loading report data..."):
#             try:
#                 filtered_df = fetch_data(report_query)
                
#                 if filtered_df.empty:
#                     st.warning("⚠️ No data matches your filters.")
#                     st.session_state.filtered_df = None
#                     st.session_state.report_ready = False
#                 else:
#                     st.session_state.filtered_df = filtered_df
#                     st.session_state.data_loaded = True
#                     st.session_state.report_ready = True
#                     st.success(f"✅ Loaded {len(filtered_df):,} records!")
#             except Exception as e:
#                 st.error(f"❌ Error loading data: {str(e)}")
#                 st.session_state.report_ready = False
#                 st.stop()
    
#     # ========================================
#     # STEP 4: GENERATE PAID INVOICE PDF (Once)
#     # ========================================
#     if not st.session_state.get("paid_pdf_generated", False):
#         try:
#             paid_pdf_path = generate_invoice_pdf(
#                 invoice_ref=invoice_ref,
#                 user_email=user_email,
#                 amount=SUBSCRIPTION_AMOUNT,
#                 description=f"Custom Report - {saved_group}",
#                 selected_group=saved_group,
#                 selected_columns=saved_columns,
#                 status="PAID ✅",
#             )
#             st.session_state.paid_pdf_path = paid_pdf_path
#             st.session_state.paid_pdf_generated = True
#         except Exception as e:
#             st.error(f"❌ Error generating invoice PDF: {str(e)}")
#             st.stop()
    
#     # ========================================
#     # STEP 5: DISPLAY PAID INVOICE
#     # ========================================
#     st.markdown("---")
#     st.subheader("✅ Payment Successful - Invoice Paid")
    
#     watermark_base64 = get_base64_image(WATERMARK_PATH)
#     user_display = user_email.split("@")[0].replace(".", " ").title()
#     invoice_date = datetime.now().strftime("%B %d, %Y")
    
#     paid_html = f"""
#     <h2 style="text-align:center;">INVOICE</h2>
#     <p><b>Name:</b> {user_display}</p>
#     <p><b>Invoice No:</b> {invoice_ref}</p>
#     <p><b>Date:</b> {invoice_date}</p>
#     <p><b>Report Group:</b> {saved_group}</p>
#     <hr>
#     <table style="width:100%; border-collapse:collapse;">
#         <thead>
#             <tr style="background-color:#f2f2f2;">
#                 <th style="padding:8px; border:1px solid #ddd;">Item</th>
#                 <th style="padding:8px; border:1px solid #ddd;">Qty</th>
#                 <th style="padding:8px; border:1px solid #ddd;">Amount (₦)</th>
#             </tr>
#         </thead>
#         <tbody>
#     """
    
#     for col in saved_columns:
#         paid_html += f"""
#         <tr>
#             <td style="padding:8px; border:1px solid #ddd;">{col}</td>
#             <td style="padding:8px; border:1px solid #ddd;">1</td>
#             <td style="padding:8px; border:1px solid #ddd;">-</td>
#         </tr>
#         """
    
#     paid_html += f"""
#         <tr>
#             <td colspan="2" style="text-align:right; padding:8px; border:1px solid #ddd;"><b>Total</b></td>
#             <td style="padding:8px; border:1px solid #ddd;"><b>₦{SUBSCRIPTION_AMOUNT:,.2f}</b></td>
#         </tr>
#         </tbody>
#     </table>
#     <p><b>Status:</b> PAID ✅</p>
#     """
    
#     container_paid = f"""
#     <div style="
#         background:white;
#         padding:25px;
#         border-radius:10px;
#         box-shadow:0 0 10px rgba(0,0,0,0.1);
#         background-image:url('data:image/jpeg;base64,{watermark_base64}');
#         background-repeat:no-repeat;
#         background-position:center;
#         background-size:45%;
#     ">{paid_html}</div>
#     """
    
#     components.html(container_paid, height=680, scrolling=True)
    
#     # ========================================
#     # STEP 6: ASK FOR REPORT NAME
#     # ========================================
#     st.markdown("---")
#     st.subheader("📝 Name Your Report")
    
#     default_report_name = f"{saved_group} Report - {datetime.now().strftime('%b %d, %Y')}"
    
#     report_name = st.text_input(
#         "Enter a name for your report:",
#         value=default_report_name,
#         key="report_name_input"
#     )
    
#     # ========================================
# # STEP 7: SAVE REPORT TO DATABASE
# # ========================================
# if not st.session_state.get("report_saved", False):
#     if st.button("💾 Save Report", type="primary"):
#         if not report_name.strip():
#             st.error("❌ Report name cannot be empty.")
#         else:
#             try:
#                 save_user_report(
#                     user_id=st.session_state.user_id,
#                     invoice_ref=invoice_ref,
#                     report_group=saved_group,
#                     report_name=report_name.strip(),
#                     filters=saved_filters,
#                     charts=saved_charts,
#                     pdf_path=st.session_state.paid_pdf_path
#                 )
#                 st.session_state.report_saved = True
#                 st.session_state.report_ready = True  # ← ADD THIS CRITICAL LINE
#                 st.success("✅ Report saved successfully!")
#                 st.balloons()
#             except Exception as e:
#                 st.error(f"❌ Failed to save report: {str(e)}")
# else:
#     st.success("✅ Report already saved to your account!")
#     st.session_state.report_ready = True  # ← ALSO SET HERE FOR ALREADY SAVED REPORTS
    
#     # ========================================
#     # STEP 8: DOWNLOAD & VIEW BUTTONS
#     # ========================================
#     st.markdown("---")
    
#     col1, col2 = st.columns(2)
    
#     with col1:
#         with open(st.session_state.paid_pdf_path, "rb") as f:
#             st.download_button(
#                 "📄 Download Invoice PDF",
#                 f,
#                 file_name=os.path.basename(st.session_state.paid_pdf_path),
#                 mime="application/pdf",
#                 key="download_paid_invoice"
#             )
    
#     with col2:
#         if st.button("📊 View Report", type="primary", key="view_report_btn"):
#             st.switch_page("pages/view_report.py")
    
#     st.info("🗂️ Your report is saved for 30 days in your account.")
# ==============================
# 📊 CREATE REPORT (Invoice + Proceed to Payment + Watermark)
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
from paystack import initialize_transaction, verify_transaction
from invoice_pdf import generate_invoice_pdf  # ✅ make sure this file exists

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

# ------------------ SESSION DEFAULTS ------------------
st.session_state.setdefault("paystack_reference", None)
st.session_state.setdefault("invoice_ref", None)
st.session_state.setdefault("payment_verified", False)
st.session_state.setdefault("saved_group", None)
st.session_state.setdefault("saved_columns", None)
st.session_state.setdefault("saved_filters", None)
st.session_state.setdefault("saved_charts", None)
st.session_state.setdefault("saved_where_clause", None)
st.session_state.setdefault("invoice_downloaded", False)

# ------------------ INSIGHT GROUP SELECTION ------------------
insight_groups = [
    "Demographic Analysis",
    "Geographic & Institutional Insights",
    "Equity & Sponsorship",
    "Temporal & Progression Trends",
]
selected_group = st.selectbox("Select Insight Group", insight_groups)

# ------------------ COLUMN SELECTION ------------------
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

# ------------------ CACHING DISTINCT VALUES ------------------
 
@st.cache_data
def get_distinct_values(col):
    query = f"SELECT DISTINCT {col} FROM exam_candidates"
    return fetch_data(query)[col].dropna().tolist()

# ------------------ FILTERS ------------------
st.subheader("Apply Filters")

filter_values = {}
for col in selected_columns:
    if col == "Age":
        # Define age groups
        age_groups = ["Below 18", "Above 18"]

        # Allow users to select age groups (Below 18 or Above 18)
        selected_age_groups = st.multiselect(
            "Select Age Groups:",
            age_groups,
            default=age_groups  # Default to both groups selected
        )
        ages = fetch_data(
            "SELECT DISTINCT TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age FROM exam_candidates"
        )["Age"].tolist()
        # Now filter the ages based on selected groups
        selected_ages = []
        if "Below 18" in selected_age_groups:
            selected_ages.extend([age for age in ages if age < 18])
        if "Above 18" in selected_age_groups:
            selected_ages.extend([age for age in ages if age >= 18])
             # If no groups are selected, default to all ages
        filter_values["Age"] = selected_ages if selected_ages else ages
    else:
        distinct_vals = fetch_data(f"SELECT DISTINCT {col} FROM exam_candidates")[col].dropna().tolist()
        filter_values[col] = st.multiselect(f"{col}:", ["All"] + distinct_vals, default=["All"])

# ------------------ BUILD WHERE CLAUSE ------------------
filters = []
for col, values in filter_values.items():
    if "All" not in values:
        if col == "Age":
             # Create the WHERE clause for age based on selected ranges
            if "Below 18" in selected_age_groups and "Above 18" in selected_age_groups:
                filters.append(
                    f"TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) < 18 OR TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) >= 18"
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
# 🔍 SHOW PREVIEW
# ============================================================
st.markdown("---")
st.subheader("👀 Data Preview")

if st.button("Show Preview"):
    if selected_group == "Demographic Analysis":
        preview_query = f"""
        SELECT Sex, Disability,
               TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age,
               COUNT(*) AS Candidates
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY Sex, Disability, Age
        ORDER BY Age ASC
        LIMIT 10
        """

    elif selected_group == "Geographic & Institutional Insights":
        preview_query = f"""
        SELECT State, Centre, COUNT(*) AS Candidates
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY State, Centre
        ORDER BY Candidates DESC
        LIMIT 10
        """

    elif selected_group == "Equity & Sponsorship":
        preview_query = f"""
        SELECT Sponsor, Sex, Disability, COUNT(*) AS Candidates
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY Sponsor, Sex, Disability
        ORDER BY Candidates DESC
        LIMIT 10
        """

    elif selected_group == "Temporal & Progression Trends":
        preview_query = f"""
        SELECT ExamYear, COUNT(*) AS Candidates
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY ExamYear
        ORDER BY Candidates DESC
        LIMIT 10
        """

    else:
        preview_query = f"""
        SELECT ExamYear, COUNT(*) AS Count
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY ExamYear
        LIMIT 10
        """

    preview_df = fetch_data(preview_query)

    if preview_df.empty:
        st.warning("No data matches your filter selection.")
    else:
        st.dataframe(preview_df, use_container_width=True)

# ============================================================
# CHART TYPE SELECTION
# ============================================================
st.markdown("---")
st.subheader("Select Chart Types")
chart_options = ["Table/Matrix", "Bar Chart", "Pie Chart", "Line Chart"]
selected_charts = st.multiselect("Select chart(s):", chart_options, default=["Table/Matrix"])

# ============================================================
# 1️⃣ GENERATE REPORT → CREATE INVOICE
# ============================================================
st.markdown("---")
st.subheader("🧾 Generate Invoice for This Report")

if st.button("Generate Invoice", type="primary"):
    payment_df = fetch_data(f"SELECT payment FROM users WHERE email_address='{user_email}'")
    user_has_paid = not payment_df.empty and payment_df["payment"].values[0]
    if st.session_state.payment_verified:
        user_has_paid = True

    # Save selections
    st.session_state.saved_group = selected_group
    st.session_state.saved_columns = selected_columns
    st.session_state.saved_filters = filter_values
    st.session_state.saved_charts = selected_charts
    st.session_state.saved_where_clause = where_clause

    if user_has_paid:
        st.success("✅ You already have an active payment.")
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

        report_payload = {
            "report_group": selected_group,
            "filters": filter_values,
            "charts": selected_charts,
            "created_at": datetime.now().isoformat(),
        }

        invoice_ref = create_invoice_record(
            user_id=user_id,
            total=int(SUBSCRIPTION_AMOUNT),
            data_dict=report_payload,
        )

        if invoice_ref:
            st.session_state.invoice_ref = invoice_ref

        # Generate the invoice PDF
        pdf_path = generate_invoice_pdf(
            invoice_ref=invoice_ref,
            user_email=user_email,
            amount=SUBSCRIPTION_AMOUNT,
            description=f"Custom Report - {selected_group}",
            selected_group=selected_group,
            selected_columns=selected_columns,
            status="Pending Payment",
        )

        # Render invoice with watermark (centered, not rotated)
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
        """

        invoice_html += """
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

            # ✅ Display formatted invoice in UI
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
        """
 
        invoice_html += """
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
        <p><b>Status:</b> Pending Payment</p>
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
 
        with open(pdf_path, "rb") as f:
            st.download_button(
                "📄 Download Invoice PDF",
                f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                key="pending_invoice_download",
            )
 
        st.info("Proceed to payment below ⬇️")

       
# ============================================================
# 2️⃣ PROCEED TO PAYMENT
# ============================================================
if st.session_state.invoice_ref and not st.session_state.payment_verified:
    if st.button("Proceed to Payment", type="primary", key="pay_btn"):
        with st.spinner("Connecting to Paystack..."):
            api_response = initialize_transaction(email_address=user_email, amount=SUBSCRIPTION_AMOUNT)
            if api_response and api_response.get("authorization_url"):
                paystack_ref = api_response.get("reference")
                st.session_state.paystack_reference = paystack_ref
                attach_paystack_ref_to_invoice(st.session_state.invoice_ref, paystack_ref)

                checkout_url = api_response.get("authorization_url")
                components.html(f"<script>window.open('{checkout_url}', '_blank');</script>")
                st.success("✅ Paystack checkout opened in a new tab.")
                st.warning("After payment, return and click **Verify My Payment** below.")
            else:
                st.error("Failed to connect to Paystack. Please try again.")

# ============================================================
# 3️⃣ VERIFY PAYMENT → MARK INVOICE PAID → PREP REPORT
# ============================================================
st.markdown("---")
st.subheader("✔️ Verify Payment & Access Report")

# Auto-redirect after download
if st.session_state.invoice_downloaded:
    st.success("Invoice downloaded! Redirecting...")
    time.sleep(2)
    st.switch_page("pages/view_report.py")

if st.button("Verify My Payment", type="primary", key="verify_btn"):
    paystack_ref = st.session_state.get("paystack_reference")
    if not paystack_ref:
        st.error("No payment reference found. Please click 'Proceed to Payment' first.")
        st.stop()

    with st.spinner("Verifying payment with Paystack..."):
        verification_response = verify_transaction(paystack_ref)

    if (
        verification_response
        and verification_response.get("status") is True
        and verification_response.get("data", {}).get("status") == "success"
    ):
        update_payment_status(user_email)
        st.session_state.payment_verified = True
        mark_invoice_paid_by_paystack_ref(paystack_ref)
        st.success("Payment verified!")
    else:
        st.error("Verification failed.")
        st.stop()


# SHOW PAID INVOICE + Download + View Report
# ============================================================
if st.session_state.payment_verified:
 
    # Build Paid invoice
    watermark_base64 = get_base64_image(WATERMARK_PATH)
    invoice_ref = st.session_state.invoice_ref
    invoice_date = datetime.now().strftime("%B %d, %Y")
    user_display = user_email.split("@")[0].replace(".", " ").title()
 
    pdf_path = generate_invoice_pdf(
        invoice_ref=invoice_ref,
        user_email=user_email,
        amount=SUBSCRIPTION_AMOUNT,
        description=f"Custom Report - {st.session_state.saved_group}",
        selected_group=st.session_state.saved_group,
        selected_columns=st.session_state.saved_columns,
        status="PAID ✅",
    )
 
    # HTML invoice
    paid_html = f"""
    <h2 style="text-align:center;">INVOICE</h2>
    <p><b>Name:</b> {user_display}</p>
    <p><b>Invoice No:</b> {invoice_ref}</p>
    <p><b>Date:</b> {invoice_date}</p>
    <p><b>Report Group:</b> {st.session_state.saved_group}</p>
    <hr>
    """
 
    paid_html += """
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
 
    for col in st.session_state.saved_columns:
        paid_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">{col}</td>
            <td style="padding:8px; border:1px solid #ddd;">1</td>
            <td style="padding:8px; border:1px solid #ddd;">-</td>
        </tr>
        """
 
    paid_html += f"""
        <tr>
            <td colspan="2" style="text-align:right; padding:8px;"><b>Total</b></td>
            <td style="padding:8px;"><b>₦{SUBSCRIPTION_AMOUNT:,.2f}</b></td>
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
 
 
    # ------------ Buttons ------------
    col1, col2 = st.columns(2)
 
    with col1:
        with open(pdf_path, "rb") as f:
            if st.download_button(
                "📄 Download Paid Invoice PDF",
                f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                key="paid_inv"
            ):
                st.session_state.invoice_downloaded = True
                st.rerun()
 
    with col2:
        if st.button("➡️ View Report", type="primary", key="view_report"):
            st.switch_page("pages/view_report.py")

#LOAD REPORT DATA + SAVE USER HISTORY
        saved_group = st.session_state.get("saved_group")
        saved_where = st.session_state.get("saved_where_clause")

        if saved_group == "Demographic Analysis":
            query = f"""
            SELECT ExamYear, Sex, Disability,
                   TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age
            FROM exam_candidates
            WHERE {saved_where}
            """
        elif saved_group == "Geographic & Institutional Insights":
            query = f"""
            SELECT ExamYear, State, Centre, COUNT(*) AS Count
            FROM exam_candidates
            WHERE {saved_where}
            GROUP BY State, Centre
            """
        elif saved_group == "Equity & Sponsorship":
            query = f"""
            SELECT ExamYear, Sponsor, Sex, Disability, COUNT(*) AS Count
            FROM exam_candidates
            WHERE {saved_where}
            GROUP BY Sponsor, Sex, Disability
            """
        elif saved_group == "Temporal & Progression Trends":
            query = f"""
            SELECT ExamYear, COUNT(*) AS Count
            FROM exam_candidates
            WHERE {saved_where}
            GROUP BY ExamYear
            """
        else:
            query = f"SELECT * FROM exam_candidates WHERE {saved_where}"

        # Retrieve paystack reference
        ref = st.session_state.get("paystack_reference")
        
        if not ref:
            st.error("No payment reference found.")
            st.stop()

        with st.spinner("Verifying with Paystack..."):
            res = verify_transaction(ref)

        if res and res.get("status") and res.get("data", {}).get("status") == "success":
            st.session_state.payment_verified = True
            update_payment_status(user_email)
            mark_invoice_paid_by_paystack_ref(ref)
            st.success("Payment verified!")
        else:
            st.session_state.filtered_df = df

            # ------------------ SAVE REPORT HISTORY (30 DAYS) ------------------
    save_user_report(
    st.session_state.user_id,
    invoice_ref,
    st.session_state.saved_group,
    st.session_state.saved_filters,
    st.session_state.saved_charts,
    pdf_path
)
 
    st.info("🗂️ Your report has been saved to your account. Available for 30 days.")

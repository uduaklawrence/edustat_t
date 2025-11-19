# ==============================
# 📊 CREATE REPORT (Invoice + Payment + Watermark + Save History)
# ==============================

import json
import streamlit as st
import streamlit.components.v1 as components
import os
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
from invoice_pdf import generate_invoice_pdf


# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # ₦
WATERMARK_PATH = r"C:\Users\uludoh\Desktop\edustat_t\assets\image 2.jpg"


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
defaults = {
    "paystack_reference": None,
    "invoice_ref": None,
    "payment_verified": False,
    "saved_group": None,
    "saved_columns": None,
    "saved_filters": None,
    "saved_charts": None,
    "saved_where_clause": None,
    "invoice_downloaded": False
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


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
    "Demographic Analysis": ["ExamNum", "ExamYear", "Sex", "Disability", "Age"],
    "Geographic & Institutional Insights": ["ExamNum", "ExamYear", "State", "Centre"],
    "Equity & Sponsorship": ["ExamNum", "ExamYear", "Sponsor", "Sex", "Disability"],
    "Temporal & Progression Trends": ["ExamYear"],
}

available_columns = columns_map[selected_group]

selected_columns = st.multiselect(
    "Select Columns to Filter",
    available_columns,
    default=available_columns
)


# ------------------ FILTERS ------------------
st.subheader("Apply Filters")

filter_values = {}
for col in selected_columns:
    if col == "Age":
        ages = fetch_data(
            "SELECT DISTINCT TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age "
            "FROM exam_candidates"
        )["Age"].tolist()
        filter_values[col] = st.multiselect(f"{col}:", ages, default=ages)
    else:
        distinct_vals = fetch_data(
            f"SELECT DISTINCT {col} FROM exam_candidates"
        )[col].dropna().tolist()
        filter_values[col] = st.multiselect(f"{col}:", ["All"] + distinct_vals, default=["All"])


# ------------------ BUILD WHERE CLAUSE ------------------
filters = []
for col, values in filter_values.items():
    if "All" not in values:
        if col == "Age":
            filters.append(
                f"TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) IN ({','.join(map(str, values))})"
            )
        else:
            value_list = ", ".join(f"'{v}'" for v in values)
            filters.append(f"{col} IN ({value_list})")

where_clause = " AND ".join(filters) if filters else "1=1"


# ============================================================
# 🔍 DATA PREVIEW
# ============================================================
st.markdown("---")
st.subheader("👀 Data Preview")

if st.button("Show Preview"):

    # Build selected column list
    if selected_columns:
        # Convert Age to SQL expression
        sql_columns = []
        for col in selected_columns:
            if col == "Age":
                sql_columns.append("TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age")
            else:
                sql_columns.append(col)

        column_list_sql = ", ".join(sql_columns)
    else:
        column_list_sql = "*"   # fallback

    preview_query = f"""
        SELECT {column_list_sql}
        FROM exam_candidates
        WHERE {where_clause}
        LIMIT 5;
    """

    preview_df = fetch_data(preview_query)

    if preview_df is not None and not preview_df.empty:
        st.dataframe(preview_df, use_container_width=True)
        st.caption("✅ Showing first 5 rows based on your selected columns and filters.")
    else:
        st.warning("No data matches your current selections.")

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

if st.button("Generate Report", type="primary"):
    # Check payment status
    payment_df = fetch_data(f"SELECT payment FROM users WHERE email_address='{user_email}'")
    user_has_paid = not payment_df.empty and payment_df["payment"].values[0]

    if st.session_state.payment_verified:
        user_has_paid = True

    # Save user selections in session
    st.session_state.saved_group = selected_group
    st.session_state.saved_columns = selected_columns
    st.session_state.saved_filters = filter_values
    st.session_state.saved_charts = selected_charts
    st.session_state.saved_where_clause = where_clause

    if user_has_paid:
        st.success("✅ You already have an active payment.")
    else:
        # Make sure user_id exists
        if not user_id or user_id == 0:
            user_df = fetch_data(f"SELECT user_id FROM users WHERE email_address='{user_email}' LIMIT 1")
            if not user_df.empty:
                user_id = int(user_df["user_id"].iloc[0])
                st.session_state.user_id = user_id
            else:
                st.error("User ID not found. Please re-login.")
                st.stop()

        # Create invoice record
        report_payload = {
            "report_group": selected_group,
            "filters": filter_values,
            "charts": selected_charts,
            "created_at": datetime.now().isoformat()
        }

        invoice_ref = create_invoice_record(
            user_id=user_id,
            total=int(SUBSCRIPTION_AMOUNT),
            data_dict=report_payload,
        )
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
            api_response = initialize_transaction(
                email_address=user_email,
                amount=SUBSCRIPTION_AMOUNT,
            )

        if api_response and api_response.get("authorization_url"):
            paystack_ref = api_response.get("reference")
            st.session_state.paystack_reference = paystack_ref

            attach_paystack_ref_to_invoice(
                st.session_state.invoice_ref,
                paystack_ref
            )

            components.html(
                f"<script>window.open('{api_response.get('authorization_url')}', '_blank');</script>"
            )
            st.success("Checkout opened in new tab. Return and verify payment.")
        else:
            st.error("Payment initialization failed. Try again.")


# ============================================================
# 3️⃣ VERIFY PAYMENT → SHOW PAID INVOICE → DOWNLOAD → VIEW REPORT
# ============================================================
st.markdown("---")
st.subheader("✔️ Verify Payment & Access Report")

# Auto-redirect after download
if st.session_state.invoice_downloaded:
    st.success("Invoice downloaded! Redirecting...")
    time.sleep(2)
    st.switch_page("pages/view_report.py")


# -------------- VERIFY PAYMENT BUTTON ----------------
if not st.session_state.payment_verified:
    if st.button("🔍 Verify My Payment", type="primary", key="verify_btn"):
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
            st.error("Verification failed.")
            st.stop()


# ============================================================
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


    # ============================================================
    # LOAD REPORT DATA + SAVE USER HISTORY
    # ============================================================
    saved_group = st.session_state.saved_group
    saved_where = st.session_state.saved_where_clause

    query_map = {
        "Demographic Analysis": f"""
            SELECT ExamNum, ExamYear, Sex, Disability,
                   TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age
            FROM exam_candidates WHERE {saved_where}
        """,
        "Geographic & Institutional Insights": f"""
            SELECT ExamNum, ExamYear, State, Centre, COUNT(*) AS Count
            FROM exam_candidates WHERE {saved_where} GROUP BY State, Centre
        """,
        "Equity & Sponsorship": f"""
            SELECT ExamNum, ExamYear, Sponsor, Sex, Disability, COUNT(*) AS Count
            FROM exam_candidates WHERE {saved_where} GROUP BY Sponsor, Sex, Disability
        """,
        "Temporal & Progression Trends": f"""
            SELECT ExamNum, ExamYear, COUNT(*) AS Count
            FROM exam_candidates WHERE {saved_where} GROUP BY ExamYear
        """,
    }

    df = fetch_data(query_map.get(saved_group, f"SELECT * FROM exam_candidates WHERE {saved_where}"))

    if df is not None and not df.empty:
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

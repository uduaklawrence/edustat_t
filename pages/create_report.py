# ==============================
# 📊 CREATE REPORT (Invoice + Proceed to Payment + Watermark)
# ==============================

import streamlit as st
import streamlit.components.v1 as components
import os
import time
from datetime import datetime
from db_queries import (
    fetch_data,
    update_payment_status,
    create_invoice_record,
    attach_paystack_ref_to_invoice,
    mark_invoice_paid_by_paystack_ref,
)
from paystack import initialize_transaction, verify_transaction
from invoice_pdf import generate_invoice_pdf  # ✅ make sure this file exists

# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # ₦
WATERMARK_PATH = r"C:\Users\uludoh\Desktop\edustat_t\assets\image 2.jpg"

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
    "Select Columns to Filter", available_columns, default=available_columns
)

# ------------------ FILTERS ------------------
st.subheader("Apply Filters")

filter_values = {}
for col in selected_columns:
    if col == "Age":
        ages = fetch_data(
            "SELECT DISTINCT TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age FROM exam_candidates"
        )["Age"].tolist()
        filter_values[col] = st.multiselect(f"{col}:", ages, default=ages)
    else:
        distinct_vals = fetch_data(f"SELECT DISTINCT {col} FROM exam_candidates")[col].dropna().tolist()
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
# 🔍 SHOW PREVIEW
# ============================================================
st.markdown("---")
st.subheader("👀 Data Preview")

if st.button("Show Preview"):
    preview_query = f"SELECT * FROM exam_candidates WHERE {where_clause} LIMIT 3"
    preview_df = fetch_data(preview_query)
    if not preview_df.empty:
        st.dataframe(preview_df, width='stretch')
        st.caption("✅ Showing top 3 rows based on your selected filters.")
    else:
        st.warning("No data matches your current filter selection.")

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

            # ✅ Generate invoice PDF
            pdf_path = generate_invoice_pdf(
                invoice_ref=invoice_ref,
                user_email=user_email,
                amount=SUBSCRIPTION_AMOUNT,
                description=f"Custom Report - {selected_group}",
                selected_group=selected_group,
                selected_columns=selected_columns,
                status="Pending Payment",
            )

            # ✅ Display formatted invoice in UI
            user_display = user_email.split("@")[0].replace(".", " ").title()
            invoice_date = datetime.now().strftime("%B %d, %Y")
            watermark_url = f"file://{os.path.abspath(WATERMARK_PATH)}"

            invoice_html = f"""
            <h2 style="text-align:center; margin-bottom:10px;">INVOICE</h2>
            <p><b>Name:</b> {user_display}</p>
            <p><b>Invoice No:</b> {invoice_ref}</p>
            <p><b>Date:</b> {invoice_date}</p>
            <p><b>Report Group:</b> {selected_group}</p>
            <hr>
            <table style="width:100%; border-collapse:collapse; margin-top:15px; font-size:15px;">
                <thead>
                    <tr style="background-color:#f2f2f2;">
                        <th style="padding:8px; border:1px solid #ddd;">Item</th>
                        <th style="padding:8px; border:1px solid #ddd;">Quantity</th>
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
                    <tr style="background-color:#f9f9f9;">
                        <td colspan="2" style="text-align:right; padding:8px; border:1px solid #ddd;"><b>Grand Total</b></td>
                        <td style="padding:8px; border:1px solid #ddd;"><b>₦{SUBSCRIPTION_AMOUNT:,.2f}</b></td>
                    </tr>
                </tbody>
            </table>
            <p style="margin-top:15px;"><b>Status:</b> <span style="color:#ff8800;">Pending Payment</span></p>
            """

            st.markdown(
                f"""
                <div style="display:flex; justify-content:center;">
                    <div style="
                        background-color:#ffffff;
                        color:#000;
                        border-radius:10px;
                        padding:25px;
                        width:80%;
                        box-shadow:0 0 10px rgba(0,0,0,0.1);
                        background-image:url('{watermark_url}');
                        background-repeat:no-repeat;
                        background-position:center;
                        background-size:45%;
                    ">
                        {invoice_html}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ✅ Download PDF
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    "📄 Download Invoice PDF",
                    data=pdf_file,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                )

            st.info("Click below to proceed with payment through Paystack.")
        else:
            st.error("❌ Unable to create invoice. Please try again.")

# ============================================================
# 2️⃣ PROCEED TO PAYMENT
# ============================================================
if st.session_state.invoice_ref and not st.session_state.payment_verified:
    if st.button("Proceed to Payment", type="primary"):
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
st.subheader("✔️ Verify Payment & View Report")

if st.button("Verify My Payment", type="primary"):
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

        saved_group = st.session_state.get("saved_group")
        saved_where = st.session_state.get("saved_where_clause")

        if saved_group == "Demographic Analysis":
            query = f"""
            SELECT ExamNum, ExamYear, Sex, Disability,
                   TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age
            FROM exam_candidates
            WHERE {saved_where}
            """
        elif saved_group == "Geographic & Institutional Insights":
            query = f"""
            SELECT ExamNum, ExamYear, State, Centre, COUNT(*) AS Count
            FROM exam_candidates
            WHERE {saved_where}
            GROUP BY State, Centre
            """
        elif saved_group == "Equity & Sponsorship":
            query = f"""
            SELECT ExamNum, ExamYear, Sponsor, Sex, Disability, COUNT(*) AS Count
            FROM exam_candidates
            WHERE {saved_where}
            GROUP BY Sponsor, Sex, Disability
            """
        elif saved_group == "Temporal & Progression Trends":
            query = f"""
            SELECT ExamNum, ExamYear, COUNT(*) AS Count
            FROM exam_candidates
            WHERE {saved_where}
            GROUP BY ExamYear
            """
        else:
            query = f"SELECT * FROM exam_candidates WHERE {saved_where}"

        df = fetch_data(query)
        if df.empty:
            st.warning("Payment verified, but no data found for your filters.")
        else:
            st.session_state.filtered_df = df
            st.success("✅ Payment verified and report prepared.")
            time.sleep(1)
            st.switch_page("pages/view_report.py")
    else:
        msg = verification_response.get("data", {}).get("gateway_response", "Verification failed.")
        st.warning(f"Payment not confirmed. Reason: {msg}")

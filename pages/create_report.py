import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import pandas as pd
import uuid
import time
from db_queries import fetch_data, update_payment_status
from paystack import initialize_transaction, verify_transaction

SUBSCRIPTION_AMOUNT = 20000.00  # Subscription amount (₦)

# ------------------ AUTH CHECK ------------------
if not st.session_state.get('logged_in', False):
    st.warning("Please sign in to view the report.")
    st.stop()

st.set_page_config(page_title="Create Report", layout="wide")
st.title("📊 Create Custom Reports")

user_email = st.session_state.get('user_email')

# ------------------ INITIALIZE SESSION STATES ------------------
if 'paystack_reference' not in st.session_state:
    st.session_state.paystack_reference = None
if 'payment_verified' not in st.session_state:
    st.session_state.payment_verified = False

# ------------------ INSIGHT GROUP SELECTION ------------------
insight_groups = [
    "Demographic Analysis",
    "Geographic & Institutional Insights",
    "Equity & Sponsorship",
    "Temporal & Progression Trends"
]
selected_group = st.selectbox("Select Insight Group", insight_groups)

# ------------------ COLUMN SELECTION ------------------
columns_map = {
    "Demographic Analysis": ["ExamNum", "ExamYear", "Sex", "Disability", "Age"],
    "Geographic & Institutional Insights": ["ExamNum", "ExamYear", "State", "Centre"],
    "Equity & Sponsorship": ["ExamNum", "ExamYear", "Sponsor", "Sex", "Disability"],
    "Temporal & Progression Trends": ["ExamYear"]
}
available_columns = columns_map[selected_group]
selected_columns = st.multiselect("Select Columns to Filter", available_columns, default=available_columns)

# ------------------ FILTERS ------------------
st.subheader("Apply Filters")

filter_values = {}
for col in selected_columns:
    if col == "Age":
        ages = fetch_data("SELECT DISTINCT TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age FROM exam_candidates")['Age'].tolist()
        filter_values[col] = st.multiselect(f"{col}:", ages, default=ages)
    else:
        distinct_vals = fetch_data(f"SELECT DISTINCT {col} FROM exam_candidates")[col].dropna().tolist()
        filter_values[col] = st.multiselect(f"{col}:", ["All"] + distinct_vals, default=["All"])

# ------------------ BUILD FILTER CLAUSE ------------------
filters = []
for col, values in filter_values.items():
    if "All" not in values:
        if col == "Age":
            filters.append(f"TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) IN ({','.join(map(str, values))})")
        else:
            value_list = ", ".join(f"'{v}'" for v in values)
            filters.append(f"{col} IN ({value_list})")

where_clause = " AND ".join(filters) if filters else "1=1"

# ------------------ CHART TYPE SELECTION ------------------
st.subheader("Select Chart Types")
chart_options = ["Table/Matrix", "Bar Chart", "Pie Chart", "Line Chart"]
selected_charts = st.multiselect("Select chart(s):", chart_options, default=["Table/Matrix"])

# =================================================================
# GENERATE REPORT BUTTON
# =================================================================
if st.button("Generate Report", type="primary"):
    payment_query = f"SELECT payment FROM users WHERE email_address='{user_email}'"
    payment_status_df = fetch_data(payment_query)
    user_has_paid = not payment_status_df.empty and payment_status_df['payment'].values[0]
    if st.session_state.payment_verified:
        user_has_paid = True

    # --- SCENARIO 1: USER HAS NOT PAID ---
    if not user_has_paid:
        with st.spinner("Subscription required. Redirecting to payment page..."):
            api_response = initialize_transaction(email_address=user_email, amount=SUBSCRIPTION_AMOUNT)
            if api_response and api_response.get("authorization_url"):
                st.session_state.paystack_reference = api_response.get("reference")
                checkout_url = api_response.get("authorization_url")

                redirect_script = f"<script>window.open('{checkout_url}', '_blank');</script>"
                components.html(redirect_script)

                st.success("🚀 Payment page opened in a new tab.")
                st.warning("After completing your payment, return to this tab and click 'Verify My Payment'.")
            else:
                st.error("Failed to connect to the payment gateway. Please try again.")

    # --- SCENARIO 2: USER HAS ALREADY PAID ---
    else:
        st.success("Report generation for paid user...")

st.divider()

# =================================================================
# MANUAL PAYMENT VERIFICATION
# =================================================================
st.subheader("Already Paid?")
st.write("If you've completed your payment, verify your transaction here.")

if st.button("Verify My Payment"):
    reference_to_verify = st.session_state.get('paystack_reference')
    if not reference_to_verify:
        st.error("No payment reference found. Please click 'Generate Report' to start.")
    else:
        with st.spinner(f"Verifying payment reference {reference_to_verify}..."):
            verification_response = verify_transaction(reference_to_verify)

            if (verification_response and verification_response.get("status") is True and
                verification_response.get("data", {}).get("status") == "success"):

                if update_payment_status(user_email):
                    st.session_state.payment_verified = True

                    # ✅ Save selections for persistence
                    st.session_state.saved_group = selected_group
                    st.session_state.saved_columns = selected_columns
                    st.session_state.saved_filters = filter_values
                    st.session_state.saved_charts = selected_charts

                    # ✅ Build the filtered DataFrame to send to the next page
                    if selected_group == "Demographic Analysis":
                        query = f"""
                        SELECT ExamNum, ExamYear, Sex, Disability,
                               TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age
                        FROM exam_candidates
                        WHERE {where_clause}
                        """
                    elif selected_group == "Geographic & Institutional Insights":
                        query = f"""
                        SELECT ExamNum, ExamYear, State, Centre, COUNT(*) AS Count
                        FROM exam_candidates
                        WHERE {where_clause}
                        GROUP BY State, Centre
                        """
                    elif selected_group == "Equity & Sponsorship":
                        query = f"""
                        SELECT ExamNum, ExamYear, Sponsor, Sex, Disability, COUNT(*) AS Count
                        FROM exam_candidates
                        WHERE {where_clause}
                        GROUP BY Sponsor, Sex, Disability
                        """
                    elif selected_group == "Temporal & Progression Trends":
                        query = f"""
                        SELECT ExamNum, ExamYear, COUNT(*) AS Count
                        FROM exam_candidates
                        WHERE {where_clause}
                        GROUP BY ExamYear
                        """
                    else:
                        query = f"SELECT * FROM exam_candidates WHERE {where_clause}"

                    df = fetch_data(query)
                    if df.empty:
                        st.warning("No data found for the selected filters.")
                    else:
                        # ✅ Save to session for view_report.py
                        st.session_state.filtered_df = df
                        st.success("✅ Payment Verified! Preparing your report...")
                        time.sleep(1)
                        st.switch_page("pages/view_report.py")

                else:
                    st.error("Payment was successful but account update failed. Please contact support.")
            else:
                message = verification_response.get("data", {}).get("gateway_response", "Verification failed.")
                st.warning(f"Payment not confirmed. Reason: {message}")

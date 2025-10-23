import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import pandas as pd
import uuid
import time
from db_queries import fetch_data, update_payment_status
from paystack import initialize_transaction, verify_transaction
 
SUBSCRIPTION_AMOUNT = 20000.00 # set subscription amount here in Naira
 
 
# ------------------ AUTH CHECK ------------------
if not st.session_state.get('logged_in', False):
    st.warning("Please sign in to view the report.")
    st.stop()
 
st.set_page_config(page_title="Create Report", layout="wide")
st.title("📊 Create Custom Reports")
 
user_email = st.session_state.get('user_email')
 
# --- UPDATED: Initialize session state for the Paystack flow ---
if 'paystack_reference' not in st.session_state: # <-- CHANGE HERE
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
 
# ------------------ COLUMN SELECTION BASED ON INSIGHT ------------------
columns_map = {
    "Demographic Analysis": ["ExamYear", "Sex", "Disability", "Age"],
    "Geographic & Institutional Insights": ["ExamYear", "State", "Centre"],
    "Equity & Sponsorship": ["ExamYear", "Sponsor", "Sex", "Disability"],
    "Temporal & Progression Trends": ["ExamYear"]
}
available_columns = columns_map[selected_group]
selected_columns = st.multiselect("Select Columns to Filter", available_columns, default=available_columns)
 
# ------------------ FILTERS ------------------
st.subheader("Apply Filters")
 
filters = []
filter_values = {}
for col in selected_columns:
    if col == "Age":
        # Compute age from DateOfBirth
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
# Table/Matrix is mandatory
default_chart_selection = ["Table/Matrix"]
selected_charts = st.multiselect("Select chart(s):", chart_options, default=default_chart_selection)
 
# =================================================================
# GENERATE REPORT BUTTON & CORE LOGIC
# =================================================================
if st.button("Generate Report", type="primary"):
    # ... (payment status check from DB remains the same) ...
    payment_query = f"SELECT payment FROM users WHERE email_address='{user_email}'"
    payment_status_df = fetch_data(payment_query)
    user_has_paid = not payment_status_df.empty and payment_status_df['payment'].values[0]
    if st.session_state.payment_verified:
        user_has_paid = True
 
    # --- SCENARIO 1: USER HAS NOT PAID ---
    if not user_has_paid:
        with st.spinner("Subscription required. Redirecting to payment page..."):
 
            # UPDATED: Call the Paystack initialize function
            api_response = initialize_transaction(
                email_address=user_email,
                amount=SUBSCRIPTION_AMOUNT
            )
 
            if api_response and api_response.get("authorization_url"):
                # UPDATED: Save the Paystack reference for verification later
                st.session_state.paystack_reference = api_response.get("reference")
 
                checkout_url = api_response.get("authorization_url")
                redirect_script = f"<script>window.open('{checkout_url}', '_blank');</script>"
                components.html(redirect_script)
 
                # UX IMPROVEMENT: Give the user clear instructions in the original tab
                st.success("🚀 Your payment page has opened in a new tab.")
                st.warning("After completing your payment, please return to this tab and click 'Verify My Payment' below to unlock your report.")
            else:
                st.error("Failed to connect to the payment gateway. Please try again.")
 
    # --- SCENARIO 2: USER HAS ALREADY PAID ---
    else:
        # ... (Your report generation logic goes here, no changes needed) ...
        st.success("Report generation for paid user...")
 
 
st.divider()
 
# =================================================================
# MANUAL VERIFICATION SECTION
# =================================================================
st.subheader("Already Paid?")
st.write("If you've completed your payment, verify your transaction here.")
 
if st.button("Verify My Payment"):
    # UPDATED: We now verify using the paystack_reference
    reference_to_verify = st.session_state.get('paystack_reference')
    if not reference_to_verify:
        st.error("We couldn't find a payment reference to verify. Please click 'Generate Report' to start.")
    else:
        with st.spinner(f"Verifying payment reference {reference_to_verify}..."):
 
            # UPDATED: Call the Paystack verification function
            verification_response = verify_transaction(reference_to_verify)
 
            if (verification_response and verification_response.get("status") is True and
                verification_response.get("data", {}).get("status") == "success"):
 
                if update_payment_status(user_email):
                    st.session_state.payment_verified = True
                    # ✅ Save filters and chart selections so they persist after reload
                    st.session_state.saved_group = selected_group
                    st.session_state.saved_columns = selected_columns
                    st.session_state.saved_filters = filter_values
                    st.session_state.saved_charts = selected_charts

                    st.success("✅ Payment Verified! Generating your report now...")
                    time.sleep(2)
                    st.rerun()

                else:
                    st.error("Payment was successful but we failed to update your account. Please contact support.")
            else:
                message = verification_response.get("data", {}).get("gateway_response", "Verification failed.")
                st.warning(f"Payment not confirmed. Reason: {message}")
 
# =================================================================
# DISPLAY REPORTS AFTER PAYMENT VERIFIED
# =================================================================
if st.session_state.payment_verified:
    st.success("Payment verified ✅. Generating your visualization...")

    # ------------------ BUILD QUERY BASED ON SELECTED GROUP ------------------
    if selected_group == "Demographic Analysis":
        query = f"""
        SELECT ExamYear, Sex, Disability, TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age
        FROM exam_candidates
        WHERE {where_clause}
        """
    elif selected_group == "Geographic & Institutional Insights":
        query = f"""
        SELECT ExamYear, State, Centre, COUNT(*) AS Count
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY State, Centre
        """
    elif selected_group == "Equity & Sponsorship":
        query = f"""
        SELECT ExamYear, Sponsor, Sex, Disability, COUNT(*) AS Count
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY Sponsor, Sex, Disability
        """
    elif selected_group == "Temporal & Progression Trends":
        query = f"""
        SELECT ExamYear, COUNT(*) AS Count
        FROM exam_candidates
        WHERE {where_clause}
        GROUP BY ExamYear
        """
    else:
        query = f"SELECT * FROM exam_candidates WHERE {where_clause}"

    df = fetch_data(query)

    if df.empty:
        st.info("No data available for the selected filters.")
    else:
        if "Table/Matrix" in selected_charts:
            st.subheader("Data Table")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download CSV", data=csv, file_name="report.csv", mime='text/csv')

        if "Bar Chart" in selected_charts:
            st.subheader("Bar Chart")
            x_col = df.columns[0]
            y_col = df.columns[1] if df.shape[1] > 1 else df.columns[0]
            fig = px.bar(df, x=x_col, y=y_col, color=x_col, title=f"{selected_group} - Bar Chart")
            st.plotly_chart(fig, use_container_width=True)

        if "Pie Chart" in selected_charts:
            st.subheader("Pie Chart")
            x_col = df.columns[0]
            y_col = df.columns[1] if df.shape[1] > 1 else df.columns[0]
            fig = px.pie(df, values=y_col, names=x_col, title=f"{selected_group} - Pie Chart", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

        if "Line Chart" in selected_charts:
            st.subheader("Line Chart")
            x_col = df.columns[0]
            y_col = df.columns[1] if df.shape[1] > 1 else df.columns[0]
            fig = px.line(df, x=x_col, y=y_col, markers=True, title=f"{selected_group} - Line Chart")
            st.plotly_chart(fig, use_container_width=True)

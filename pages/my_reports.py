import streamlit as st
from db_queries import fetch_user_reports

st.set_page_config(page_title="My Reports", layout="wide")
st.title("📁 My Reports (History)")

# Ensure user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please log in to view your reports.")
    st.stop()

user_id = st.session_state.get("user_id")

# Fetch reports
reports = fetch_user_reports(user_id)

if reports.empty:
    st.info("You have no saved reports in the last 30 days.")
    st.stop()

# Display in a table
st.subheader("Your Saved Reports")

st.dataframe(
    reports[[
        "invoice_ref",
        "report_group",
        "pdf_path",
        "created_at",
        "expires_at"
    ]],
    use_container_width=True
)

# Let user view/download a report
st.subheader("Open a Report")

report_ids = reports["report_id"].tolist()
selected_id = st.selectbox("Select a Report ID", report_ids)

if st.button("Open Report"):
    st.session_state.selected_report_id = selected_id
    st.switch_page("pages/view_report.py")
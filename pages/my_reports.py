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
reports = reports.reset_index(drop=True)
reports.index = reports.index + 1

if reports.empty:
    st.info("You have no saved reports in the last 30 days.")
    st.stop()

# Display in a table
st.subheader("Your Saved Reports")

st.dataframe(
    reports[[
         "report_name",
        "report_group",
        "pdf_path",
        "created_at",
        "expires_at"
    ]],
    width='stretch'
)

# Let user view/download a report
st.subheader("Open a Report")

report_names = reports["report_name"].tolist()
selected_name = st.selectbox("Select a Report to open", report_names)

if st.button("Open Report"):
    # Find corresponding report_id
    selected_report = reports[reports["report_name"] == selected_name].iloc[0]
    st.session_state.selected_report_id = int(selected_report["report_id"])
    st.switch_page("pages/view_report.py")

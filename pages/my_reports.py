import streamlit as st
from db_queries import fetch_user_reports
import pandas as pd

st.set_page_config(page_title="My Reports", layout="wide")

# Load your existing CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional CSS for the reports table (complements your existing styles.css)
st.markdown("""
<style>
    /* Reports page specific styles */
    .reports-container {
        background: var(--card-white);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
    }
    
    .reports-header {
        margin-bottom: 32px;
    }
    
    .reports-title {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 8px;
    }
    
    .reports-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
    }
    
    .search-filter-row {
        margin-bottom: 32px;
    }
    
    /* Table styling using your design system */
    .reports-table-header {
        background-color: var(--background-gray);
        padding: 16px;
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 2px solid var(--border-light);
    }
    
    .reports-table-row {
        padding: 16px;
        border-bottom: 1px solid var(--border-light);
        transition: background-color 0.2s;
        display: flex;
        align-items: center;
    }
    
    .reports-table-row:hover {
        background-color: var(--background-gray);
    }
    
    .report-name-link {
        color: var(--accent-blue);
        text-decoration: none;
        font-weight: 500;
        cursor: pointer;
    }
    
    .report-name-link:hover {
        color: var(--primary-blue);
        text-decoration: underline;
    }
    
    /* Expiry badge */
    .expiry-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
    }
    
    .expiry-normal {
        background-color: #dbeafe;
        color: #1e40af;
    }
    
    .expiry-warning {
        background-color: #fef3c7;
        color: #92400e;
    }
    
    /* Action buttons */
    .action-buttons {
        display: flex;
        gap: 8px;
        align-items: center;
    }
    
    div[data-testid="stButton"] button.action-btn {
        background: transparent !important;
        border: 1px solid var(--border-light) !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        color: var(--text-secondary) !important;
        font-size: 18px !important;
        transition: all 0.2s ease !important;
        min-width: 40px !important;
        height: 40px !important;
    }
    
    div[data-testid="stButton"] button.action-btn:hover {
        background: var(--background-gray) !important;
        border-color: var(--primary-blue) !important;
        color: var(--primary-blue) !important;
    }
    
    div[data-testid="stButton"] button.report-name-btn {
        background: transparent !important;
        border: none !important;
        color: var(--accent-blue) !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 0 !important;
        transition: color 0.2s ease !important;
    }
    
    div[data-testid="stButton"] button.report-name-btn:hover {
        color: var(--primary-blue) !important;
        text-decoration: underline !important;
    }
    
    /* Search input styling */
    .stTextInput input {
        border-radius: 8px !important;
        border: 2px solid var(--border-light) !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
    }
    
    .stTextInput input:focus {
        border-color: var(--primary-blue) !important;
    }
    
    .stSelectbox select {
        border-radius: 8px !important;
        border: 2px solid var(--border-light) !important;
        padding: 12px 16px !important;
    }
    
    .stSelectbox select:focus {
        border-color: var(--primary-blue) !important;
    }
</style>
""", unsafe_allow_html=True)

# Page header
st.markdown("""
<div class="reports-header">
    <div class="reports-title">Saved Reports</div>
    <div class="reports-subtitle">Access and manage your previously generated reports</div>
</div>
""", unsafe_allow_html=True)

# Ensure user is logged in
if not st.session_state.get("logged_in", False):
    st.warning("Please log in to view your reports.")
    st.stop()

user_id = st.session_state.get("user_id")

# Fetch reports
reports = fetch_user_reports(user_id)

# Search and filter section
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("", placeholder="🔍 Search saved reports...", label_visibility="collapsed")

with col2:
    categories = ["All Categories"] + (reports["report_group"].unique().tolist() if not reports.empty else [])
    selected_category = st.selectbox("", categories, label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)

if reports.empty:
    st.info("You have no saved reports in the last 30 days.")
    st.stop()

# Filter reports based on search and category
filtered_reports = reports.copy()

if search_query:
    filtered_reports = filtered_reports[
        filtered_reports["report_name"].str.contains(search_query, case=False, na=False)
    ]

if selected_category != "All Categories":
    filtered_reports = filtered_reports[filtered_reports["report_group"] == selected_category]

# Create table within a container
st.markdown('<div class="reports-container">', unsafe_allow_html=True)

# Table header
header_cols = st.columns([1, 1.5, 2.5, 1.5, 1.5, 1.5])
headers = ["Report ID", "Report Type", "Report Name", "Date Created", "Expiry Date", "Actions"]

for col, header in zip(header_cols, headers):
    with col:
        st.markdown(f'<div class="reports-table-header">{header}</div>', unsafe_allow_html=True)

# Data rows
for idx, row in filtered_reports.iterrows():
    row_cols = st.columns([1, 1.5, 2.5, 1.5, 1.5, 1.5])
    
    with row_cols[0]:
        st.markdown(f'<div style="padding: 16px; color: var(--text-secondary); font-family: monospace;">{row["report_id"]}</div>', unsafe_allow_html=True)
    
    with row_cols[1]:
        st.markdown(f'<div style="padding: 16px; color: var(--text-primary);">{row["report_group"]}</div>', unsafe_allow_html=True)
    
    with row_cols[2]:
        # Clickable report name using your button style
        if st.button(row["report_name"], key=f"name_{row['report_id']}", type="secondary"):
            st.session_state.selected_report_id = int(row["report_id"])
            st.switch_page("pages/view_report.py")
    
    with row_cols[3]:
        # Format date
        date_created = pd.to_datetime(row["created_at"]).strftime("%d/%m/%Y") if pd.notna(row["created_at"]) else "N/A"
        st.markdown(f'<div style="padding: 16px; color: var(--text-primary);">{date_created}</div>', unsafe_allow_html=True)
    
    with row_cols[4]:
        # Calculate days left
        if pd.notna(row["expires_at"]):
            expires_at = pd.to_datetime(row["expires_at"])
            days_left = (expires_at - pd.Timestamp.now()).days
            badge_class = "expiry-warning" if days_left < 7 else "expiry-normal"
            st.markdown(f'<div style="padding: 16px;"><span class="expiry-badge {badge_class}">{days_left} days left</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding: 16px; color: var(--text-secondary);">N/A</div>', unsafe_allow_html=True)
    
    with row_cols[5]:
        # Action buttons
        action_cols = st.columns(3)
        
        with action_cols[0]:
            if st.button("👁️", key=f"view_{row['report_id']}", help="View report"):
                st.session_state.selected_report_id = int(row["report_id"])
                st.switch_page("pages/view_report.py")
        
        with action_cols[1]:
            if st.button("⬇️", key=f"download_{row['report_id']}", help="Download report"):
                # Implement download logic
                st.toast(f"Downloading {row['report_name']}...")
        
        with action_cols[2]:
            if st.button("🗑️", key=f"delete_{row['report_id']}", help="Delete report"):
                # Implement delete logic with confirmation
                if st.session_state.get(f"confirm_delete_{row['report_id']}", False):
                    # Add your delete query here
                    # delete_report(row['report_id'])
                    st.success(f"Deleted {row['report_name']}")
                    st.rerun()
                else:
                    st.session_state[f"confirm_delete_{row['report_id']}"] = True
                    st.warning("Click again to confirm deletion")
    
    st.markdown("<hr style='margin: 0; border: none; border-bottom: 1px solid var(--border-light);'>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Show message if no results after filtering
if filtered_reports.empty:
    st.info("No reports found matching your search criteria.")
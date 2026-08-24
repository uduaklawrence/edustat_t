import streamlit as st
import json
from datetime import datetime
import sys
from pathlib import Path
from db_queries import (
    fetch_data,
    create_invoice_record,
)
from redis_cache import get_or_set_distinct_values
from report_config import report_structure   # ← single source of truth

# Add parent directory to path to import auth_utils
sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import require_authentication, logout_user

# -------------------- AUTH CHECK --------------------
require_authentication()

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Create Report", layout="wide")

# Back to Dashboard Button
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button("← Back to Dashboard", key="back_to_dashboard"):
        st.switch_page("pages/dashboard.py")

# Load existing CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Additional CSS for report selection UI
st.markdown("""
<style>
    .report-selection-header { text-align: center; margin-bottom: 40px; }
    .report-selection-title {
        font-size: 36px; font-weight: 700;
        color: var(--text-primary); margin-bottom: 12px;
    }
    .report-selection-subtitle {
        font-size: 18px; color: var(--text-secondary);
        max-width: 800px; margin: 0 auto; line-height: 1.6;
    }
    .subgroup-card {
        background: white; border-radius: 12px; padding: 28px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
        display: flex; flex-direction: column; min-height: 280px;
    }
    .subgroup-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-4px);
        border-color: var(--accent-blue);
    }
    .subgroup-card-title {
        font-size: 20px; font-weight: 700;
        color: var(--text-primary); margin-bottom: 16px;
        min-height: 52px; display: flex; align-items: center;
    }
    .subgroup-card-description {
        color: var(--text-secondary); font-size: 15px;
        line-height: 1.6; flex-grow: 1; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email")
user_id    = st.session_state.get("user_id", 0)

# -------------------- SESSION DEFAULTS --------------------
st.session_state.setdefault("selected_main_group", None)
st.session_state.setdefault("selected_subgroup",   None)
st.session_state.setdefault("invoice_ref",         None)
st.session_state.setdefault("payment_verified",    False)

# Clear filter state when user returns to create a new report
st.session_state["_filter_page_key"] = None

# -------------------- HEADER --------------------
st.markdown("""
<div class="report-selection-header">
    <div class="report-selection-title">Select Report Group</div>
    <div class="report-selection-subtitle">
        Choose a report group to begin your data analysis journey. 
        Each group provides specialised insights tailored to your needs.
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------- GROUP SELECTION TABS --------------------
if not st.session_state.selected_main_group:
    st.session_state.selected_main_group = list(report_structure.keys())[0]

group_list = list(report_structure.items())

# First row — first 6 groups
cols = st.columns(6)
for idx in range(min(6, len(group_list))):
    group_name, group_data = group_list[idx]
    with cols[idx]:
        if st.button(
            f"{group_data['icon']} {group_name}",
            key=f"group_{idx}",
            use_container_width=True,
        ):
            st.session_state.selected_main_group = group_name
            st.rerun()

# Second row — remaining groups
remaining = group_list[6:]
if remaining:
    st.markdown("<br>", unsafe_allow_html=True)
    cols2 = st.columns(len(remaining))
    for idx, (group_name, group_data) in enumerate(remaining):
        with cols2[idx]:
            if st.button(
                f"{group_data['icon']} {group_name}",
                key=f"group_{idx + 6}",
                use_container_width=True,
            ):
                st.session_state.selected_main_group = group_name
                st.rerun()

# -------------------- SUBGROUP CARDS --------------------
selected_group = st.session_state.selected_main_group
st.markdown(f"### 📋 {selected_group}")
st.markdown("---")

subgroups = report_structure[selected_group]["subgroups"]
num_cols  = 3
rows      = [
    list(subgroups.items())[i : i + num_cols]
    for i in range(0, len(subgroups), num_cols)
]

for row in rows:
    cols = st.columns(num_cols)
    for idx, (subgroup_name, description) in enumerate(row):
        with cols[idx]:
            st.markdown(f"""
            <div class="subgroup-card">
                <div class="subgroup-card-title">{subgroup_name}</div>
                <div class="subgroup-card-description">{description}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(
                "Explore Filters",
                key=f"explore_{subgroup_name}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state.selected_subgroup   = subgroup_name
                st.session_state.selected_main_group = selected_group
                st.switch_page("pages/report_filters.py")

    # Pad last row with empty columns
    for empty_idx in range(len(row), num_cols):
        cols[empty_idx].empty()

st.markdown("<br><br>", unsafe_allow_html=True)
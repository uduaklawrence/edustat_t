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

# Add parent directory to path to import auth_utils
sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import require_authentication, logout_user

# -------------------- AUTH CHECK --------------------
require_authentication()

# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # 

st.set_page_config(page_title="Create Report", layout="wide")

# Back to Dashboard Button
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    if st.button("← Back to Dashboard", key="back_to_dashboard"):
        st.switch_page("pages/dashboard.py")

# Load existing CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional CSS for report selection UI
st.markdown("""
<style>
    /* Header Section */
    .report-selection-header {
        text-align: center;
        margin-bottom: 40px;
    }
    
    .report-selection-title {
        font-size: 36px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }
    
    .report-selection-subtitle {
        font-size: 18px;
        color: var(--text-secondary);
        max-width: 800px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Group Tabs */
    .group-tabs-container {
        display: flex;
        gap: 12px;
        margin: 40px 0 30px 0;
        flex-wrap: wrap;
        justify-content: center;
    }
    
    .group-tab {
        background: white;
        padding: 14px 28px;
        border-radius: 8px;
        border: 2px solid var(--border-light);
        cursor: pointer;
        font-weight: 600;
        color: var(--text-secondary);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 15px;
    }
    
    .group-tab:hover {
        border-color: var(--primary-blue);
        color: var(--primary-blue);
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    
    .group-tab.active {
        background: var(--primary-navy);
        color: white;
        border-color: var(--primary-navy);
        box-shadow: 0 4px 12px rgba(30, 39, 73, 0.3);
    }
    
    /* Subgroup Cards */
    .subgroup-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 24px;
        margin-top: 40px;
    }
    
    .subgroup-card {
        background: white;
        border-radius: 12px;
        padding: 28px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        min-height: 280px;
    }
    
    .subgroup-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-4px);
        border-color: var(--accent-blue);
    }
    
    .subgroup-card-title {
        font-size: 20px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 16px;
        min-height: 52px;
        display: flex;
        align-items: center;
    }
    
    .subgroup-card-description {
        color: var(--text-secondary);
        font-size: 15px;
        line-height: 1.6;
        flex-grow: 1;
        margin-bottom: 20px;
    }
    
    /* Explore Button */
    div[data-testid="stButton"] button.explore-btn {
        background-color: var(--primary-navy) !important;
        color: white !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        font-size: 15px !important;
    }
    
    div[data-testid="stButton"] button.explore-btn:hover {
        background-color: var(--primary-blue) !important;
        box-shadow: 0 4px 12px rgba(30, 39, 73, 0.3) !important;
        transform: translateY(-2px) !important;
    }
</style>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# ------------------ SESSION DEFAULTS ------------------
st.session_state.setdefault("selected_main_group", None)
st.session_state.setdefault("selected_subgroup", None)
st.session_state.setdefault("invoice_ref", None)
st.session_state.setdefault("payment_verified", False)

# ------------------ REPORT STRUCTURE ------------------
report_structure = {
    "Demographic Analysis": {
        "icon": "👥",
        "subgroups": {
            "Age Distribution Analysis": "Analyzes candidate age ranges, trends, and appropriateness across exam years and types.",
            "Gender Equity Analysis": "Examines male-to-female ratios, gender balance trends, and distribution across exam types.",
            "Special Needs & Disability Analysis": "Tracks inclusion rates and disability representation trends over time and by demographics."
        }
    },
    "Geographic & Institutional Insights": {
        "icon": "🗺️",
        "subgroups": {
            "State-Level Distribution": "Identifies enrollment patterns, top/bottom states, and regional education access.",
            "Centre/School Comparison": "Compares examination centres by popularity, capacity, and geographic distribution.",
            "Origin Analysis": "Maps where candidates come from and migration patterns for education."
        }
    },
    "Examination & Academic Performance": {
        "icon": "📊",
        "subgroups": {
            "Exam Type Analysis": "Compares school exams vs private exams distribution, preferences, and trends.",
            "Subject Performance Analysis": "Reveals most popular subjects, enrollment patterns, and subject difficulty levels.",
            "Grade Distribution Analysis": "Shows overall performance, pass/fail rates, and grade patterns across variables."
        }
    },
    "Temporal & Progression Trends": {
        "icon": "📈",
        "subgroups": {
            "Year-over-Year Enrollment Trends": "Tracks enrollment growth/decline and education system expansion over time.",
            "Birth Cohort Analysis": "Examines age-appropriate enrollment and generational education patterns."
        }
    },
    "Cross-Dimensional Analysis": {
        "icon": "🔄",
        "subgroups": {
            "Gender-Subject Preference": "Identifies gender biases in subject selection and male/female-dominated fields.",
            "Gender-Performance Analysis": "Compares academic outcomes between male and female candidates.",
            "Age-Performance Correlation": "Determines if age affects exam success and identifies optimal age ranges.",
            "State-Performance Comparison": "Ranks states by academic outcomes and identifies regional performance gaps.",
            "Disability-Performance Analysis": "Measures achievement gaps between students with and without disabilities.",
            "Exam Type-Performance Analysis": "Compares grade outcomes between school and private examinations.",
            "Centre-Performance Rankings": "Ranks centres by academic quality and identifies best/worst performers."
        }
    },
    "Statistical Insights & Summaries": {
        "icon": "📉",
        "subgroups": {
            "Descriptive Statistics": "Provides mean, median, standard deviation, and outlier detection across all metrics.",
            "Correlation Analysis": "Identifies relationships between variables and factors predicting academic success."
        }
    }
}

# ------------------ HEADER SECTION ------------------
st.markdown("""
<div class="report-selection-header">
    <div class="report-selection-title">Select Report Group</div>
    <div class="report-selection-subtitle">
        Choose a report group to begin your data analysis journey. Each group provides specialized 
        insights tailored to your needs.
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------ GROUP SELECTION TABS ------------------
# Initialize selected group if not set
if 'selected_main_group' not in st.session_state or st.session_state.selected_main_group is None:
    st.session_state.selected_main_group = list(report_structure.keys())[0]

# Create clickable group tabs
cols = st.columns(len(report_structure))
for idx, (group_name, group_data) in enumerate(report_structure.items()):
    with cols[idx]:
        if st.button(
            f"{group_data['icon']} {group_name}", 
            key=f"group_{idx}",
            use_container_width=True
        ):
            st.session_state.selected_main_group = group_name
            st.rerun()

# Display selected group indicator
selected_group = st.session_state.selected_main_group
st.markdown(f"### 📋 {selected_group}")
st.markdown("---")

# ------------------ SUBGROUP CARDS ------------------
subgroups = report_structure[selected_group]["subgroups"]

# Create grid of subgroup cards
num_cols = 3
rows = [list(subgroups.items())[i:i+num_cols] for i in range(0, len(subgroups), num_cols)]

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
            
            if st.button("Explore Filters →", key=f"explore_{subgroup_name}", type="primary"):
                st.session_state.selected_subgroup = subgroup_name
                st.session_state.selected_main_group = selected_group
                
                # Redirect to filters page (you'll create this next)
                st.switch_page("pages/report_filters.py")

# Fill empty columns in last row
if len(row) < num_cols:
    for _ in range(num_cols - len(row)):
        with cols[len(row)]:
            st.empty()

st.markdown("<br><br>", unsafe_allow_html=True)
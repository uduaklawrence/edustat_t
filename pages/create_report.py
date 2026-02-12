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
SUBSCRIPTION_AMOUNT = 20000.00  # ₦

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
</style>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# ------------------ SESSION DEFAULTS ------------------
st.session_state.setdefault("selected_main_group", None)
st.session_state.setdefault("selected_subgroup", None)
st.session_state.setdefault("invoice_ref", None)
st.session_state.setdefault("payment_verified", False)

# ------------------ COMPLETE REPORT STRUCTURE ------------------
report_structure = {
    "Demographic Analysis": {
        "icon": "👥",
        "subgroups": {
            "Age Distribution Analysis": "Analyzes candidate age ranges, trends, and appropriateness across exam years and types.",
            "Gender Equity Analysis": "Examines male-to-female ratios, gender balance trends, and distribution across exam types.",
            "Regional & Geographic Distribution": "Maps where candidates come from and migration patterns for education.",
            "Birth Cohort Analysis": "Examines age-appropriate enrollment and generational education patterns."
        }
    },
    "State Analysis": {
        "icon": "🗺️",
        "subgroups": {
            "State Enrollment & Registration": "Tracks state-level candidate registration, trends, and growth rates.",
            "State Infrastructure": "Analyzes schools and centres registered per state and capacity utilization.",
            "State Performance Comparison": "State-to-state performance comparison and quality indicators.",
            "State Subject Analysis": "Number of subjects registered by state and subject performance.",
            "State Examination Attendance": "State examination attendance rates and absenteeism patterns."
        }
    },
    "Candidate Registration Statistics": {
        "icon": "📋",
        "subgroups": {
            "Overall Registration Metrics": "Total candidate registration, enrollment trends, and forecasting.",
            "Subject Registration Patterns": "Number of subjects per candidate and subject combination analysis.",
            "Institutional Registration": "Number of schools and centres registered with growth trends.",
            "Registration Demographics": "Age, gender, and regional registration distribution patterns."
        }
    },
    "Candidate Performance Insights": {
        "icon": "🎯",
        "subgroups": {
            "Overall Performance Analysis": "Pass/fail rates, grade distribution, and performance trends.",
            "Credit Requirements Analysis": "Minimum required credits and credits with English & Mathematics.",
            "Result Release Statistics": "Result release patterns, withheld results, and processing timelines.",
            "Comparative Performance Analysis": "School, subject, state, and year-over-year performance comparison."
        }
    },
    "Subject Pattern Insights": {
        "icon": "📚",
        "subgroups": {
            "Subject Enrollment Statistics": "Subject registration numbers, popularity rankings, and trends.",
            "Subject Performance Analysis": "Results by subject, difficulty assessment, and pass/fail rates.",
            "Subject Comparisons": "Subject-to-subject performance and benchmark analysis.",
            "Subject Demographics": "Age, gender, and regional subject preference patterns."
        }
    },
    "Special Needs & Disability Insights": {
        "icon": "♿",
        "subgroups": {
            "Special Needs Registration": "Number of special needs candidates and registration trends.",
            "Special Needs Demographics": "Age, gender, and state distribution of special needs candidates.",
            "Special Needs Performance": "Average performance and achievement gap analysis.",
            "Special Needs Accessibility": "Centres with special needs support and accessibility patterns."
        }
    },
    "School & Centre Analysis": {
        "icon": "🏫",
        "subgroups": {
            "School & Centre Statistics": "Number of schools/centres, capacity utilization, and size distribution.",
            "Centre Performance Rankings": "Top/bottom performing centres and quality scorecard.",
            "Centre Distribution & Accessibility": "Centre distribution by state and urban vs rural analysis.",
            "Centre Capacity Analysis": "Centre size vs performance and optimal capacity analysis."
        }
    },
    "Examination & Academic Performance": {
        "icon": "📊",
        "subgroups": {
            "Exam Type Analysis": "School vs private exams distribution and preferences.",
            "Exam Type Performance": "Performance by exam type and quality indicators.",
            "Grade Distribution Analysis": "Overall grade distribution and patterns across variables.",
            "Examination Attendance": "Attendance rates, registration gaps, and absenteeism patterns."
        }
    },
    "Temporal Trends & Forecasting": {
        "icon": "📈",
        "subgroups": {
            "Year-over-Year Trends": "Enrollment and performance trends across years.",
            "Growth Rate Analysis": "Year-on-year percentage changes and growth patterns.",
            "Forecasting & Projections": "Future enrollment and performance trend predictions.",
            "Seasonal & Cyclical Patterns": "Seasonal registration and examination cycle analysis."
        }
    },
    "Cross-Dimensional Analysis": {
        "icon": "🔄",
        "subgroups": {
            "Gender-Subject Preference": "Gender biases in subject selection and STEM gender gaps.",
            "Gender-Performance Analysis": "Gender performance gaps and equity in outcomes.",
            "Age-Performance Correlation": "Optimal age for success and age-grade relationships.",
            "State-Performance Correlation": "State performance rankings and regional disparities.",
            "Multi-Variable Analysis": "Complex cross-dimensional insights and correlations."
        }
    },
    "Statistical Insights & Summaries": {
        "icon": "📉",
        "subgroups": {
            "Descriptive Statistics": "Mean, median, mode, variance, and outlier detection.",
            "Correlation Analysis": "Performance prediction factors and variable relationships.",
            "Distribution Analysis": "Normal distribution testing and data patterns.",
            "Advanced Analytics": "Regression analysis, trend analysis, and predictive modeling."
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
if 'selected_main_group' not in st.session_state or st.session_state.selected_main_group is None:
    st.session_state.selected_main_group = list(report_structure.keys())[0]

# Create clickable group tabs (first 6 groups)
cols = st.columns(6)
group_list = list(report_structure.items())
for idx in range(6):
    group_name, group_data = group_list[idx]
    with cols[idx]:
        if st.button(
            f"{group_data['icon']} {group_name}", 
            key=f"group_{idx}",
            use_container_width=True
        ):
            st.session_state.selected_main_group = group_name
            st.rerun()

# Second row of tabs (remaining groups)
st.markdown("<br>", unsafe_allow_html=True)
cols2 = st.columns(5)
for idx in range(6, len(group_list)):
    group_name, group_data = group_list[idx]
    with cols2[idx-6]:
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
                st.switch_page("pages/report_filters.py")

# Fill empty columns in last row
if len(row) < num_cols:
    for _ in range(num_cols - len(row)):
        with cols[len(row)]:
            st.empty()

st.markdown("<br><br>", unsafe_allow_html=True)
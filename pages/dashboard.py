import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from Analytics_layer import get_exam_dataset
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path to import auth_utils
sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import require_authentication, logout_user

# -------------------- AUTH CHECK --------------------
require_authentication()

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Edustat WAEC Dashboard", layout="wide", initial_sidebar_state="collapsed")

# -------------------- CUSTOM CSS --------------------
st.markdown("""
<style>
    /* Main container styling */
    .main {
        padding: 2rem 3rem;
        background-color: #ffffff;
            border:2px solid white;
    }
    
    /* Header styling */
    .welcome-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    
    /* KPI Card styling */
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        height: 100%;
        transition: transform 0.2s;
    }
    
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    
    .kpi-icon {
        background: #1e293b;
        color: white;
        width: 48px;
        height: 48px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.25rem;
    }
    
    .kpi-label {
        font-size: 0.95rem;
        color: #6c757d;
        font-weight: 500;
    }
    
    /* Section styling */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 2rem 0 1rem 0;
    }
    
    /* Filter section */
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* Chart container */
    .chart-container {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
    
    .chart-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
    }
    
    /* Table styling */
    .dataframe {
        border: none !important;
    }
    
    /* Activity card */
    .activity-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    
    .activity-item {
        display: flex;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid #e9ecef;
        cursor: pointer;
        transition: background 0.2s;
    }
    
    .activity-item:hover {
        background: #f8f9fa;
    }
    
    .activity-item:last-child {
        border-bottom: none;
    }
    
    .activity-icon {
        background: #1e293b;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 1rem;
        font-size: 1.2rem;
    }
    
    .activity-title {
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.25rem;
    }
    
    .activity-desc {
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        padding: 0.5rem 1.5rem;
        border: none;
        background: #1e293b;
        color: white;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: #0f172a;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_dataset():
    return get_exam_dataset()

df = load_dataset()

# -------------------- HEADER --------------------
col_header, col_logout = st.columns([6, 1])
with col_header:
    # Get username from session_state (set by cookie authentication)
    username = st.session_state.get('username', 'User')
    user_email = st.session_state.get('user_email', '')

    # Use email as fallback if username is not available
    if not username and user_email:
        username = user_email.split('@')[0].title()
        
    st.markdown(f'<div class="welcome-header">Welcome back, {username}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Here\'s your educational analytics overview</div>', unsafe_allow_html=True)

with col_logout:
    if st.button("🔓 Logout", key="logout_btn"):
        # Use the logout_user function from auth_utils
        logout_user()
        st.success("You have been logged out.")
        st.switch_page("pages/Landing.py")

# -------------------- KPI CARDS --------------------
total_candidates = len(df)
male_count = (df["Sex"].str.lower() == "male").sum()
female_count = (df["Sex"].str.lower() == "female").sum()
disability_count = df[(df["Disability"].notna()) & (df["Disability"] != "None")].shape[0]

col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">👥</div>
        <div class="kpi-value">{total_candidates:,}</div>
        <div class="kpi-label">Total Candidates</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">♂️</div>
        <div class="kpi-value">{male_count:,}</div>
        <div class="kpi-label">Males</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">♀️</div>
        <div class="kpi-value">{female_count:,}</div>
        <div class="kpi-label">Females</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">♿</div>
        <div class="kpi-value">{disability_count:,}</div>
        <div class="kpi-label">Disabilities</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------- FILTER SECTION --------------------
st.markdown('<div class="section-header">Select state to filter</div>', unsafe_allow_html=True)

col_filter, col_search = st.columns([1, 2], gap="large")

with col_filter:
    agg = df.groupby(["ExamYear", "State"]).size().reset_index(name="NumberOfCandidates")
    states = sorted(agg["State"].unique())
    selected_state = st.selectbox("", ["All states"] + states, key="state_filter", label_visibility="collapsed")

with col_search:
    st.text_input("🔍 Search reports, activities, or data...", key="search_box", label_visibility="collapsed")

# -------------------- QUICK INSIGHTS --------------------
st.markdown('<div class="section-header">Quick insights</div>', unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns(2, gap="large")

# Candidates per Year Chart
with col_chart1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Candidates per year</div>', unsafe_allow_html=True)
    
    yearly = df.groupby("ExamYear").size().reset_index(name="Count")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yearly["ExamYear"],
        y=yearly["Count"],
        marker_color='#1e293b',
        marker_line_color='#1e293b',
        marker_line_width=1.5,
        opacity=1
    ))
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=40),
        height=300,
        xaxis=dict(
            title="Exam year",
            showgrid=False,
            showline=True,
            linecolor='#e9ecef',
            title_font=dict(size=12, color='#6c757d')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#f1f3f5',
            showline=False,
            title=None
        ),
        font=dict(family="Arial, sans-serif", size=12, color="#1a1a1a"),
        bargap=0.3
    )
    
    st.plotly_chart(fig, use_container_width=True, key="yearly_chart")
    st.markdown('</div>', unsafe_allow_html=True)

# Gender Distribution Chart
with col_chart2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Male Vs Female</div>', unsafe_allow_html=True)
    
    gender = df["Sex"].value_counts().reset_index()
    gender.columns = ["Sex", "Count"]
    
    # Calculate percentages
    total = gender["Count"].sum()
    gender["Percentage"] = (gender["Count"] / total * 100).round(0).astype(int)
    
    fig = go.Figure(data=[go.Pie(
        labels=gender["Sex"],
        values=gender["Count"],
        hole=0.6,
        marker=dict(colors=['#1e293b', '#e2e8f0']),
        textposition='outside',
        texttemplate='%{percent}',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        showlegend=True
    )])
    
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=20, b=20),
        height=300,
        font=dict(family="Arial, sans-serif", size=12, color="#1a1a1a"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig, use_container_width=True, key="gender_chart")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- TOP EXAM CENTRES --------------------
st.markdown('<div class="section-header">Top Exam Centres</div>', unsafe_allow_html=True)

st.markdown('<div class="chart-container">', unsafe_allow_html=True)

top_centres = (
    df.groupby(["Centre", "State"])
    .size()
    .reset_index(name="Registered Candidates")
    .sort_values("Registered Candidates", ascending=False)
    .head(5)
    .reset_index(drop=True)
)

# Adjust index to start from 1
top_centres.index = top_centres.index + 1

# Display as styled table
st.dataframe(
    top_centres,
    use_container_width=True,
    hide_index=False,
    column_config={
        "Centre": st.column_config.TextColumn("Centre", width="large"),
        "State": st.column_config.TextColumn("State", width="medium"),
        "Registered Candidates": st.column_config.TextColumn("Registered Candidates", width="medium")
    }
)

st.markdown('</div>', unsafe_allow_html=True)

# -------------------- BOTTOM SECTION --------------------
col_activity, col_actions = st.columns([1.5, 1], gap="large")

# Recent Activity
with col_activity:
    st.markdown('<div class="section-header">Recent Activity</div>', unsafe_allow_html=True)
    st.markdown('<div style="color: #6c757d; margin-bottom: 1rem;">Your latest report activities</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="activity-card">', unsafe_allow_html=True)
    
    for i in range(4):
        st.markdown(f"""
        <div class="activity-item">
            <div class="activity-icon">⏱️</div>
            <div>
                <div class="activity-title">Generate Report</div>
                <div class="activity-desc">Create new analytics report</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("View All →", key="view_all_activity"):
        st.info("View all activities feature coming soon!")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Quick Actions
with col_actions:
    st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
    st.markdown('<div style="color: #6c757d; margin-bottom: 1rem;">Frequently used features</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="activity-card">', unsafe_allow_html=True)
    
    actions = [
        ("📊", "Generate Report", "Create new analytics report"),
        ("💾", "Saved Reports", "Access your saved reports"),
        ("🧾", "View Invoices", "Check payment history"),
        ("💳", "Payment methods", "Manage your payments")
    ]
    
    for icon, title, desc in actions:
        if st.button(f"{icon} {title}", key=f"action_{title}", use_container_width=True):
            if "Generate Report" in title:
                st.switch_page("pages/Create_Report.py")
            else:
                st.info(f"{title} feature coming soon!")
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
import streamlit as st
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add parent directory to path to import auth_utils
sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import require_authentication, logout_user

# Import granular dashboard functions (no more raw-row DataFrame)
from Analytics_layer import (
    get_dashboard_kpis,
    get_dashboard_yearly_chart,
    get_dashboard_gender_chart,
    get_dashboard_top_centres,
    get_dashboard_state_summary,
)

# -------------------- AUTH CHECK --------------------
require_authentication()

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="Edustat WAEC Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -------------------- CUSTOM CSS --------------------
st.markdown("""
<style>
#     :root {
#     --primary-blue: #1e293b;
#     --accent-blue: #2563eb;
#     --text-primary: #1a1a1a;
#     --text-secondary: #64748b;
#     --background-gray: #f8fafc;
#     --border-light: #e2e8f0;
# }
#     .stApp {
#     background-color: white !important;
#     color: var(--text-primary) !important;
# }
#     .stMarkdown, p, span, label, .stMetric {
#     color: var(--text-primary) !important;
# }
#     .report-section, .reports-container, .analysis-card {
#     background: white !important;
#     border: 1px solid var(--border-light) !important;
#     box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1) !important;
}                
    .main {
        padding: 2rem 3rem;
        background-color: #ffffff;
        border: 2px solid white;
    }
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
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 2rem 0 1rem 0;
    }
    .filter-section {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
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
    .activity-item:hover { background: #f8f9fa; }
    .activity-item:last-child { border-bottom: none; }
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
    .activity-desc { font-size: 0.9rem; color: #6c757d; }
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
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
col_header, col_logout = st.columns([6, 1])
with col_header:
    username   = st.session_state.get("username", "User")
    user_email = st.session_state.get("user_email", "")
    if not username and user_email:
        username = user_email.split("@")[0].title()

    st.markdown(
        f'<div class="welcome-header">Welcome back, {username}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Here\'s your educational analytics overview</div>',
        unsafe_allow_html=True,
    )

with col_logout:
    if st.button("🔓 Logout", key="logout_btn"):
        logout_user()
        st.success("You have been logged out.")
        st.switch_page("pages/Landing.py")


# -------------------- LOAD AGGREGATED DATA --------------------
# Each call returns a tiny object — no raw millions-of-rows DataFrames.
kpis         = get_dashboard_kpis()
yearly_df    = get_dashboard_yearly_chart()
gender_df    = get_dashboard_gender_chart()
top_centres  = get_dashboard_top_centres(top_n=5)
state_summary = get_dashboard_state_summary()

# Safety check — if KPIs all zero and yearly_df is empty, something went wrong
if kpis["total_candidates"] == 0 and yearly_df.empty:
    st.error("No data loaded. Check your parquet folder path in Analytics_layer.py")
    st.stop()


# -------------------- KPI CARDS --------------------
col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">👥</div>
        <div class="kpi-value">{kpis['total_candidates']:,}</div>
        <div class="kpi-label">Total Candidates</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">♂️</div>
        <div class="kpi-value">{kpis['male_count']:,}</div>
        <div class="kpi-label">Males</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">♀️</div>
        <div class="kpi-value">{kpis['female_count']:,}</div>
        <div class="kpi-label">Females</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">♿</div>
        <div class="kpi-value">{kpis['disability_count']:,}</div>
        <div class="kpi-label">Disabilities</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# -------------------- FILTER SECTION --------------------
st.markdown('<div class="section-header">Select state to filter</div>', unsafe_allow_html=True)

col_filter, col_search = st.columns([1, 2], gap="large")

with col_filter:
    # state_summary is a tiny aggregated df — safe to use directly
    states = sorted(state_summary["State"].unique()) if not state_summary.empty else []
    selected_state = st.selectbox(
        "Select a state",
        ["All states"] + states,
        key="state_filter",
        label_visibility="collapsed",
    )

with col_search:
    st.text_input(
        "🔍 Search reports, activities, or data...",
        key="search_box",
        label_visibility="collapsed",
    )


# -------------------- QUICK INSIGHTS --------------------
st.markdown('<div class="section-header">Quick insights</div>', unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns(2, gap="large")

# ── Candidates per Year ────────────────────────────────────────────────────────
with col_chart1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Candidates per year</div>', unsafe_allow_html=True)

    if not yearly_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=yearly_df["ExamYear"],
            y=yearly_df["Count"],
            marker_color="#1e293b",
            marker_line_color="#1e293b",
            marker_line_width=1.5,
            opacity=1,
        ))
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=40),
            height=300,
            xaxis=dict(
                title="Exam year",
                showgrid=False,
                showline=True,
                linecolor="#e9ecef",
                title_font=dict(size=12, color="#6c757d"),
                tickmode="array",
                tickvals=yearly_df["ExamYear"].tolist(),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#f1f3f5",
                showline=False,
                title=None,
            ),
            font=dict(family="Arial, sans-serif", size=12, color="#1a1a1a"),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True, key="yearly_chart")
    else:
        st.info("No yearly data available.")

    st.markdown("</div>", unsafe_allow_html=True)

# ── Gender Distribution ────────────────────────────────────────────────────────
with col_chart2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Male Vs Female</div>', unsafe_allow_html=True)

    if not gender_df.empty:
        fig = go.Figure(data=[go.Pie(
            labels=gender_df["Sex"],
            values=gender_df["Count"],
            hole=0.6,
            marker=dict(colors=["#1e293b", "#e2e8f0"]),
            textposition="outside",
            texttemplate="%{percent}",
            hovertemplate=(
                "<b>%{label}</b><br>Count: %{value}<br>"
                "Percentage: %{percent}<extra></extra>"
            ),
            showlegend=True,
        )])
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            font=dict(family="Arial, sans-serif", size=12, color="#1a1a1a"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
            ),
        )
        st.plotly_chart(fig, use_container_width=True, key="gender_chart")
    else:
        st.info("No gender data available.")

    st.markdown("</div>", unsafe_allow_html=True)


# -------------------- TOP EXAM CENTRES --------------------
st.markdown('<div class="section-header">Top Exam Centres</div>', unsafe_allow_html=True)
st.markdown('<div class="chart-container">', unsafe_allow_html=True)

if not top_centres.empty:
    st.dataframe(
        top_centres,
        use_container_width=True,
        hide_index=False,
        column_config={
            "centre": st.column_config.TextColumn("Centre", width="large"),
            "State":  st.column_config.TextColumn("State",  width="medium"),
            "Registered Candidates": st.column_config.NumberColumn(
                "Registered Candidates", width="medium"
            ),
        },
    )
else:
    st.info("No centre data available.")

st.markdown("</div>", unsafe_allow_html=True)


# -------------------- BOTTOM SECTION --------------------
col_activity, col_actions = st.columns([1.5, 1], gap="large")

# ── Recent Activity ────────────────────────────────────────────────────────────
with col_activity:
    st.markdown('<div class="section-header">Recent Activity</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color: #6c757d; margin-bottom: 1rem;">Your latest report activities</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="activity-card">', unsafe_allow_html=True)

    for _ in range(4):
        st.markdown("""
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

    st.markdown("</div>", unsafe_allow_html=True)

# ── Quick Actions ──────────────────────────────────────────────────────────────
with col_actions:
    st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="color: #6c757d; margin-bottom: 1rem;">Frequently used features</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="activity-card">', unsafe_allow_html=True)

    actions = [
        ("📊", "Create Report",   "pages/create_report.py"),
        ("💾", "Saved Reports",   "pages/my_reports.py"),
        ("🧾", "My Invoices",     "pages/my_invoices.py"),
        ("💳", "Payment Methods", None),
    ]

    for icon, title, page in actions:
        if st.button(f"{icon} {title}", key=f"action_{title}", use_container_width=True):
            if page:
                st.switch_page(page)
            else:
                st.info(f"{title} feature coming soon!")
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
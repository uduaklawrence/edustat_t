import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from Analytics_layer import (
    get_dashboard_kpis,           # Corrected name
    get_dashboard_yearly_chart,    # Corrected name
    get_dashboard_gender_chart,    # Corrected name
    get_dashboard_top_centres,     # Corrected name
    get_dashboard_state_summary,   # Corrected name
)
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import require_authentication, logout_user

require_authentication()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Edustat WAEC Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .legendtext { 
            fill: #1e293b !important;
    }        
    .main { padding: 2rem 3rem; background-color: #ffffff; }
    .welcome-header { font-size: 2.5rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0.5rem; }
    .subtitle { font-size: 1.1rem; color: #6c757d; margin-bottom: 2rem; }
    .kpi-card {
        background: white; border-radius: 12px; padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;
        height: 100%; transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
    .kpi-icon {
        background: #1e293b; color: white; width: 48px; height: 48px;
        border-radius: 8px; display: flex; align-items: center;
        justify-content: center; font-size: 1.5rem; margin-bottom: 1rem;
    }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #1a1a1a; margin-bottom: 0.25rem; }
    .kpi-label { font-size: 0.95rem; color: #6c757d; font-weight: 500; }
    .section-header { font-size: 1.5rem; font-weight: 600; color: #1a1a1a; margin: 2rem 0 1rem 0; }
    .chart-container {
        background: #ffffff !important; border-radius: 12px; padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1.5rem;
        border: 1px solid #e2e8f0 !important;
    }
    .chart-title { font-size: 1.2rem; font-weight: 600; color: #1a1a1a; margin-bottom: 1rem; }
    .stPlotlyChart > div { background: #ffffff !important; border-radius: 8px; }
    .activity-card { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1rem; border: 1px solid #e2e8f0; }
    .activity-item { display: flex; align-items: center; padding: 1rem; border-bottom: 1px solid #e9ecef; cursor: pointer; transition: background 0.2s; }
    .activity-item:hover { background: #f8f9fa; }
    .activity-item:last-child { border-bottom: none; }
    .activity-icon { background: #1e293b; color: white; width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-right: 1rem; font-size: 1.2rem; }
    .activity-title { font-weight: 600; color: #1a1a1a; margin-bottom: 0.25rem; }
    .activity-desc  { font-size: 0.9rem; color: #6c757d; }
    .stButton > button { border-radius: 8px; font-weight: 500; padding: 0.5rem 1.5rem; border: none; background: #1e293b; color: white; transition: all 0.2s; }
    .stButton > button:hover { background: #0f172a; transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CHART LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
def chart_layout(title: str = "") -> dict:
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",   
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color="#1e293b",  
        ),
        title=dict(
            text=title,
            font=dict(size=14, color="#1e293b"),
            x=0,
        ),
        margin=dict(l=50, r=30, t=60, b=80),
        height=350,
        xaxis=dict(
            showline=True,
            linecolor="#cbd5e1",
            tickfont=dict(color="#1e293b"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            tickfont=dict(color="#1e293b"),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.04, 
            xanchor="center",
            x=0.5,
            font=dict(color="#1e293b", size=12), 
            bgcolor="rgba(255,255,255,0)", 
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA (CORRECTED NAMES AND KEYS)
# ─────────────────────────────────────────────────────────────────────────────
stats       = get_dashboard_kpis()
yearly      = get_dashboard_yearly_chart()
gender      = get_dashboard_gender_chart()
top_centres = get_dashboard_top_centres(top_n=5)
agg         = get_dashboard_state_summary()

# Use the specific keys returned by Analytics_layer.py
total_candidates = stats["total_candidates"]
male_count       = stats["male_count"]
female_count     = stats["female_count"]
disability_count = stats["disability_count"]

# get_dashboard_state_summary returns a DF with "State" column
states = sorted(agg["State"].unique()) if not agg.empty else []


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
col_header, col_logout = st.columns([6, 1])
with col_header:
    username   = st.session_state.get("username", "")
    user_email = st.session_state.get("user_email", "")
    if not username and user_email:
        username = user_email.split("@")[0].title()
    st.markdown(f'<div class="welcome-header">Welcome back, {username}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Here\'s your educational analytics overview</div>', unsafe_allow_html=True)

with col_logout:
    if st.button("🔓 Logout", key="logout_btn"):
        logout_user()
        st.success("You have been logged out.")
        st.switch_page("pages/Landing.py")


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4, gap="medium")

for col, icon, value, label in [
    (col1, "👥", f"{total_candidates:,}", "Total Candidates"),
    (col2, "♂️", f"{male_count:,}",       "Males"),
    (col3, "♀️", f"{female_count:,}",     "Females"),
    (col4, "♿", f"{disability_count:,}", "Disabilities"),
]:
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# STATE FILTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Select state to filter</div>', unsafe_allow_html=True)

col_filter, col_search = st.columns([1, 2], gap="large")
with col_filter:
    selected_state = st.selectbox(
        "Filter by state",
        ["All states"] + states,
        key="state_filter",
        label_visibility="collapsed",
    )
with col_search:
    st.text_input(
        "Search reports",
        key="search_box",
        label_visibility="collapsed",
        placeholder="🔍 Search reports, activities, or data...",
    )


# ─────────────────────────────────────────────────────────────────────────────
# QUICK INSIGHTS — CHARTS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Quick insights</div>', unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns(2, gap="large")

with col_chart1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Candidates per year</div>', unsafe_allow_html=True)

    if not yearly.empty:
        yearly["ExamYear"] = yearly["ExamYear"].astype(int)

        if selected_state != "All states" and not agg.empty:
            state_yearly = (
                agg[agg["State"] == selected_state]
                .groupby("ExamYear")["NumberOfCandidates"]
                .sum()
                .reset_index()
                .rename(columns={"NumberOfCandidates": "Count"})
            )
            plot_df = state_yearly if not state_yearly.empty else yearly
        else:
            plot_df = yearly

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=plot_df["ExamYear"],
            y=plot_df["Count"],
            marker=dict(color="#2563eb", line=dict(color="#1d4ed8", width=1)),
            hovertemplate="<b>%{x}</b><br>Candidates: %{y:,}<extra></extra>",
        ))

        layout = chart_layout("Candidates per Exam Year")
        layout.update({
            "xaxis": {**layout.get("xaxis", {}), "title": "Exam year", "tickmode": "array", "tickvals": plot_df["ExamYear"].tolist(), "tickangle": -30},
            "yaxis": {**layout.get("yaxis", {}), "title": "Candidates"},
            "bargap": 0.3,
        })
        fig_bar.update_layout(**layout)
        st.plotly_chart(
            fig_bar,
            use_container_width=True, 
            theme= None,
            key="yearly_chart", 
            config={"displayModeBar": False})
    else:
        st.info("No yearly data available.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_chart2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">Male Vs Female</div>', unsafe_allow_html=True)

    if not gender.empty:
        GENDER_COLORS = {"Male": "#2563eb", "Female": "#db2777"}
        ordered_labels = [l for l in ["Male","Female"] if l in gender["Sex"].values]
        gender_ordered = gender.set_index("Sex").reindex(ordered_labels).reset_index()
        bar_colors = [GENDER_COLORS.get(s, "#64748b") for s in gender_ordered["Sex"]]

        fig_pie = go.Figure(data=[go.Pie(
            labels=gender_ordered["Sex"],
            values=gender_ordered["Count"],
            hole=0.55,
            marker=dict(colors=bar_colors, line=dict(color="white", width=3)),
            textposition="outside",
            texttemplate="%{percent}",
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>%{percent}<extra></extra>",
            showlegend=True,
        )])

        pie_layout = chart_layout("")
        pie_layout.update({
            "height": 320,
             "showlegend": True,
             "legend": dict(
                 orientation="h", 
                 yanchor="bottom", 
                 y=-0.2, 
                 xanchor="center", 
                 x=0.5, 
                 font=dict(color="#1e293b", size=12))})
        fig_pie.update_layout(**pie_layout)
        st.plotly_chart(
            fig_pie, 
            use_container_width=True,
            theme= None,
            key="gender_chart", 
            config={"displayModeBar": False})
    else:
        st.info("No gender data available.")
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TOP EXAM CENTRES TABLE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Top Exam Centres</div>', unsafe_allow_html=True)
st.markdown('<div class="chart-container">', unsafe_allow_html=True)

if not top_centres.empty:
    st.dataframe(
        top_centres,
        use_container_width=True,
        hide_index=False,
        column_config={
            "centre": st.column_config.TextColumn("Centre", width="large"),
            "State": st.column_config.TextColumn("State", width="medium"),
            "Registered Candidates": st.column_config.NumberColumn("Registered Candidates", width="medium", format="%d"),
        },
    )
else:
    st.info("No centre data available.")
st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# BOTTOM SECTION
# ─────────────────────────────────────────────────────────────────────────────
col_activity, col_actions = st.columns([1.5, 1], gap="large")

with col_activity:
    st.markdown('<div class="section-header">Recent Activity</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#6c757d;margin-bottom:1rem;">Your latest report activities</div>', unsafe_allow_html=True)
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
        st.info("View all activities coming soon!")
    st.markdown("</div>", unsafe_allow_html=True)

with col_actions:
    st.markdown('<div class="section-header">Quick Actions</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#6c757d;margin-bottom:1rem;">Frequently used features</div>', unsafe_allow_html=True)
    st.markdown('<div class="activity-card">', unsafe_allow_html=True)

    actions = [
        ("📊", "Create New Report",  "pages/create_report.py"),
        ("💾", "Saved Reports",      "pages/my_reports.py"),
        ("🧾", "My Invoices",        "pages/my_invoices.py"),
        ("💳", "Payment Methods",    None),
    ]

    for icon, title, page in actions:
        if st.button(f"{icon} {title}", key=f"action_{title}", use_container_width=True):
            if page:
                st.switch_page(page)
            else:
                st.info(f"{title} coming soon!")
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
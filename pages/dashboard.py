import streamlit as st
import plotly.express as px
from db_queries import fetch_data

# -------------------- AUTH CHECK --------------------
if not st.session_state.get('logged_in', False):
    st.warning("Please sign in to view the dashboard.")
    st.switch_page("pages/Login.py")
    st.stop()

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Edustat WAEC Dashboard", layout="wide")

# -------------------- HEADER --------------------
col1, col2 = st.columns([6, 1])
with col1:
    st.title("🎓 Edustat WAEC — Dashboard")

with col2:
    # Logout button in top-right corner
    if st.button("🔓 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.success("You have been logged out.")
        st.switch_page("pages/Landing.py")

st.markdown("---")  # nice visual separator

# -------------------- KPI CARDS --------------------
kpi_query = "SELECT Sex, COUNT(*) AS Count FROM exam_candidates GROUP BY Sex"
kpi_df = fetch_data(kpi_query)

total_candidates = kpi_df['Count'].sum() if not kpi_df.empty else 0
male_count = kpi_df[kpi_df['Sex'] == 'Male']['Count'].sum() if not kpi_df.empty else 0
female_count = kpi_df[kpi_df['Sex'] == 'Female']['Count'].sum() if not kpi_df.empty else 0

disability_query = "SELECT COUNT(*) AS Count FROM exam_candidates WHERE Disability IS NOT NULL AND Disability != 'None'"
disability_count = fetch_data(disability_query)['Count'].values[0] if not fetch_data(disability_query).empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("👥 Total Candidates", f"{total_candidates:,}")
col2.metric("♂️ Males", f"{male_count:,}")
col3.metric("♀️ Females", f"{female_count:,}")
col4.metric("♿ Disabilities", f"{disability_count:,}")

# -------------------- DATA INSPECT --------------------
st.header("🔍 Inspect the Data")
df = fetch_data("SELECT * FROM exam_candidates LIMIT 10")
st.dataframe(df)

# -------------------- QUICK INSIGHTS --------------------
st.header("📊 Quick Insights")
col1, col2, col3 = st.columns(3)

# Candidates per Year
with col1:
    yearly_df = fetch_data("SELECT ExamYear, COUNT(*) AS Count FROM exam_candidates GROUP BY ExamYear")
    if not yearly_df.empty:
        fig = px.bar(yearly_df, x='ExamYear', y='Count', color='ExamYear', title="Candidates per Year")
        st.plotly_chart(fig, use_container_width=True)

# Gender distribution
with col2:
    if not kpi_df.empty:
        fig = px.pie(kpi_df, values='Count', names='Sex', hole=0.3, title="Overall Male vs Female")
        st.plotly_chart(fig, use_container_width=True)

# Top 3 Centres
with col3:
    centres_df = fetch_data("SELECT Centre, COUNT(*) AS Count FROM exam_candidates GROUP BY Centre ORDER BY COUNT(*) DESC LIMIT 3")
    if not centres_df.empty:
        fig = px.bar(centres_df, x='Centre', y='Count', color='Centre', title="Top 3 Centres")
        st.plotly_chart(fig, use_container_width=True)

# -------------------- REPORT LINK --------------------
st.subheader("📑 Create Custom Reports")
st.write("Click below to create and download reports with your filters and visualizations.")
if st.button("Go to Create Report"):
    st.switch_page("pages/Create_Report.py")
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
# Modify the query to summarize data based on ExamYear and State
aggregated_query = """
SELECT ExamYear, State, COUNT(*) AS NumberOfCandidates
FROM exam_candidates
GROUP BY ExamYear, State
"""
aggregated_data = fetch_data(aggregated_query)
 
# Create a dropdown for state selection
states = aggregated_data['State'].unique()  # Get unique states
selected_state = st.selectbox('Select State to Filter', options=['All States'] + list(states))
 
# Apply filter based on selected state
if selected_state != 'All States':
    aggregated_data = aggregated_data[aggregated_data['State'] == selected_state]
 
# Display the table without the 'State' column
aggregated_data = aggregated_data.drop(columns=['State'])

# ✅ Make index start from 1 (display only)
df_display = aggregated_data.reset_index(drop=True)
df_display.index = df_display.index + 1
st.dataframe(df_display)
 
# -------------------- QUICK INSIGHTS --------------------
st.header("📊 Quick Insights")
col1, col2 = st.columns(2)
 
# Candidates per Year
with col1:
    yearly_df = fetch_data("SELECT ExamYear, COUNT(*) AS Count FROM exam_candidates GROUP BY ExamYear")
    if not yearly_df.empty:
        fig = px.bar(yearly_df, x='ExamYear', y='Count', color='ExamYear', title="Candidates per Year")
        st.plotly_chart(fig,config= {'displayModeBar': False}, width='stretch')
 
# Gender distribution
with col2:
    if not kpi_df.empty:
        fig = px.pie(kpi_df, values='Count', names='Sex', hole=0.3, title="Overall Male vs Female")
        st.plotly_chart(fig,config= {'displayModeBar': False}, width='stretch')
 
# Top 3 Centres
st.markdown("---")
st.subheader("Top 3 Centres")
centres_df = fetch_data("SELECT Centre, State, COUNT(*) AS Registered_candidates FROM exam_candidates GROUP BY Centre, State ORDER BY COUNT(*) DESC LIMIT 3")
centres_display = centres_df.reset_index(drop=True)
centres_display.index = centres_display.index + 1
# Display the result as a table
st.dataframe(centres_display)
 
# -------------------- REPORT LINK --------------------
st.subheader("📑 Create Custom Reports")
st.write("Click below to create and download reports with your filters and visualizations.")
if st.button("Go to Create Report"):
    st.switch_page("pages/Create_Report.py")
import streamlit as st
import plotly.express as px
from Analytics_layer import get_exam_dataset
import pandas as pd
 
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

@st.cache_data(show_spinner=False)
def load_dataset():
    return get_exam_dataset()

df = load_dataset()

# -------------------- KPI CARDS --------------------
total_candidates = len(df)

male_count = (df["Sex"].str.lower() == "male").sum()
female_count = (df["Sex"].str.lower() == "female").sum()

disability_count = df[
    (df["Disability"].notna()) & (df["Disability"] != "None")
].shape[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("👥 Total Candidates", f"{total_candidates:,}")
col2.metric("♂️ Males", f"{male_count:,}")
col3.metric("♀️ Females", f"{female_count:,}")
col4.metric("♿ Disabilities", f"{disability_count:,}")
 
# -------------------- DATA INSPECT --------------------
st.header("🔍 Inspect the Data")

agg = df.groupby(["ExamYear", "State"]).size().reset_index(name="NumberOfCandidates")

states = sorted(agg["State"].unique())
selected_state = st.selectbox("Select State to Filter", ["All States"] + states)

if selected_state != "All States":
    agg = agg[agg["State"] == selected_state]

display_df = agg.drop(columns=["State"]).reset_index(drop=True)
display_df.index += 1

st.dataframe(display_df)
 
# -------------------- QUICK INSIGHTS --------------------
st.header("📊 Quick Insights")
col1, col2 = st.columns(2)
 
# Candidates per Year
with col1:
    yearly = df.groupby("ExamYear").size().reset_index(name="Count")
    fig = px.bar(yearly, x="ExamYear", y="Count", title="Candidates per Year")
    st.plotly_chart(fig, use_container_width=True)
 
# Gender distribution
with col2:
    gender = df["Sex"].value_counts().reset_index()
    gender.columns = ["Sex", "Count"]
    fig = px.pie(gender, values="Count", names="Sex", hole=0.3, title="Male vs Female")
    st.plotly_chart(fig, use_container_width=True)
 
# Top 3 Centres
st.markdown("---")
st.subheader("Top 3 Centres")

top_centres = (
    df.groupby(["Centre", "State"])
    .size()
    .reset_index(name="Registered_candidates")
    .sort_values("Registered_candidates", ascending=False)
    .head(3)
)

top_centres.index += 1
st.dataframe(top_centres)
 
# -------------------- REPORT LINK --------------------
st.subheader("📑 Create Custom Reports")
st.write("Click below to create and download reports with your filters and visualizations.")
if st.button("Go to Create Report"):
    st.switch_page("pages/Create_Report.py")
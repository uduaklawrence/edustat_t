# pages/view_report.py — Option B (Modern Redesign)
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
<<<<<<< HEAD
from watermark import add_watermark
import tempfile
=======
import warnings

# Suppress deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
>>>>>>> 62568dbb339c9b90cbfb3dd6246d25190e793591

# Page setup
st.set_page_config(page_title="View Report", layout="wide")
st.title("📄 View Report")

# If user came from history
history_mode = st.session_state.get("history_mode", False)

# Required session keys unless coming from history
if not history_mode:
    if not st.session_state.get("logged_in", False):
        st.warning("Please sign in to access this page.")
        st.stop()

    if not st.session_state.get("payment_verified", False):
        st.warning("You must complete payment before viewing this report.")
        st.stop()

# Data check
if "filtered_df" not in st.session_state:
    st.warning("No report data found. Please generate a new report.")
    st.stop()

df = st.session_state["filtered_df"]
saved_group = st.session_state.get("saved_group", "Custom Report")
saved_charts = st.session_state.get("saved_charts", ["Table/Matrix"])

<<<<<<< HEAD
st.success(f"Showing report for **{saved_group}**")

# Preview
st.subheader("📊 Preview of Data Used")
st.dataframe(df, use_container_width=True)
=======
# --- Quick Metrics ---
st.markdown("### 📌 Key Metrics")
col1, col2 = st.columns(2)
with col1:
 st.metric("Total Candidates", len(df))
with col2:
 if "Sex" in df.columns:
    female_pct = (df["Sex"].str.lower().eq("female").mean() * 100)
    st.metric("Female Representation", f"{female_pct:.1f}%")

# -------------------------------
# GLOBAL COLOR PALETTE
# -------------------------------
COLOR_PALETTE = ["#0078D7", "#FFA500", "#FFFFFF"]

# -------------------------------
# DATA PREVIEW
# -------------------------------
st.subheader("📊 Candidates Report")
summary_items = []

# Total candidates 
summary_items.append(("Total Candidates", len(df)))

# ExamYear (frequency)
if "ExamYear" in df.columns:
    year_counts = df["ExamYear"].value_counts().sort_index()
    for year, count in year_counts.items():
        summary_items.append((f"Exam Year {year}", count))

# Sex distribution
if "Sex" in df.columns:
    sex_counts = df["Sex"].value_counts()
    for k, v in sex_counts.items():
        summary_items.append((f"Sex — {k}", v))

# Disability
if "Disability" in df.columns:
    dis_counts = df["Disability"].value_counts()
    for k, v in dis_counts.items():
        summary_items.append((f"Disability — {k}", v))

# Age (most common age)
if "Age" in df.columns:
    age_counts = df["Age"].value_counts().sort_values(ascending=False)
    top_age = age_counts.index[0]
    top_age_count = age_counts.iloc[0]
    summary_items.append((f"Common Age", f"{top_age} years ({top_age_count} candidates)"))

# Render summary cleanly
for metric, value in summary_items:
    st.markdown(f"""
    <div style="
        padding:12px; 
        margin-bottom:8px; 
        background:#f9f9f9; 
        border-left: 6px solid #0078D7;
        border-radius:6px;
    ">
        <b>{metric}:</b> {value}
    </div>
    """, unsafe_allow_html=True)

# 👉 Needed for PDF generation
summary_df = pd.DataFrame(summary_items, columns=["Metric", "Value"])
>>>>>>> 62568dbb339c9b90cbfb3dd6246d25190e793591

# ------- Auto Visuals (same as your original, lighter formatting) -------
COLOR_PALETTE = ["#0078D7", "#FFA500", "#FFFFFF"]
chart_images = []

<<<<<<< HEAD
def plot_and_capture(fig):
    st.plotly_chart(fig, use_container_width=True)
=======
def safe_plot(fig):
    """Render and export chart safely."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        st.plotly_chart(fig, width='stretch')

    tmp_path = None
>>>>>>> 62568dbb339c9b90cbfb3dd6246d25190e793591
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.write_image(tmp.name)
            return tmp.name
    except:
        return None

<<<<<<< HEAD
# Basic metric section
st.markdown("## 🧠 Quick Insights")
st.metric("Total Records", len(df))

if "Sex" in df.columns:
    female_pct = (df["Sex"].str.lower() == "female").mean() * 100
    st.metric("Female Representation", f"{female_pct:.1f}%")

# Group-specific insights
=======
# --- Insights by Group ---
>>>>>>> 62568dbb339c9b90cbfb3dd6246d25190e793591
if saved_group == "Demographic Analysis":
    st.subheader("Demographic Breakdown")

    if "Sex" in df.columns:
        fig = px.pie(df, names="Sex", hole=0.3, title="Gender Distribution",
                     color_discrete_sequence=COLOR_PALETTE)
        chart_images.append(plot_and_capture(fig))

    if "Age" in df.columns:
        fig = px.histogram(df, x="Age", title="Age Distribution", nbins=12)
        chart_images.append(plot_and_capture(fig))

# more insight categories can be added…

# PDF Generation
@st.cache_data
def generate_pdf(df, title, charts):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    )
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Spacer(1, 12)
    ]

    data = [df.columns.tolist()] + df.values.tolist()
    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)

    for chart_path in charts:
        elements.append(PageBreak())
        elements.append(Image(chart_path, width=600, height=300))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        SimpleDocTemplate(tmp.name, pagesize=landscape(A4)).build(elements)
        return tmp.name

# Download Report PDF
st.markdown("---")
st.subheader("📥 Download Report PDF")

if chart_images:
<<<<<<< HEAD
    pdf_path = generate_pdf(df, saved_group, chart_images)
    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 Download Report PDF",
            data=f,
=======
    pdf_path = generate_pdf(summary_df, f"{saved_group} Summary Report", chart_images)
    with open(pdf_path, "rb") as pdf_file:
        # add watermark to PDF
        pdf_bytes = BytesIO(pdf_file.read())
        pdf_bytes.seek(0)

        # apply watermark
    pdf = add_watermark(input_pdf_stream=pdf_bytes, watermark_image_path="altered_edustat.jpg")

    st.download_button(
            label="📄 Download Report as PDF",
            data=pdf,
>>>>>>> 62568dbb339c9b90cbfb3dd6246d25190e793591
            file_name=f"{saved_group.replace(' ', '_')}_report.pdf",
            mime="application/pdf"
        )
else:
    st.info("Add or generate a chart to enable PDF export.")

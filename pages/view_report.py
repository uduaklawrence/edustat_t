import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
import io

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(page_title="View Report", layout="wide")
st.title("📄 View and Export Report")

# -------------------------------
# SESSION VALIDATION
# -------------------------------
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please sign in to access this page.")
    st.stop()

if not st.session_state.get("payment_verified", False):
    st.warning("⚠️ You must complete payment to view this report.")
    st.stop()

# -------------------------------
# LOAD SAVED STATE FROM CREATE REPORT
# -------------------------------
saved_group = st.session_state.get("saved_group", "General Report")
saved_columns = st.session_state.get("saved_columns", [])
saved_filters = st.session_state.get("saved_filters", {})
saved_charts = st.session_state.get("saved_charts", ["Table/Matrix"])

# Load dataset
if "filtered_df" in st.session_state:
    df = st.session_state["filtered_df"]
else:
    st.warning("No filtered data found. Please go back and create a report first.")
    st.stop()

st.success(f"✅ Showing results for: **{saved_group}**")

# -------------------------------
# DATA PREVIEW
# -------------------------------
st.subheader("📊 Filtered Dataset Preview")
st.dataframe(df, use_container_width=True)

# -------------------------------
# VISUALIZATION SECTION (UPDATED)
# -------------------------------
st.subheader("📈 Visualization Options")

# Initialize visualization storage
if "visualizations" not in st.session_state:
    st.session_state.visualizations = []

# --- Add new chart form ---
with st.form("add_chart_form", clear_on_submit=True):
    chart_type = st.selectbox(
        "Select Chart Type",
        ["Bar Chart", "Pie Chart", "Line Chart"],
        index=0,
        key="chart_type_select"
    )

    x_col = st.selectbox("Select X-axis Column", df.columns, key="x_col_select")
    y_col = st.selectbox("Select Y-axis Column", df.columns, key="y_col_select")

    submitted = st.form_submit_button("➕ Add Visual")

    if submitted:
        st.session_state.visualizations.append({
            "type": chart_type,
            "x": x_col,
            "y": y_col
        })
        st.success(f"✅ Added {chart_type} ({x_col} vs {y_col})")

# --- Display all added charts ---
chart_images = []

if st.session_state.visualizations:
    st.subheader("📊 Your Visuals")

    for idx, chart in enumerate(st.session_state.visualizations):
        chart_type = chart["type"]
        x_col = chart["x"]
        y_col = chart["y"]

        st.markdown(f"### {idx + 1}. {chart_type} — {x_col} vs {y_col}")

        # Generate chart figure
        try:
            if chart_type == "Bar Chart":
                fig = px.bar(df, x=x_col, y=y_col, color=x_col, title=f"{saved_group} - Bar Chart ({x_col} vs {y_col})")
            elif chart_type == "Pie Chart":
                fig = px.pie(df, values=y_col, names=x_col, hole=0.3, title=f"{saved_group} - Pie Chart ({x_col} vs {y_col})")
            elif chart_type == "Line Chart":
                fig = px.line(df, x=x_col, y=y_col, markers=True, title=f"{saved_group} - Line Chart ({x_col} vs {y_col})")
            else:
                continue

            st.plotly_chart(fig, use_container_width=True)

            # Safer image export (fix Kaleido timeout)
            tmp_chart = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            fig.write_image(tmp_chart.name, format="png", engine="kaleido", scale=2, width=800, height=400)
            chart_images.append(tmp_chart.name)

        except Exception as e:
            st.error(f"Error rendering {chart_type}: {e}")

        # Delete button for individual visuals
        if st.button(f"🗑️ Delete '{chart_type} ({x_col} vs {y_col})'", key=f"del_{idx}"):
            st.session_state.visualizations.pop(idx)
            st.rerun()

    # Button to clear all visuals
    if st.button("🧹 Clear All Visuals"):
        st.session_state.visualizations = []
        st.rerun()

else:
    st.info("No visuals added yet. Use the form above to add one.")

# -------------------------------
# PDF GENERATION FUNCTION
# -------------------------------
def generate_pdf(dataframe, title, chart_paths):
    """Generate styled PDF with title, table, and charts (each chart on a new page)."""

    styles = getSampleStyleSheet()
    report_title = Paragraph(f"<b>{title}</b>", styles["Title"])
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_on = Paragraph(f"Generated on: {date_str}", styles["Normal"])

    data = [dataframe.columns.tolist()] + dataframe.values.tolist()
    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        doc = SimpleDocTemplate(tmpfile.name, pagesize=landscape(A4))
        elements = [
            report_title,
            Spacer(1, 12),
            generated_on,
            Spacer(1, 12),
            Paragraph("<b>Filtered Data Summary</b>", styles["Heading2"]),
            Spacer(1, 6),
            table,
        ]

        # Add each chart on a new page for clarity
        for path in chart_paths:
            elements.append(PageBreak())
            elements.append(Paragraph("<b>Chart Visualization</b>", styles["Heading2"]))
            elements.append(Spacer(1, 12))
            elements.append(Image(path, width=600, height=300))

        doc.build(elements)
        return tmpfile.name

# -------------------------------
# PDF DOWNLOAD SECTION
# -------------------------------
st.subheader("📥 Download Report")

if chart_images:
    pdf_path = generate_pdf(df, f"{saved_group} Report", chart_images)

    with open(pdf_path, "rb") as pdf_file:
        st.download_button(
            label="📄 Download Report as PDF",
            data=pdf_file,
            file_name=f"{saved_group.replace(' ', '_')}_report.pdf",
            mime="application/pdf"
        )

    st.success("✅ Your report is ready to download with all visuals.")
else:
    st.warning("⚠️ Add at least one chart to include visuals in your PDF report.")

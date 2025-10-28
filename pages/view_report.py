import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

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

# Assume that the filtered dataset has been saved to session (from create_report)
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
# VISUALIZATION SECTION
# -------------------------------
st.subheader("📈 Visualization Options")

chart_type = st.selectbox(
    "Select Chart Type",
    ["Bar Chart", "Pie Chart", "Line Chart"],
    index=0
)

x_col = st.selectbox("Select X-axis Column", df.columns)
y_col = st.selectbox("Select Y-axis Column", df.columns)

chart_images = []

if chart_type == "Bar Chart":
    fig = px.bar(df, x=x_col, y=y_col, color=x_col, title=f"{saved_group} - Bar Chart")
    st.plotly_chart(fig, use_container_width=True)

    tmp_bar = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.write_image(tmp_bar.name)
    chart_images.append(tmp_bar.name)

elif chart_type == "Pie Chart":
    fig = px.pie(df, values=y_col, names=x_col, hole=0.3, title=f"{saved_group} - Pie Chart")
    st.plotly_chart(fig, use_container_width=True)

    tmp_pie = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.write_image(tmp_pie.name)
    chart_images.append(tmp_pie.name)

elif chart_type == "Line Chart":
    fig = px.line(df, x=x_col, y=y_col, markers=True, title=f"{saved_group} - Line Chart")
    st.plotly_chart(fig, use_container_width=True)

    tmp_line = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.write_image(tmp_line.name)
    chart_images.append(tmp_line.name)

# -------------------------------
# PDF GENERATION FUNCTION
# -------------------------------
def generate_pdf(dataframe, title, chart_paths):
    """Generate a styled PDF report including title, table, and charts."""

    styles = getSampleStyleSheet()
    report_title = Paragraph(f"<b>{title}</b>", styles["Title"])
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_on = Paragraph(f"Generated on: {date_str}", styles["Normal"])

    # Convert DataFrame to table
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

    # Build PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        doc = SimpleDocTemplate(tmpfile.name, pagesize=landscape(A4))
        elements = [
            report_title,
            Spacer(1, 12),
            generated_on,
            Spacer(1, 12),
            Paragraph("<b>Filtered Data Summary</b>", styles["Heading2"]),
            Spacer(1, 6),
            table
        ]

        for path in chart_paths:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("<b>Chart Visualization</b>", styles["Heading2"]))
            elements.append(Image(path, width=600, height=300))

        doc.build(elements)
        return tmpfile.name

# -------------------------------
# PDF DOWNLOAD SECTION
# -------------------------------
st.subheader("📥 Download Report")

pdf_path = generate_pdf(df, f"{saved_group} Report", chart_images)

with open(pdf_path, "rb") as pdf_file:
    st.download_button(
        label="📄 Download Report as PDF",
        data=pdf_file,
        file_name=f"{saved_group.replace(' ', '_')}_report.pdf",
        mime="application/pdf"
    )

st.success("✅ Your report is ready to download with the selected chart and filters.")

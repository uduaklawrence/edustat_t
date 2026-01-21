# 📄 VIEW REPORT 
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from watermark import add_watermark
from io import BytesIO
from report_summary import generate_report_summary

# PAGE CONFIGURATION
st.set_page_config(page_title="View Report - Edustat", layout="wide")

# -------------------- CUSTOM CSS --------------------
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling */
    .main {
        padding: 2rem 3rem;
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    .page-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .page-subtitle {
        font-size: 1.1rem;
        color: #6c757d;
        margin-bottom: 2rem;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 2rem 0 1rem 0;
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
    
    /* Summary box */
    .summary-box {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
    
    .summary-item {
        padding: 12px;
        margin-bottom: 8px;
        background: #f9f9f9;
        border-left: 6px solid #1e293b;
        border-radius: 6px;
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
    
    /* Download button special styling */
    .download-btn {
        background: #28a745 !important;
    }
    
    .download-btn:hover {
        background: #218838 !important;
    }
    
    /* Alert styling */
    .stAlert {
        border-radius: 8px;
        border-left-width: 4px;
    }
    
    /* Info banner */
    .info-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .info-banner h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    .info-banner p {
        margin: 0;
        opacity: 0.95;
    }
    
    /* Form styling */
    .stSelectbox > div > div {
        border-radius: 8px;
        border-color: #e2e8f0;
    }
    
    /* Dataframe styling */
    .dataframe {
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# SESSION VALIDATION
# =========================================================
def require_session(keys):
    """Ensure required session keys are set, else stop execution."""
    for key, message in keys.items():
        if not st.session_state.get(key, False):
            st.warning(message)
            if st.button("← Go Back to Create Report"):
                st.switch_page("pages/create_report.py")
            st.stop()

require_session({
    "logged_in": "⚠️ Please sign in to access this page.",
    "payment_verified": "⚠️ You must complete payment to view this report.",
    "report_ready": "⚠️ No report data available. Please create a report first."
})

# =========================================================
# LOAD SAVED STATE FROM CREATE REPORT
# =========================================================
saved_group = st.session_state.get("saved_group", "General Report")
saved_columns = st.session_state.get("saved_columns", [])
saved_filters = st.session_state.get("saved_filters", {})
saved_charts = st.session_state.get("saved_charts", ["Table/Matrix"])

# Check for filtered data
if "filtered_df" not in st.session_state or st.session_state.filtered_df is None:
    st.error("❌ No filtered data found. Please go back and create a report first.")
    if st.button("← Go Back to Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

df = st.session_state["filtered_df"]

if df.empty:
    st.warning("⚠️ The filtered dataset is empty. Please adjust your filters.")
    if st.button("← Go Back to Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

# =========================================================
# HEADER SECTION
# =========================================================
username = st.session_state.get('user_email', 'User').split('@')[0].title()
st.markdown(f'<div class="page-header">View Report: {saved_group}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="page-subtitle">Generated for {username} • {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>', unsafe_allow_html=True)

# Success banner
st.markdown(f"""
<div class="info-banner">
    <h3>✅ Report Ready</h3>
    <p>Showing results for <strong>{saved_group}</strong> with {len(df):,} total records</p>
</div>
""", unsafe_allow_html=True)

# =========================================================
# CALCULATE METRICS
# =========================================================
top_age = df['Age'].mode()[0] if 'Age' in df.columns and not df['Age'].empty else "N/A"
female_pct = (df["Sex"].str.lower().eq("female").sum() / len(df) * 100) if "Sex" in df.columns else 0
female_pct = round(female_pct, 0)
top_state = df['State'].mode()[0] if 'State' in df.columns and not df['State'].empty else "N/A"
top_state_count = df["State"].value_counts().get(top_state, 0) if top_state != "N/A" else 0
peak_year = df['ExamYear'].mode()[0] if 'ExamYear' in df.columns and not df['ExamYear'].empty else "N/A"

metrics = {
    "modal_age": top_age,
    "female_pct": female_pct,
    "top_state": top_state,
    "top_state_count": top_state_count,
    "peak_year": peak_year,
}

# Generate report summary
summary_text = generate_report_summary(
    report_group=saved_group,
    total_records=len(df),
    metrics=metrics,
    applied_filters=saved_filters
)

# =========================================================
# KEY METRICS CARDS
# =========================================================
st.markdown('<div class="section-header">📊 Overview Metrics</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">👥</div>
        <div class="kpi-value">{len(df):,}</div>
        <div class="kpi-label">Total Candidates</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    if "Sex" in df.columns:
        female_count = df["Sex"].str.lower().eq("female").sum()
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">♀️</div>
            <div class="kpi-value">{female_count:,}</div>
            <div class="kpi-label">Female ({female_pct:.0f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-icon">♀️</div>
            <div class="kpi-value">N/A</div>
            <div class="kpi-label">Female</div>
        </div>
        """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">📍</div>
        <div class="kpi-value">{top_state}</div>
        <div class="kpi-label">Top State</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">📅</div>
        <div class="kpi-value">{peak_year}</div>
        <div class="kpi-label">Peak Year</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# REPORT SUMMARY
# =========================================================
st.markdown('<div class="section-header">📋 Report Summary</div>', unsafe_allow_html=True)

st.markdown('<div class="summary-box">', unsafe_allow_html=True)
st.markdown(f"""
<div style="font-size: 1rem; line-height: 1.8; color: #374151;">
{summary_text}
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# DATA SUMMARY BREAKDOWN
# =========================================================
st.markdown('<div class="section-header">📈 Data Breakdown</div>', unsafe_allow_html=True)

summary_items = []

# Total candidates
summary_items.append(("Total Candidates", f"{len(df):,}"))

# ExamYear distribution
if "ExamYear" in df.columns:
    year_counts = df["ExamYear"].value_counts().sort_index()
    for year, count in year_counts.items():
        summary_items.append((f"Exam Year {year}", f"{count:,}"))

# Sex distribution
if "Sex" in df.columns:
    sex_counts = df["Sex"].value_counts()
    for k, v in sex_counts.items():
        summary_items.append((f"Sex — {k}", f"{v:,}"))

# Disability
if "Disability" in df.columns:
    dis_counts = df["Disability"].value_counts()
    for k, v in dis_counts.items():
        summary_items.append((f"Disability — {k}", f"{v:,}"))

# Age (most common age)
if "Age" in df.columns:
    age_counts = df["Age"].value_counts().sort_values(ascending=False)
    if not age_counts.empty:
        top_age_val = age_counts.index[0]
        top_age_count = age_counts.iloc[0]
        summary_items.append(("Modal Age", f"{top_age_val} years ({top_age_count:,} candidates)"))

# Render summary
st.markdown('<div class="summary-box">', unsafe_allow_html=True)
for metric, value in summary_items:
    st.markdown(f"""
    <div class="summary-item">
        <b>{metric}:</b> {value}
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Create summary DataFrame for PDF
summary_df = pd.DataFrame(summary_items, columns=["Metric", "Value"])

# =========================================================
# GLOBAL COLOR PALETTE
# =========================================================
COLOR_PALETTE = ["#1e293b", "#667eea", "#28a745", "#dc3545", "#ffa500"]

# =========================================================
# AUTOMATED VISUALIZATIONS
# =========================================================
st.markdown('<div class="section-header">📊 Automated Insights</div>', unsafe_allow_html=True)

chart_images = []

def safe_plot(fig):
    """Render and export chart safely."""
    st.plotly_chart(fig, config={'displayModeBar': False}, use_container_width=True)
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_chart:
            fig.write_image(tmp_chart.name, format="png", scale=2, width=800, height=400)
            tmp_path = tmp_chart.name
    except Exception as e:
        st.warning(f"⚠️ Could not export chart image: {e}")
    
    return tmp_path

# --- Insights by Group ---
if saved_group == "Demographic Analysis":
    
    # Gender distribution
    if "Sex" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Gender Distribution</div>', unsafe_allow_html=True)
        
        fig_gender = px.pie(
            df, 
            names="Sex", 
            hole=0.4, 
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_gender.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=20),
            height=350,
            font=dict(family="Arial, sans-serif", size=12)
        )
        chart_images.append(safe_plot(fig_gender))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Disability
    if "Disability" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Disability Status Breakdown</div>', unsafe_allow_html=True)
        
        dis_data = df["Disability"].value_counts().reset_index()
        dis_data.columns = ["Disability", "Count"]
        
        fig_dis = px.bar(
            dis_data, 
            x="Disability", 
            y="Count", 
            color="Disability",
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_dis.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=40),
            height=350,
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f5')
        )
        chart_images.append(safe_plot(fig_dis))
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Age distribution
    if "Age" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Age Distribution</div>', unsafe_allow_html=True)
        
        fig_age = px.histogram(
            df, 
            x="Age", 
            nbins=10,
            color_discrete_sequence=[COLOR_PALETTE[0]]
        )
        fig_age.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=40),
            height=350,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f5')
        )
        chart_images.append(safe_plot(fig_age))
        st.markdown('</div>', unsafe_allow_html=True)

elif saved_group == "Geographic & Institutional Insights":
    
    if "State" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Candidates by State</div>', unsafe_allow_html=True)
        
        state_data = df["State"].value_counts().reset_index()
        state_data.columns = ["State", "Count"]
        
        fig_state = px.bar(
            state_data, 
            x="State", 
            y="Count", 
            color="State",
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_state.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=40),
            height=400,
            showlegend=False,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f5')
        )
        chart_images.append(safe_plot(fig_state))
        st.markdown('</div>', unsafe_allow_html=True)
    
    if "Centre" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Top 10 Exam Centers by Candidates</div>', unsafe_allow_html=True)
        
        center_data = df["Centre"].value_counts().reset_index().head(10)
        center_data.columns = ["Centre", "Count"]
        
        fig_center = px.bar(
            center_data, 
            x="Centre", 
            y="Count", 
            color="Centre",
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_center.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=80),
            height=400,
            showlegend=False,
            xaxis=dict(showgrid=False, tickangle=-45),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f5')
        )
        chart_images.append(safe_plot(fig_center))
        st.markdown('</div>', unsafe_allow_html=True)

elif saved_group == "Equity & Sponsorship":
    
    if "Sponsor" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Sponsorship Distribution</div>', unsafe_allow_html=True)
        
        fig_sponsor = px.pie(
            df, 
            names="Sponsor", 
            hole=0.4, 
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_sponsor.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=20),
            height=350
        )
        chart_images.append(safe_plot(fig_sponsor))
        st.markdown('</div>', unsafe_allow_html=True)
    
    if {"Sponsor", "Disability"}.issubset(df.columns):
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Disability vs Sponsorship</div>', unsafe_allow_html=True)
        
        sponsor_dis = df.groupby(["Sponsor", "Disability"]).size().reset_index(name="Count")
        fig_equity = px.bar(
            sponsor_dis, 
            x="Sponsor", 
            y="Count", 
            color="Disability",
            barmode="group", 
            color_discrete_sequence=COLOR_PALETTE
        )
        fig_equity.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=40),
            height=400,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f5')
        )
        chart_images.append(safe_plot(fig_equity))
        st.markdown('</div>', unsafe_allow_html=True)

elif saved_group == "Temporal & Progression Trends":
    
    if "ExamYear" in df.columns:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.markdown('<div class="chart-title">Candidate Trend Over Years</div>', unsafe_allow_html=True)
        
        trend = df["ExamYear"].value_counts().sort_index().reset_index()
        trend.columns = ["ExamYear", "Count"]
        
        fig_year = px.line(
            trend, 
            x="ExamYear", 
            y="Count", 
            markers=True,
            color_discrete_sequence=[COLOR_PALETTE[0]]
        )
        fig_year.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=20, b=40),
            height=350,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#f1f3f5')
        )
        chart_images.append(safe_plot(fig_year))
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PDF GENERATION SETUP
# =========================================================
summary_style = ParagraphStyle(
    name='SummaryStyle',
    fontName='Helvetica',
    fontSize=14,
    leading=16,
    alignment=0,
    spaceAfter=12
)

@st.cache_data(show_spinner=False)
def generate_pdf(dataframe, title, chart_paths, user_email):
    """Generate styled PDF with title, table, and charts."""
    styles = getSampleStyleSheet()
    report_title = Paragraph(f"<b>{title}</b>", styles["Title"])
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_on = Paragraph(f"Generated on: {date_str}", styles["Normal"])
    
    user_identifier = user_email.split("@")[0].replace(".", " ").title()
    user_identifier_display = Paragraph(
        f"<para align='center'><font size=20><b>Name: </b></font><font size=26><b>{user_identifier}</b></font></para>",
        styles["Normal"]
    )

    data = [dataframe.columns.tolist()] + dataframe.values.tolist()
    table = Table(data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 14)
    ]))

    def footer(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.drawString(40, 20, "© Copyright 2025 Edustat. - All rights reserved")
        canvas_obj.drawRightString(800, 20, f"email: {user_email}")
        canvas_obj.restoreState()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        doc = SimpleDocTemplate(tmpfile.name, pagesize=landscape(A4))
        elements = [
            report_title,
            Spacer(1, 18),
            generated_on,
            Spacer(1, 18),
            user_identifier_display,
            Spacer(1, 24),
            Paragraph("<b>Report Summary</b>", styles["Heading2"]),
            Spacer(1, 6),
            Paragraph(summary_text, summary_style),
            Spacer(1, 12),
            Paragraph("<b>Filtered Data Summary</b>", styles["Heading2"]),
            Spacer(1, 6),
            table,
        ]

        # Add charts
        for path in chart_paths:
            if path:
                elements.append(PageBreak())
                elements.append(Paragraph("<b>Chart Visualization</b>", styles["Heading2"]))
                elements.append(Spacer(1, 12))
                elements.append(Image(path, width=700, height=400))
        
        doc.build(elements, onFirstPage=footer, onLaterPages=footer)
        return tmpfile.name

# =========================================================
# DOWNLOAD SECTION
# =========================================================
st.markdown('<div class="section-header">📥 Download Options</div>', unsafe_allow_html=True)

col_down1, col_down2 = st.columns(2, gap="large")

# Get user info
user_identifier = st.session_state.get("user_email", "user").split("@")[0]
user_email = st.session_state.get("user_email", "no-email")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# CSV Download
with col_down1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">📊 CSV Export</div>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6c757d; margin-bottom: 1rem;">Download the raw data for external analysis</p>', unsafe_allow_html=True)
    
    csv_data = df.to_csv(index=False).encode("utf-8")
    csv_filename = f"{user_identifier}_{saved_group.replace(' ', '_')}.csv"
    
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name=csv_filename,
        mime="text/csv",
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# PDF Download
with col_down2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="chart-title">📄 PDF Report</div>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6c757d; margin-bottom: 1rem;">Download a comprehensive PDF with all visualizations</p>', unsafe_allow_html=True)
    
    if chart_images:
        valid_charts = [img for img in chart_images if img is not None]
        
        if valid_charts:
            try:
                pdf_path = generate_pdf(
                    summary_df, 
                    f"{saved_group} Summary Report", 
                    valid_charts, 
                    user_email
                )
                
                with open(pdf_path, "rb") as pdf_file:
                    pdf_bytes = BytesIO(pdf_file.read())
                    pdf_bytes.seek(0)
                    
                    # Apply watermark
                    pdf = add_watermark(
                        input_pdf_stream=pdf_bytes, 
                        watermark_image_path="altered_edustat.jpg"
                    )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf,
                    file_name=f"{saved_group.replace(' ', '_')}_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            except Exception as e:
                st.error(f"⚠️ Error generating PDF: {str(e)}")
        else:
            st.warning("⚠️ Charts could not be exported")
    else:
        st.info("ℹ️ Add charts to enable PDF export")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# BACK BUTTON
# =========================================================
st.markdown("---")
if st.button("← Back to Create Report"):
    st.switch_page("pages/create_report.py")
# 📄 VIEW REPORT 
import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from watermark import add_watermark
from io import BytesIO

# PAGE CONFIGURATION
st.set_page_config(page_title="View Report", layout="wide")
st.title("📄 View and Export Report")

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

st.success(f"✅ Showing results for: **{saved_group}**")
st.info(f"📊 **Total Records:** {len(df):,} | **Columns:** {', '.join(df.columns.tolist())}")

# =========================================================
# QUICK METRICS
# =========================================================
st.markdown("### 📌 Key Metrics")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Candidates", f"{len(df):,}")

with col2:
    if "Sex" in df.columns:
        female_count = df["Sex"].str.lower().eq("female").sum()
        female_pct = (female_count / len(df) * 100) if len(df) > 0 else 0
        st.metric("Female Candidates", f"{female_count:,} ({female_pct:.1f}%)")
    else:
        st.metric("Female Candidates", "N/A")

with col3:
    if "Disability" in df.columns:
        disability_count = df["Disability"].notna().sum()
        st.metric("With Disability Info", f"{disability_count:,}")
    else:
        st.metric("With Disability Info", "N/A")

# =========================================================
# GLOBAL COLOR PALETTE
# =========================================================
COLOR_PALETTE = ["#0078D7", "#FFA500", "#28A745", "#DC3545", "#6C757D"]

# =========================================================
# DATA PREVIEW & SUMMARY
# =========================================================
st.markdown("---")
st.subheader("📊 Data Summary")

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
        top_age = age_counts.index[0]
        top_age_count = age_counts.iloc[0]
        summary_items.append(("Most Common Age", f"{top_age} years ({top_age_count:,} candidates)"))

# Render summary
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

# Create summary DataFrame for PDF
summary_df = pd.DataFrame(summary_items, columns=["Metric", "Value"])

# =========================================================
# AUTO INSIGHTS SECTION
# =========================================================
st.markdown("---")
st.markdown("## 🧠 Automated Insights")

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
    st.info("📈 Analyzing **gender**, **age**, and **disability** demographics.")
    
    # Gender distribution
    if "Sex" in df.columns:
        fig_gender = px.pie(
            df, 
            names="Sex", 
            title="Gender Distribution",
            hole=0.3, 
            color_discrete_sequence=COLOR_PALETTE
        )
        chart_images.append(safe_plot(fig_gender))
        st.caption("Shows proportion of male vs. female candidates.")
    
    # Disability
    if "Disability" in df.columns:
        dis_data = df["Disability"].value_counts().reset_index()
        dis_data.columns = ["Disability", "Count"]
        
        fig_dis = px.bar(
            dis_data, 
            x="Disability", 
            y="Count", 
            color="Disability",
            color_discrete_sequence=COLOR_PALETTE,
            title="Disability Status Breakdown"
        )
        chart_images.append(safe_plot(fig_dis))
        st.caption("Highlights inclusion of candidates with disabilities.")
    
    # Age distribution
    if "Age" in df.columns:
        fig_age = px.histogram(
            df, 
            x="Age", 
            nbins=10, 
            title="Age Distribution",
            color_discrete_sequence=COLOR_PALETTE
        )
        chart_images.append(safe_plot(fig_age))
        st.caption("Displays candidate age spread for demographic insight.")

elif saved_group == "Geographic & Institutional Insights":
    st.info("🗺️ Exploring **regional participation** by state and exam center.")
    
    if "State" in df.columns:
        state_data = df["State"].value_counts().reset_index()
        state_data.columns = ["State", "Count"]
        
        fig_state = px.bar(
            state_data, 
            x="State", 
            y="Count", 
            color="State",
            color_discrete_sequence=COLOR_PALETTE,
            title="Candidates by State"
        )
        chart_images.append(safe_plot(fig_state))
        st.caption("Shows which states have the highest candidate participation.")
    
    if "Centre" in df.columns:
        center_data = df["Centre"].value_counts().reset_index().head(10)
        center_data.columns = ["Centre", "Count"]
        
        fig_center = px.bar(
            center_data, 
            x="Centre", 
            y="Count", 
            color="Centre",
            color_discrete_sequence=COLOR_PALETTE,
            title="Top 10 Exam Centers by Candidates"
        )
        chart_images.append(safe_plot(fig_center))
        st.caption("Highlights centers with highest participation.")

elif saved_group == "Equity & Sponsorship":
    st.info("💼 Evaluating **sponsorship** and **equity** participation.")
    
    if "Sponsor" in df.columns:
        fig_sponsor = px.pie(
            df, 
            names="Sponsor", 
            title="Sponsorship Distribution",
            hole=0.4, 
            color_discrete_sequence=COLOR_PALETTE
        )
        chart_images.append(safe_plot(fig_sponsor))
        st.caption("Compares sponsored vs. self-sponsored candidates.")
    
    if {"Sponsor", "Disability"}.issubset(df.columns):
        sponsor_dis = df.groupby(["Sponsor", "Disability"]).size().reset_index(name="Count")
        fig_equity = px.bar(
            sponsor_dis, 
            x="Sponsor", 
            y="Count", 
            color="Disability",
            barmode="group", 
            color_discrete_sequence=COLOR_PALETTE,
            title="Disability vs Sponsorship"
        )
        chart_images.append(safe_plot(fig_equity))
        st.caption("Shows representation of persons with disabilities among sponsored candidates.")

elif saved_group == "Temporal & Progression Trends":
    st.info("📅 Tracking **yearly performance** and **progression trends**.")
    
    if "ExamYear" in df.columns:
        trend = df["ExamYear"].value_counts().sort_index().reset_index()
        trend.columns = ["ExamYear", "Count"]
        
        fig_year = px.line(
            trend, 
            x="ExamYear", 
            y="Count", 
            markers=True,
            title="Candidate Trend Over Years",
            color_discrete_sequence=COLOR_PALETTE
        )
        chart_images.append(safe_plot(fig_year))
        st.caption("Shows yearly participation trends.")

else:
    st.info("ℹ️ No predefined insights available for this report group.")

# =========================================================
# RAW DATA TABLE
# =========================================================
st.markdown("---")
st.subheader("📋 Raw Data Preview")
st.dataframe(df.head(50), use_container_width=True)
st.caption(f"Showing first 50 of {len(df):,} records")

# =========================================================
# MANUAL VISUALIZATION SECTION
# =========================================================
st.markdown("---")
st.subheader("📈 Add Your Own Visuals")

if "visualizations" not in st.session_state:
    st.session_state.visualizations = []

with st.form("add_chart_form", clear_on_submit=True):
    chart_type = st.selectbox("Select Chart Type", ["Bar Chart", "Pie Chart", "Line Chart"])
    x_col = st.selectbox("X-axis Column", df.columns)
    y_col = st.selectbox("Y-axis Column (for aggregation)", df.columns)
    submitted = st.form_submit_button("➕ Add Visual")
    
    if submitted:
        st.session_state.visualizations.append({"type": chart_type, "x": x_col, "y": y_col})
        st.success(f"✅ Added {chart_type}: {x_col} vs {y_col}")
        st.rerun()

if st.session_state.visualizations:
    st.subheader("🖼️ Custom Visuals")
    
    for idx, chart in enumerate(st.session_state.visualizations):
        chart_type = chart["type"]
        x_col, y_col = chart["x"], chart["y"]
        st.markdown(f"### {idx + 1}. {chart_type} — {x_col} vs {y_col}")
        
        try:
            if chart_type == "Bar Chart":
                agg_data = df.groupby(x_col)[y_col].count().reset_index()
                agg_data.columns = [x_col, "Count"]
                fig = px.bar(
                    agg_data, 
                    x=x_col, 
                    y="Count", 
                    color=x_col,
                    title=f"{chart_type}: {x_col}",
                    color_discrete_sequence=COLOR_PALETTE
                )
            elif chart_type == "Pie Chart":
                agg_data = df.groupby(x_col)[y_col].count().reset_index()
                agg_data.columns = [x_col, "Count"]
                fig = px.pie(
                    agg_data, 
                    values="Count", 
                    names=x_col, 
                    hole=0.3,
                    title=f"{chart_type}: {x_col}",
                    color_discrete_sequence=COLOR_PALETTE
                )
            elif chart_type == "Line Chart":
                agg_data = df.groupby(x_col)[y_col].count().reset_index()
                agg_data.columns = [x_col, "Count"]
                fig = px.line(
                    agg_data, 
                    x=x_col, 
                    y="Count", 
                    markers=True,
                    title=f"{chart_type}: {x_col}",
                    color_discrete_sequence=COLOR_PALETTE
                )
            else:
                continue
            
            path = safe_plot(fig)
            if path:
                chart_images.append(path)
        
        except Exception as e:
            st.error(f"⚠️ Error rendering {chart_type}: {e}")
        
        if st.button(f"🗑️ Delete '{chart_type} ({x_col})'", key=f"del_{idx}"):
            st.session_state.visualizations.pop(idx)
            st.rerun()
    
    if st.button("🧹 Clear All Visuals"):
        st.session_state.visualizations = []
        st.rerun()
else:
    st.info("ℹ️ No custom visuals added yet. Use the form above to add one.")

# =========================================================
# PDF GENERATION & DOWNLOAD
# =========================================================
@st.cache_data(show_spinner=False)
def generate_pdf(dataframe, title, chart_paths):
    """Generate styled PDF with title, table, and charts."""
    styles = getSampleStyleSheet()
    report_title = Paragraph(f"<b>{title}</b>", styles["Title"])
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_on = Paragraph(f"Generated on: {date_str}", styles["Normal"])
    
    data = [dataframe.columns.tolist()] + dataframe.values.tolist()
    table = Table(data, colWidths=[200, 300])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 14)
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
        
        for path in chart_paths:
            if path:  # Only add if path exists
                elements.append(PageBreak())
                elements.append(Paragraph("<b>Chart Visualization</b>", styles["Heading2"]))
                elements.append(Spacer(1, 12))
                elements.append(Image(path, width=700, height=400))
        
        doc.build(elements)
        return tmpfile.name

# =========================================================
# PDF DOWNLOAD
# =========================================================
st.markdown("---")
st.subheader("📥 Download Report")

if chart_images:
    # Filter out None values from chart_images
    valid_chart_images = [img for img in chart_images if img is not None]
    
    if valid_chart_images:
        pdf_path = generate_pdf(summary_df, f"{saved_group} Summary Report", valid_chart_images)
        
        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = BytesIO(pdf_file.read())
            pdf_bytes.seek(0)
            
            # Apply watermark
            pdf = add_watermark(input_pdf_stream=pdf_bytes, watermark_image_path="altered_edustat.jpg")
        
        st.download_button(
            label="📄 Download Report as PDF",
            data=pdf,
            file_name=f"{saved_group.replace(' ', '_')}_report.pdf",
            mime="application/pdf"
        )
        st.success("✅ Your report is ready to download with all visuals.")
    else:
        st.warning("⚠️ Charts could not be exported. Download CSV instead.")
else:
    st.warning("⚠️ Add or generate at least one chart to include visuals in your PDF report.")

# CSV Download (always available)
st.markdown("---")
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📊 Download Raw Data as CSV",
    data=csv,
    file_name=f"{saved_group.replace(' ', '_')}_data.csv",
    mime="text/csv"
)

# Back button
st.markdown("---")
if st.button("← Back to Create Report"):
    st.switch_page("pages/create_report.py")
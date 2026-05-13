# ==============================
# 📊 VIEW REPORT — EDUSTAT
# ==============================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image, PageBreak, HRFlowable,
)
from watermark import add_watermark

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & CSS
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="View Report — Edustat", layout="wide")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer    {visibility: hidden;}
    header    {visibility: hidden;}
    .report-section {
        background: white; border-radius: 14px; padding: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07); margin-bottom: 2.5rem;
        border-left: 6px solid #1e293b;
    }
    .report-section-header { font-size:1.4rem; font-weight:700; color:#1e293b; margin-bottom:0.3rem; }
    .report-meta { font-size:0.9rem; color:#6c757d; margin-bottom:1.2rem; }
    .narrative-box {
        background:#f8fafc; border-left:4px solid #667eea;
        padding:1rem 1.5rem; border-radius:8px;
        font-size:0.97rem; line-height:1.8; color:#374151; margin-bottom:1.5rem;
    }
    .stat-chip { display:inline-block; background:#1e293b; color:white;
                 padding:6px 14px; border-radius:20px;
                 font-size:0.82rem; font-weight:600; margin:4px 4px 4px 0; }
    .stat-chip.green  { background:#16a34a; }
    .stat-chip.red    { background:#dc2626; }
    .stat-chip.blue   { background:#2563eb; }
    .stat-chip.orange { background:#ea580c; }
    .kpi-row  { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:1.5rem; }
    .kpi-box  { background:#f1f5f9; border-radius:10px;
                padding:14px 20px; min-width:140px; text-align:center; }
    .kpi-box .val { font-size:1.6rem; font-weight:700; color:#1e293b; }
    .kpi-box .lbl { font-size:0.8rem; color:#6c757d; margin-top:2px; }
    .page-header   { font-size:2.2rem; font-weight:700; color:#1a1a1a; margin-bottom:0.4rem; }
    .page-subtitle { font-size:1rem; color:#6c757d; margin-bottom:2rem; }
    .info-banner {
        background:linear-gradient(135deg,#1e293b 0%,#334155 100%);
        color:white; padding:1.4rem 1.8rem; border-radius:12px; margin-bottom:2rem;
    }
    .info-banner h3 { margin:0 0 0.3rem 0; font-size:1.2rem; }
    .info-banner p  { margin:0; opacity:0.85; font-size:0.95rem; }
    .chart-wrap { background:#fafafa; border-radius:10px; padding:1rem; margin-top:1rem; }
    .download-section { background:white; border-radius:14px; padding:2rem;
                         box-shadow:0 2px 12px rgba(0,0,0,0.07); margin-top:2rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
COLOR_PALETTE = [
    "#1e293b","#667eea","#16a34a","#dc2626","#ea580c",
    "#7c3aed","#0891b2","#d97706","#be185d","#065f46",
]
PARQUET_GLOB = r"C:\Users\uludoh\Documents\DB-PARQUET\chunks_data\**\*.parquet"
_GLOB        = PARQUET_GLOB.replace("\\", "/")

# Grade classification constants
CREDIT_GRADES = ("A1","B2","B3","C4","C5","C6")
PASS_GRADES   = ("A1","B2","B3","C4","C5","C6","D7","E8")
FAIL_GRADES   = ("D7","E8","F9")

# Nigerian geopolitical zones
ZONES = {
    "North-Central": ["Benue","Kogi","Kwara","Nassarawa","Niger","Plateau","Abuja","FCT"],
    "North-East":    ["Adamawa","Bauchi","Borno","Gombe","Taraba","Yobe"],
    "North-West":    ["Jigawa","Kaduna","Kano","Katsina","Kebbi","Sokoto","Zamfara"],
    "South-East":    ["Abia","Anambra","Ebonyi","Enugu","Imo"],
    "South-South":   ["Akwa Ibom","Bayelsa","Cross River","Rivers","Edo","Delta"],
    "South-West":    ["Ekiti","Lagos","Ogun","Ondo","Osun","Oyo"],
}

def state_to_zone(state: str) -> str:
    for zone, states in ZONES.items():
        if state in states:
            return zone
    return "Other"

# ─────────────────────────────────────────────────────────────────────────────
# SESSION VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in", False):
    st.warning("⚠️ Please sign in to access this page.")
    st.stop()

if not st.session_state.get("payment_verified", False):
    st.warning("⚠️ You must complete payment to view this report.")
    if st.button("← Go Back to Invoice"):
        st.switch_page("pages/view_invoice.py")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# SAVED REPORT LOADER
# When coming from my_reports.py, selected_report_id is set in session_state.
# We load the report filters from the database and reconstruct report_cart.
# ─────────────────────────────────────────────────────────────────────────────
selected_report_id = st.session_state.get("selected_report_id")
if selected_report_id and not st.session_state.get("report_cart"):
    try:
        from db_queries import fetch_data
        import json
        row = fetch_data(
            f"SELECT * FROM user_reports WHERE report_id = {selected_report_id} LIMIT 1"
        )
        if not row.empty:
            r = row.iloc[0]
            raw_filters = r.get("filters", "{}")
            filters_loaded = json.loads(raw_filters) if isinstance(raw_filters, str) else (raw_filters or {})

            # Pull the metadata fields that were packed into the filters dict
            # by view_invoice.py at save time. These are prefixed with "__".
            subgroup     = filters_loaded.pop("__subgroup__",     r.get("subgroup",    ""))
            analysis     = filters_loaded.pop("__analysis__",     r.get("report_name", "").split(" — ")[-1]
                                              if " — " in str(r.get("report_name","")) else r.get("report_name",""))
            record_count = filters_loaded.pop("__record_count__", 0)

            st.session_state.report_cart = [{
                "id":           1,
                "report_group": r.get("report_group", ""),
                "subgroup":     subgroup,
                "analysis":     analysis,
                "filters":      filters_loaded,
                "record_count": record_count,
                "price":        0,
                "price_fmt":    "₦0",
                "description":  r.get("report_name", ""),
            }]
        else:
            st.error("❌ Report not found. It may have expired or been deleted.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Could not load saved report: {e}")
        st.stop()

report_cart = st.session_state.get("report_cart", [])
if not report_cart:
    st.error("❌ No reports found. Please create a report first.")
    if st.button("← Go Back to Create Report"):
        st.switch_page("pages/create_report.py")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# DUCKDB CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_conn():
    import duckdb
    conn = duckdb.connect()
    conn.execute("SET memory_limit='3GB';")
    conn.execute("SET threads=4;")
    return conn


@st.cache_data(show_spinner=False, ttl=1800)
def _run(sql: str) -> pd.DataFrame:
    """Run aggregation SQL, return small DataFrame. Cached 30 min."""
    try:
        return _get_conn().execute(sql).df()
    except Exception as e:
        st.error(f"❌ Query failed: {e}")
        return pd.DataFrame()


def _src() -> str:
    return f"read_parquet('{_GLOB}', hive_partitioning=true, union_by_name=true)"


def _where(filters: dict) -> str:
    """Convert filter dict → SQL WHERE string. [] = no clause = all values."""
    parts = []
    yrs = filters.get("ExamYear")
    if yrs:
        joined = ", ".join(str(int(y)) for y in yrs)
        parts.append(f"TRY_CAST(ExamYear AS INTEGER) IN ({joined})")

    def add(col, key):
        v = filters.get(key)
        if not v:
            return
        esc = ", ".join(f"'{str(x).replace(chr(39),chr(39)*2)}'" for x in v)
        parts.append(f"{col} IN ({esc})")

    add("State","State"); add("Sex","Sex"); add("Disability","Disability")
    add("Sponsor","Sponsor"); add("AgeGroup","AgeGroup"); add("centre","centre")
    add("ExamType","ExamType"); add("Subject","Subject")
    add("Grade","Grade"); add("Status","Status")
    return ("WHERE " + " AND ".join(parts)) if parts else ""


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADER — ONE AGGREGATED QUERY PER ANALYSIS TYPE
# For performance/academic reports: returns Grade + Count so rates
# can be computed in Python (credits/total, pass/total).
# ─────────────────────────────────────────────────────────────────────────────
def get_item_df(item: dict) -> pd.DataFrame:
    filters  = item.get("filters", {})
    analysis = item.get("analysis", "")
    w        = _where(filters)
    s        = _src()

    # ── ACADEMIC PERFORMANCE — ALL GRADE-BASED REPORTS ───────────────────────
    # Returns Grade per ExamYear/State/Sex/AgeGroup/Subject/ExamType so that
    # credit_rate and pass_rate can be computed in Python by classification.
    if any(k in analysis for k in [
        "Grade","Performance","Credit","Pass","Fail",
        "Subject Performance","Attainment","School vs Private",
        "Exam Type Pass","Exam Type Performance",
    ]):
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                State,
                Sex,
                AgeGroup,
                Disability,
                Subject,
                ExamType,
                Grade,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY ExamYear, State, Sex, AgeGroup,
                     Disability, Subject, ExamType, Grade
            ORDER BY ExamYear, Grade
        """)

    # ── EXAM TYPE VOLUME/GENDER ───────────────────────────────────────────────
    elif "Exam Type" in analysis or "ExamType" in analysis:
        return _run(f"""
            SELECT ExamType, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   Sex, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY ExamType, ExamYear, Sex
            ORDER BY ExamYear, ExamType
        """)

    # ── GENDER ───────────────────────────────────────────────────────────────
    elif "Gender" in analysis or "Male" in analysis or "Female" in analysis:
        return _run(f"""
            SELECT Sex, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   State, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY Sex, ExamYear, State
            ORDER BY ExamYear, Sex
        """)

    # ── AGE ───────────────────────────────────────────────────────────────────
    elif analysis in ("Age Range of Candidates", "Age Distribution by Exam Year",
                      "Generational Education Trends",
                      "Age-Appropriate Enrollment Assessment"):
        return _run(f"""
            SELECT AgeGroup, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY AgeGroup, ExamYear
            ORDER BY ExamYear, AgeGroup
        """)

    elif analysis == "Cohort Tracking Across Years":
        age_min = filters.get("_age_min", 12)
        age_max = filters.get("_age_max", 25)
        cf  = {k: v for k, v in filters.items() if not k.startswith("_") and k != "AgeGroup"}
        cw  = _where(cf)
        af  = (f" AND (TRY_CAST(ExamYear AS INTEGER)"
               f" - YEAR(TRY_CAST(DateOfBirth AS DATE)))"
               f" BETWEEN {age_min} AND {age_max}")
        return _run(f"""
            SELECT TRY_CAST(ExamYear AS INTEGER) AS ExamYear, Sex,
                   (TRY_CAST(ExamYear AS INTEGER)
                    - YEAR(TRY_CAST(DateOfBirth AS DATE))) AS computed_age,
                   COUNT(*) AS Count
            FROM {s} {cw if cw else "WHERE 1=1"} {af}
            GROUP BY ExamYear, Sex, computed_age
            ORDER BY ExamYear, computed_age
        """)

    # ── REGISTRATION / ENROLLMENT ─────────────────────────────────────────────
    elif "Registration" in analysis or "Enrollment" in analysis:
        return _run(f"""
            SELECT TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   Sex, Sponsor, ExamType, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY ExamYear, Sex, Sponsor, ExamType
            ORDER BY ExamYear
        """)

    # ── STATE ─────────────────────────────────────────────────────────────────
    elif "State" in analysis or "Regional" in analysis or "Geographic" in analysis:
        return _run(f"""
            SELECT State, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY State, ExamYear
            ORDER BY Count DESC
        """)

    # ── CENTRE ────────────────────────────────────────────────────────────────
    elif "Centre" in analysis or "Center" in analysis:
        return _run(f"""
            SELECT centre, State, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY centre, State
            ORDER BY Count DESC
            LIMIT 50
        """)

    # ── DISABILITY ────────────────────────────────────────────────────────────
    elif "Disability" in analysis:
        return _run(f"""
            SELECT Disability, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   Sex, AgeGroup, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY Disability, ExamYear, Sex, AgeGroup
            ORDER BY ExamYear
        """)

    # ── SUBJECT ENROLLMENT (non-performance) ─────────────────────────────────
    elif "Subject" in analysis:
        return _run(f"""
            SELECT Subject, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   Grade, Sex, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY Subject, ExamYear, Grade, Sex
            ORDER BY Subject, ExamYear
        """)

    # ── SPONSOR ───────────────────────────────────────────────────────────────
    elif "Sponsor" in analysis:
        return _run(f"""
            SELECT Sponsor, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   State, ExamType, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY Sponsor, ExamYear, State, ExamType
            ORDER BY ExamYear
        """)

    # ── ABSENTEEISM ───────────────────────────────────────────────────────────
    elif "Absenteeism" in analysis or "Attendance" in analysis or "Sat" in analysis:
        return _run(f"""
            SELECT Status, TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   State, Sex, ExamType, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY Status, ExamYear, State, Sex, ExamType
            ORDER BY ExamYear
        """)

    # ── GENERIC ───────────────────────────────────────────────────────────────
    else:
        return _run(f"""
            SELECT TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   State, Sex, AgeGroup, Disability, ExamType, Sponsor,
                   COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY ExamYear, State, Sex, AgeGroup, Disability, ExamType, Sponsor
            ORDER BY ExamYear
        """)


# ─────────────────────────────────────────────────────────────────────────────
# RATE HELPERS
# All academic performance reports use these instead of raw counts.
# ─────────────────────────────────────────────────────────────────────────────

def credit_rate(df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
    if df.empty: return df
    
    # Fill missing values to prevent 0.0% errors
    g = df.copy()
    g["IsCredit"] = g["Grade"].isin(CREDIT_GRADES)
    
    agg = g.groupby(group_cols).apply(
        lambda x: pd.Series({
            "Total": x["Count"].sum(),
            "Credits": x.loc[x["IsCredit"], "Count"].sum(),
        })
    ).reset_index()
    
    # Avoid division by zero
    agg["CreditRate"] = (agg["Credits"] / agg["Total"].replace(0, float("nan")) * 100).round(1)
    
    # Filter out rows with 0 total to avoid plotting empty bars
    return agg[agg["Total"] > 0]

# def credit_rate(df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
#     """
#     Given a df with [group_cols..., Grade, Count], compute:
#       CreditRate = sum(Count where Grade in CREDIT_GRADES) / sum(Count) * 100
#     Returns df with group_cols + [Total, Credits, CreditRate%].
#     """
#     if "Grade" not in df.columns or "Count" not in df.columns:
#         return pd.DataFrame()
#     g = df.copy()
#     g["IsCredit"] = g["Grade"].isin(CREDIT_GRADES)
#     agg = g.groupby(group_cols).apply(
#         lambda x: pd.Series({
#             "Total":       x["Count"].sum(),
#             "Credits":     x.loc[x["IsCredit"], "Count"].sum(),
#         })
#     ).reset_index()
#     agg["CreditRate"] = (agg["Credits"] / agg["Total"].replace(0, float("nan")) * 100).round(1)
#     return agg


def pass_fail_rate(df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
    """
    Compute pass rate (A1–E8) and fail rate (F9) per group.
    Returns group_cols + [Total, Pass, Fail, PassRate%, FailRate%].
    """
    if "Grade" not in df.columns or "Count" not in df.columns:
        return pd.DataFrame()
    g = df.copy()
    g["IsPass"] = g["Grade"].isin(PASS_GRADES)
    g["IsFail"] = g["Grade"] == "F9"
    agg = g.groupby(group_cols).apply(
        lambda x: pd.Series({
            "Total": x["Count"].sum(),
            "Pass":  x.loc[x["IsPass"], "Count"].sum(),
            "Fail":  x.loc[x["IsFail"], "Count"].sum(),
        })
    ).reset_index()
    agg["PassRate"] = (agg["Pass"] / agg["Total"].replace(0, float("nan")) * 100).round(1)
    agg["FailRate"] = (agg["Fail"] / agg["Total"].replace(0, float("nan")) * 100).round(1)
    return agg


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def fmt(n) -> str:
    try:    return f"{int(n):,}"
    except: return str(n)

def pct(part, whole) -> str:
    if whole == 0: return "0%"
    return f"{round(part / whole * 100, 1)}%"

def trend_dir(series: pd.Series) -> str:
    if len(series) < 2: return "stable"
    diffs = [series.iloc[i+1] - series.iloc[i] for i in range(len(series)-1)]
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    if pos > neg: return "an upward"
    if neg > pos: return "a downward"
    return "a mixed"

def filter_label(filters: dict) -> str:
    parts = []
    for k, v in filters.items():
        if k.startswith("_"): continue
        display = "All" if v == [] or v is None else (
            ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
        )
        parts.append(f"**{k}**: {display}")
    return ", ".join(parts) if parts else "all data"


# ─────────────────────────────────────────────────────────────────────────────
# CHART IMAGE SAVER — REQUIRED FOR PDF
#
# THE PROBLEM WITH TEMP FILES:
# When the user clicks "Generate PDF", Streamlit reruns the entire script.
# Any dict or variable set earlier (like chart_images_by_report) is rebuilt
# empty on every rerun. Temp files written in one rerun may also be cleaned
# up before the PDF rerun happens.
#
# THE FIX:
# Save chart PNG bytes directly into st.session_state, keyed by a stable
# string. Session state persists across reruns within the same browser session.
# The PDF builder reads from session_state instead of a local dict.
#
# Requires: pip install kaleido
# ─────────────────────────────────────────────────────────────────────────────
def save_chart_to_session(fig, key: str) -> bool:
    """
    Renders a Plotly figure to PNG bytes and stores them in session_state[key].
    Returns True if successful, False otherwise.

    Using bytes (not file paths) means the data survives Streamlit reruns —
    temp files can be deleted between reruns but session_state persists.
    """
    if fig is None:
        return False
    try:
        # to_image() returns PNG as bytes — no file system needed
        img_bytes = fig.to_image(format="png", scale=2, width=900, height=420)
        if img_bytes:
            st.session_state[key] = img_bytes
            return True
        return False
    except Exception as e:
        st.warning(
            f"⚠️ Chart export failed: {e}. "
            "Run: pip install kaleido"
        )
        return False


def get_chart_bytes_for_pdf(key: str):
    """Retrieve chart PNG bytes from session_state for PDF embedding."""
    return st.session_state.get(key)


# Legacy wrapper kept for any remaining direct calls
def save_chart_image(fig) -> str | None:
    """
    Saves a Plotly figure to a temp PNG file. Returns path or None.
    NOTE: Prefer save_chart_to_session() for PDF use — temp files
    are deleted between Streamlit reruns.
    """
    if fig is None:
        return None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".png", dir=tempfile.gettempdir()
        ) as tmp:
            path = tmp.name
        fig.write_image(path, format="png", scale=2, width=900, height=420)
        return path if os.path.exists(path) and os.path.getsize(path) > 0 else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# STANDARD CHART LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

def _layout(**extra):
    return dict(
        plot_bgcolor="white",    # Background of the chart area
        paper_bgcolor="white",   # Background of the entire widget
        font=dict(
            family="Arial, sans-serif", 
            size=12, 
            color="#1e293b"      # Force text to be Navy (Dark)
        ),
        margin=dict(l=50, r=50, t=80, b=100),
        height=500,
        xaxis=dict(
            showline=True, 
            linecolor="#e2e8f0", 
            tickangle=-30,
            tickfont=dict(color="#1e293b") # Ensure state names are visible
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor="#f1f5f9", # Light gray grid lines
            tickfont=dict(color="#1e293b")
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=-0.3, 
            xanchor="center", 
            x=0.5
        )
    )

# def _layout(**extra):
#     base = dict(
#         plot_bgcolor="white", paper_bgcolor="white",
#         font=dict(family="Arial, sans-serif", size=12),
#         margin=dict(l=40, r=40, t=60, b=100),
#         height=440,
#         colorway=COLOR_PALETTE,
#         legend=dict(orientation="h", yanchor="bottom", y=-0.35,
#                     xanchor="center", x=0.5),
#     )
#     base.update(extra)
#     return base


# ─────────────────────────────────────────────────────────────────────────────
# NARRATIVE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_narrative(analysis: str, df: pd.DataFrame, filters: dict) -> str:
    if df is None or df.empty: return "No data found."
    
    # 1. Extract context variables
    total = int(df["Count"].sum())
    top_year = df.groupby("ExamYear")["Count"].sum().idxmax() if "ExamYear" in df.columns else "N/A"
    
    # 2. Logic for Performance Reports
    if "Grade" in df.columns:
        # Calculate Credit Rate (A1-C6)
        credits = int(df[df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
        rate = (credits / total * 100) if total > 0 else 0
        
        if "Subject" in analysis:
            top_subj = df.groupby("Subject")["Count"].sum().idxmax()
            return f"The **{analysis}** reveals that out of {total:,} results, **{top_subj}** recorded the highest volume. The overall credit attainment rate (A1-C6) stands at **{rate:.1f}%**. Year-on-year data suggests performance peaked in **{top_year}**."
            
        if "State" in analysis:
            top_state = df.groupby("State")["Count"].sum().idxmax()
            return f"Geographic analysis for **{analysis}** identifies **{top_state}** as the leading territory by volume. System-wide credit success is **{rate:.1f}%**. This suggests a localized concentration of academic excellence."

    # 3. Logic for Demographic Reports
    if "Sex" in df.columns:
        male_pct = (df[df["Sex"] == "Male"]["Count"].sum() / total * 100)
        female_pct = 100 - male_pct
        bias = "Male" if male_pct > 55 else "Female" if female_pct > 55 else "Balanced"
        return f"The demographic profile for this report is **{bias}**. Female participation stands at **{female_pct:.1f}%** compared to Male at **{male_pct:.1f}%**. The highest enrollment was recorded in **{top_year}**."

    return f"This {analysis} report summarizes {total:,} records. Key participation was highest in {top_year}."

def generate_narrative(analysis: str, df: pd.DataFrame, filters: dict) -> str:
    if df is None or df.empty:
        return "No data available for the selected filters."

    total       = int(df["Count"].sum()) if "Count" in df.columns else 0
    filter_desc = filter_label(filters)

    # ── FULL GRADE BREAKDOWN ──────────────────────────────────────────────────
    if analysis == "Full Grade Breakdown":
        if "Grade" not in df.columns:
            return f"Total results: {fmt(total)}. Grade data unavailable."
        gd = df.groupby("Grade")["Count"].sum().sort_values(ascending=False)
        top_g  = gd.index[0]
        top_ct = int(gd.iloc[0])
        cr_total = int(df[df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
        return (
            f"Full grade breakdown. Filters: {filter_desc}. "
            f"Total results: **{fmt(total)}**. "
            f"Most common grade: **{top_g}** — {fmt(top_g)} ({pct(top_ct, total)}). "
            f"Credit grades (A1–C6): **{fmt(cr_total)}** ({pct(cr_total, total)} of all results). "
            f"Fail (F9): **{fmt(int(df[df['Grade']=='F9']['Count'].sum()))}** "
            f"({pct(int(df[df['Grade']=='F9']['Count'].sum()), total)})."
        )

    # ── PASS VS FAIL RATE ─────────────────────────────────────────────────────
    elif analysis == "Pass vs Fail Rate":
        if "Grade" not in df.columns:
            return f"Total results: {fmt(total)}. Grade data unavailable."

        # Use custom pass/fail buckets if user defined them in configure_filters
        # otherwise fall back to standard WAEC classification
        pass_grades = filters.get("_pass_grades") or list(PASS_GRADES)
        fail_grades = filters.get("_fail_grades") or ["F9"]

        # Per-grade percentage breakdown
        grade_counts = df.groupby("Grade")["Count"].sum().sort_index()
        grade_pcts   = (grade_counts / total * 100).round(1)

        pass_ct = int(df[df["Grade"].isin(pass_grades)]["Count"].sum())
        fail_ct = int(df[df["Grade"].isin(fail_grades)]["Count"].sum())

        # Build per-grade detail string
        grade_detail = " ".join(
            f"**{g}**: {grade_pcts.get(g, 0)}%"
            for g in ["A1","B2","B3","C4","C5","C6","D7","E8","F9"]
            if g in grade_counts.index
        )

        return (
            f"Pass vs Fail analysis. Filters: {filter_desc}. "
            f"Total results: **{fmt(total)}**. "
            f"**Overall pass rate** ({', '.join(pass_grades)}): "
            f"**{pct(pass_ct, total)}** ({fmt(pass_ct)} results). "
            f"**Overall fail rate** ({', '.join(fail_grades)}): "
            f"**{pct(fail_ct, total)}** ({fmt(fail_ct)} results). "
            f"Per-grade breakdown — {grade_detail}. "
            + (
                "✅ The majority of candidates passed."
                if pass_ct > fail_ct else
                "⚠️ More candidates failed than passed — intervention may be needed."
            )
        )

    # ── GRADE DISTRIBUTION BY EXAM YEAR ──────────────────────────────────────
    elif analysis == "Grade Distribution by Exam Year":
        if "ExamYear" not in df.columns:
            return f"Total: {fmt(total)}. ExamYear unavailable."
        agg = credit_rate(df, ["ExamYear"])
        if agg.empty:
            return f"Total: {fmt(total)} results across selected years. Filters: {filter_desc}."
        agg = agg.sort_values("ExamYear")
        best  = agg.loc[agg["CreditRate"].idxmax()]
        worst = agg.loc[agg["CreditRate"].idxmin()]
        return (
            f"Grade distribution by exam year. Filters: {filter_desc}. "
            f"Total results: **{fmt(total)}**. "
            f"Best year: **{int(best['ExamYear'])}** — credit rate {best['CreditRate']}%. "
            f"Worst year: **{int(worst['ExamYear'])}** — credit rate {worst['CreditRate']}%. "
            f"Trend: {trend_dir(agg.set_index('ExamYear')['CreditRate'])}."
        )

    # ── GRADE DISTRIBUTION BY STATE ───────────────────────────────────────────
    elif analysis == "Grade Distribution by State":
        if "State" not in df.columns:
            return f"Total: {fmt(total)}. State data unavailable."
        agg = credit_rate(df, ["State"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)} results. Filters: {filter_desc}."
        return (
            f"Grade distribution by state. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results across **{agg['State'].nunique()}** states. "
            f"Top state: **{agg.iloc[0]['State']}** — {agg.iloc[0]['CreditRate']}% credit rate. "
            f"Bottom state: **{agg.iloc[-1]['State']}** — {agg.iloc[-1]['CreditRate']}% credit rate."
        )

    # ── 5-CREDIT ATTAINMENT RATE ──────────────────────────────────────────────
    elif analysis == "5-Credit Attainment Rate":
        cr_total = int(df[df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
        return (
            f"5-Credit attainment analysis. Filters: {filter_desc}. "
            f"Total results: **{fmt(total)}**. "
            f"Results achieving credit grade (A1–C6): **{fmt(cr_total)}** "
            f"({pct(cr_total, total)} of total). "
            "Note: To compute candidates with 5 or more credits requires "
            "grouping by candidate ID across subjects — this shows the "
            "proportion of individual subject results at credit level."
        )

    # ── ENGLISH & MATHS CREDIT RATE ───────────────────────────────────────────
    elif analysis == "English & Maths Credit Rate":
        lines = [
            f"English Language and Mathematics credit rate analysis. "
            f"Filters: {filter_desc}. Total results: **{fmt(total)}**."
        ]
        for subj in ["English Language", "Mathematics"]:
            sub_df = df[df["Subject"] == subj] if "Subject" in df.columns else pd.DataFrame()
            if not sub_df.empty:
                sub_total = int(sub_df["Count"].sum())
                sub_cr    = int(sub_df[sub_df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
                lines.append(
                    f"**{subj}**: {fmt(sub_total)} results, "
                    f"credit rate **{pct(sub_cr, sub_total)}** ({fmt(sub_cr)} credits)."
                )
        return " ".join(lines)

    # ── CREDIT ATTAINMENT TREND ────────────────────────────────────────────────
    elif analysis == "Credit Attainment Trend":
        agg = credit_rate(df, ["ExamYear"]).sort_values("ExamYear")
        if agg.empty:
            return f"Total: {fmt(total)} results. Filters: {filter_desc}."
        trend = trend_dir(agg.set_index("ExamYear")["CreditRate"])
        best  = agg.loc[agg["CreditRate"].idxmax()]
        worst = agg.loc[agg["CreditRate"].idxmin()]
        return (
            f"Credit attainment trend. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results. "
            f"Overall trend: **{trend}**. "
            f"Peak: **{int(best['ExamYear'])}** at {best['CreditRate']}% credit rate. "
            f"Lowest: **{int(worst['ExamYear'])}** at {worst['CreditRate']}% credit rate."
        )

    # ── CREDIT ATTAINMENT BY STATE & GENDER ───────────────────────────────────
    elif analysis == "Credit Attainment by State & Gender":
        lines = [
            f"Credit attainment by state and gender. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results."
        ]
        if "Sex" in df.columns and "State" in df.columns:
            agg = credit_rate(df, ["State", "Sex"]).sort_values("CreditRate", ascending=False)
            if not agg.empty:
                top = agg.iloc[0]
                bot = agg.iloc[-1]
                lines.append(
                    f"Highest: **{top['State']}** ({top['Sex']}) — "
                    f"{top['CreditRate']}% credit rate."
                )
                lines.append(
                    f"Lowest: **{bot['State']}** ({bot['Sex']}) — "
                    f"{bot['CreditRate']}% credit rate."
                )
        return " ".join(lines)

    # ── BEST & WORST PERFORMING SUBJECTS ──────────────────────────────────────
    elif analysis == "Best & Worst Performing Subjects":
        agg = credit_rate(df, ["Subject"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        n   = filters.get("_top_n", 5)
        top = agg.head(n)
        bot = agg.tail(n)
        top_list = ", ".join(f"**{r['Subject']}** ({r['CreditRate']}%)" for _, r in top.iterrows())
        bot_list = ", ".join(f"**{r['Subject']}** ({r['CreditRate']}%)" for _, r in bot.iterrows())
        return (
            f"Subject performance ranking. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results. "
            f"Top {n} by credit rate: {top_list}. "
            f"Bottom {n}: {bot_list}."
        )

    # ── SUBJECT PASS RATE COMPARISON ──────────────────────────────────────────
    elif analysis == "Subject Pass Rate Comparison":
        agg = pass_fail_rate(df, ["Subject"]).sort_values("PassRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        top = agg.iloc[0]
        bot = agg.iloc[-1]
        return (
            f"Subject pass rate comparison. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results across **{agg['Subject'].nunique()}** subjects. "
            f"Highest pass rate: **{top['Subject']}** — {top['PassRate']}%. "
            f"Lowest: **{bot['Subject']}** — {bot['PassRate']}%."
        )

    # ── SUBJECT PERFORMANCE BY STATE ──────────────────────────────────────────
    elif analysis == "Subject Performance by State":
        agg = credit_rate(df, ["Subject","State"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        top = agg.iloc[0]
        bot = agg.iloc[-1]
        return (
            f"Subject credit rate by state. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results. "
            f"Highest: **{top['Subject']}** in **{top['State']}** — {top['CreditRate']}% credit rate. "
            f"Lowest: **{bot['Subject']}** in **{bot['State']}** — {bot['CreditRate']}%."
        )

    # ── SUBJECT PERFORMANCE TRENDS ────────────────────────────────────────────
    elif analysis == "Subject Performance Trends":
        agg = credit_rate(df, ["Subject","ExamYear"]).sort_values(["Subject","ExamYear"])
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        lines = [
            f"Subject credit rate trends. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results."
        ]
        for subj, grp in agg.groupby("Subject"):
            trend = trend_dir(grp.set_index("ExamYear")["CreditRate"])
            lines.append(f"**{subj}**: {trend} trend in credit rate.")
        return " ".join(lines)

    # ── GENDER PERFORMANCE GAP ────────────────────────────────────────────────
    elif analysis == "Gender Performance Gap":
        agg = credit_rate(df, ["Sex","ExamYear"]).sort_values("ExamYear")
        if "Sex" not in df.columns:
            return f"Total: {fmt(total)}. Sex data unavailable."
        sex_agg = credit_rate(df, ["Sex"])
        male_r   = float(sex_agg.loc[sex_agg["Sex"]=="Male",   "CreditRate"].values[0]) if "Male"   in sex_agg["Sex"].values else 0
        female_r = float(sex_agg.loc[sex_agg["Sex"]=="Female", "CreditRate"].values[0]) if "Female" in sex_agg["Sex"].values else 0
        gap      = round(abs(male_r - female_r), 1)
        better   = "females" if female_r > male_r else "males"
        return (
            f"Gender performance gap. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results. "
            f"Male credit rate: **{male_r}%**. Female credit rate: **{female_r}%**. "
            f"**{better.title()}** outperform by **{gap}** percentage points. "
            + (f"The gap is significant and warrants attention." if gap > 5 else
               f"The gap is relatively small.")
        )

    # ── AGE GROUP PERFORMANCE ─────────────────────────────────────────────────
    elif analysis == "Age Group Performance Comparison":
        agg = credit_rate(df, ["AgeGroup"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        top = agg.iloc[0]
        bot = agg.iloc[-1]
        return (
            f"Age group credit rate comparison. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results. "
            f"Best performing age group: **{top['AgeGroup']}** — {top['CreditRate']}% credit rate. "
            f"Lowest: **{bot['AgeGroup']}** — {bot['CreditRate']}%. "
            + (
                "Younger candidates tend to outperform older ones."
                if top["AgeGroup"] < bot["AgeGroup"] else
                "Older candidates show stronger performance."
            )
        )

    # ── DISABILITY ACHIEVEMENT GAP ────────────────────────────────────────────
    elif analysis == "Disability Achievement Gap":
        agg = credit_rate(df, ["Disability"])
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        lines = [
            f"Disability achievement gap. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results."
        ]
        for _, row in agg.iterrows():
            lines.append(f"**{row['Disability']}**: {row['CreditRate']}% credit rate.")
        return " ".join(lines)

    # ── COMBINED DEMOGRAPHIC PERFORMANCE ──────────────────────────────────────
    elif analysis == "Combined Demographic Performance":
        agg = credit_rate(df, ["Sex","AgeGroup","Disability"]).sort_values(
            "CreditRate", ascending=False
        )
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        top = agg.iloc[0]
        return (
            f"Combined demographic performance. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results. "
            f"Highest-performing group: **{top.get('Sex','?')}**, "
            f"age **{top.get('AgeGroup','?')}**, "
            f"disability **{top.get('Disability','?')}** — "
            f"{top['CreditRate']}% credit rate."
        )

    # ── STATE PERFORMANCE RANKINGS ────────────────────────────────────────────
    elif analysis == "State Performance Rankings":
        agg = credit_rate(df, ["State"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        top5 = ", ".join(f"**{r['State']}** ({r['CreditRate']}%)"
                         for _, r in agg.head(5).iterrows())
        bot5 = ", ".join(f"**{r['State']}** ({r['CreditRate']}%)"
                         for _, r in agg.tail(5).iterrows())
        return (
            f"State credit rate rankings. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results across **{agg['State'].nunique()}** states. "
            f"Top 5: {top5}. Bottom 5: {bot5}."
        )

    # ── REGIONAL PERFORMANCE GAPS ─────────────────────────────────────────────
    elif analysis == "Regional Performance Gaps":
        if "State" not in df.columns:
            return f"Total: {fmt(total)}. State data unavailable."
        df2 = df.copy()
        df2["Zone"] = df2["State"].apply(state_to_zone)
        agg = credit_rate(df2, ["Zone"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        top = agg.iloc[0]
        bot = agg.iloc[-1]
        gap = round(float(top["CreditRate"]) - float(bot["CreditRate"]), 1)
        return (
            f"Regional credit rate analysis by geopolitical zone. "
            f"Filters: {filter_desc}. Total: **{fmt(total)}** results. "
            f"**{top['Zone']}** leads with {top['CreditRate']}% credit rate. "
            f"**{bot['Zone']}** has the lowest at {bot['CreditRate']}%. "
            f"Regional gap: **{gap} percentage points**."
        )

    # ── STATE PERFORMANCE TRENDS ──────────────────────────────────────────────
    elif analysis == "State Performance Trends":
        agg = credit_rate(df, ["State","ExamYear"]).sort_values(["State","ExamYear"])
        lines = [
            f"State credit rate trends. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results."
        ]
        if not agg.empty:
            for state, grp in agg.groupby("State"):
                trend = trend_dir(grp.set_index("ExamYear")["CreditRate"])
                lines.append(f"**{state}**: {trend} trend.")
        return " ".join(lines)

    # ── SCHOOL VS PRIVATE ─────────────────────────────────────────────────────
    elif analysis == "School vs Private Candidate Performance":
        agg = credit_rate(df, ["ExamType","ExamYear"]).sort_values("ExamYear")
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        et_agg = credit_rate(df, ["ExamType"])
        lines  = [
            f"School vs Private candidate credit rate. "
            f"Filters: {filter_desc}. Total: **{fmt(total)}** results."
        ]
        for _, row in et_agg.sort_values("CreditRate", ascending=False).iterrows():
            lines.append(f"**{row['ExamType']}**: {row['CreditRate']}% credit rate.")
        return " ".join(lines)

    # ── EXAM TYPE PASS RATE COMPARISON ────────────────────────────────────────
    elif analysis == "Exam Type Pass Rate Comparison":
        agg = pass_fail_rate(df, ["ExamType"]).sort_values("PassRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        lines = [
            f"Exam type pass rate comparison. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** results."
        ]
        for _, row in agg.iterrows():
            lines.append(
                f"**{row['ExamType']}**: {row['PassRate']}% pass rate, "
                f"{row['FailRate']}% fail rate."
            )
        return " ".join(lines)

    # ── EXAM TYPE PERFORMANCE BY STATE ────────────────────────────────────────
    elif analysis == "Exam Type Performance by State":
        if "ExamType" not in df.columns or "State" not in df.columns:
            return None
        
    # 1. Ensure we compute the Credit Rate for BOTH State and ExamType
    agg = credit_rate(df, ["State", "ExamType"]).sort_values("State")
    
    # 2. Use 'color' to segment and 'barmode' to group
    fig = px.bar(
        agg, 
        x="State", 
        y="CreditRate", 
        color="ExamType",        # This creates the different colored bars
        barmode="group",         # This puts them side-by-side (School vs Private)
        title="Credit Rate by State and Exam Type",
        labels={"CreditRate": "Credit Rate (%)", "ExamType": "Exam Type"},
        color_discrete_map={     # Force distinct brand colors
            "School Exams": "#1e293b", 
            "Private Examination": "#2563eb"
        },
        text=agg["CreditRate"].astype(str) + "%", # Show % on top
    )
    
    fig.update_traces(textposition="outside")
    fig.update_layout(**L) # Use the updated L layout below for visual clarity
    fig.update_yaxes(range=[0, 110], ticksuffix="%")
    return fig

#     # ── EXAM TYPE PERFORMANCE TRENDS ──────────────────────────────────────────
#     elif analysis == "Exam Type Performance Trends":
#         agg = credit_rate(df, ["ExamType","ExamYear"]).sort_values(["ExamType","ExamYear"])
#         lines = [
#             f"Exam type credit rate trends. Filters: {filter_desc}. "
#             f"Total: **{fmt(total)}** results."
#         ]
#         for et, grp in agg.groupby("ExamType"):
#             trend = trend_dir(grp.set_index("ExamYear")["CreditRate"])
#             lines.append(f"**{et}**: {trend} trend.")
#         return " ".join(lines)

#     # ── GENERIC FALLBACK ──────────────────────────────────────────────────────
#     else:
#         total = int(df["Count"].sum()) if "Count" in df.columns else 0
#         lines = [f"**{analysis}**. Filters: {filter_desc}. Total: **{fmt(total)}**."]
#         for col in ["ExamYear","State","Sex","AgeGroup","Disability","ExamType","Sponsor"]:
#             if col in df.columns:
#                 top_val = df.groupby(col)["Count"].sum().idxmax()
#                 top_ct  = int(df.groupby(col)["Count"].sum().max())
#                 lines.append(f"Top **{col}**: {top_val} ({fmt(top_ct)}, {pct(top_ct, total)}).")
#         return " ".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_chart(analysis: str, df: pd.DataFrame, filters: dict):
    if df is None or df.empty:
        return None
    L = _layout()

    try:
        total = int(df["Count"].sum()) if "Count" in df.columns else 1

        # ── FULL GRADE BREAKDOWN — bar chart of grade counts ─────────────────
        if analysis == "Full Grade Breakdown":
            if "Grade" not in df.columns:
                return None
            g = df.groupby("Grade")["Count"].sum().reset_index()
            g["Pct"] = (g["Count"] / total * 100).round(1)
            g["Label"] = g["Grade"] + "<br>" + g["Pct"].astype(str) + "%"
            # Colour credits green, fails red, passes amber
            def grade_color(gr):
                if gr in CREDIT_GRADES: return "#16a34a"
                if gr == "F9":          return "#dc2626"
                return "#d97706"
            g["Color"] = g["Grade"].apply(grade_color)
            fig = px.bar(
                g, x="Grade", y="Count",
                title="Full Grade Distribution",
                color="Grade",
                color_discrete_map={r["Grade"]: grade_color(r["Grade"]) for _, r in g.iterrows()},
                text=g["Pct"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L, title_x=0)
            fig.update_xaxes(showgrid=False, categoryorder="array",
                             categoryarray=["A1","B2","B3","C4","C5","C6","D7","E8","F9"])
            fig.update_yaxes(gridcolor="#f1f3f5", title="Number of Results")
            return fig

        # ── PASS VS FAIL — donut chart ────────────────────────────────────────
        elif analysis == "Pass vs Fail Rate":
            if "Grade" not in df.columns:
                return None
            grade_totals = df.groupby("Grade")["Count"].sum().reset_index()
            grade_totals["Category"] = grade_totals["Grade"].apply(
                lambda g: ("Credit (A1–C6)" if g in CREDIT_GRADES
                           else ("Pass (D7–E8)" if g in ("D7","E8")
                                 else "Fail (F9)"))
            )
            cat_totals = grade_totals.groupby("Category")["Count"].sum().reset_index()
            fig = px.pie(
                cat_totals, names="Category", values="Count", hole=0.5,
                title="Pass vs Fail Rate",
                color="Category",
                color_discrete_map={
                    "Credit (A1–C6)": "#16a34a",
                    "Pass (D7–E8)":   "#d97706",
                    "Fail (F9)":      "#dc2626",
                },
            )
            fig.update_traces(textinfo="label+percent", textposition="outside")
            fig.update_layout(**L)
            return fig

        # ── GRADE DISTRIBUTION BY EXAM YEAR — line chart of credit rate ───────
        elif analysis == "Grade Distribution by Exam Year":
            if "Grade" not in df.columns or "ExamYear" not in df.columns:
                return None
            agg = credit_rate(df, ["ExamYear"]).sort_values("ExamYear")
            fig = px.line(
                agg, x="ExamYear", y="CreditRate",
                markers=True,
                title="Credit Rate (A1–C6) by Exam Year",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=[COLOR_PALETTE[2]],
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0, 100], ticksuffix="%")
            return fig

        # ── GRADE DISTRIBUTION BY STATE — horizontal bar ──────────────────────
        elif analysis == "Grade Distribution by State":
            if "State" not in df.columns:
                return None
            agg = credit_rate(df, ["State"]).sort_values("CreditRate", ascending=True)
            fig = px.bar(
                agg, x="CreditRate", y="State", orientation="h",
                title="Credit Rate by State",
                color="CreditRate",
                color_continuous_scale=["#dc2626","#d97706","#16a34a"],
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(range=[0,100], ticksuffix="%", title="Credit Rate (%)")
            fig.update_yaxes(showgrid=False)
            return fig

        # ── 5-CREDIT ATTAINMENT — stacked bar of grade categories per year ────
        elif analysis == "5-Credit Attainment Rate":
            if "Grade" not in df.columns or "ExamYear" not in df.columns:
                return None
            df2 = df.copy()
            df2["Category"] = df2["Grade"].apply(
                lambda g: "Credit" if g in CREDIT_GRADES else ("Pass" if g in ("D7","E8") else "Fail")
            )
            agg = df2.groupby(["ExamYear","Category"])["Count"].sum().reset_index()
            # Compute credit rate per year
            cr  = credit_rate(df, ["ExamYear"]).sort_values("ExamYear")
            fig = px.line(
                cr, x="ExamYear", y="CreditRate",
                markers=True,
                title="Credit Grade Rate (A1–C6) per Exam Year",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=[COLOR_PALETTE[2]],
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── ENGLISH & MATHS CREDIT RATE — grouped bar per year ────────────────
        elif analysis == "English & Maths Credit Rate":
            if "Subject" not in df.columns or "ExamYear" not in df.columns:
                return None
            df2  = df[df["Subject"].isin(["English Language","Mathematics"])].copy()
            agg  = credit_rate(df2, ["ExamYear","Subject"]).sort_values("ExamYear")
            fig  = px.bar(
                agg, x="ExamYear", y="CreditRate", color="Subject",
                barmode="group",
                title="English Language vs Mathematics — Credit Rate by Year",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=["#1e293b","#667eea"],
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── CREDIT ATTAINMENT TREND — line chart ──────────────────────────────
        elif analysis == "Credit Attainment Trend":
            agg = credit_rate(df, ["ExamYear"]).sort_values("ExamYear")
            if agg.empty:
                return None
            fig = px.line(
                agg, x="ExamYear", y="CreditRate",
                markers=True,
                title="Credit Attainment Rate Over Time",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=[COLOR_PALETTE[1]],
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── CREDIT BY STATE & GENDER — grouped bar ────────────────────────────
        elif analysis == "Credit Attainment by State & Gender":
            if "State" not in df.columns or "Sex" not in df.columns:
                return None
            agg = credit_rate(df, ["State","Sex"]).sort_values("CreditRate", ascending=False)
            fig = px.bar(
                agg, x="State", y="CreditRate", color="Sex",
                barmode="group",
                title="Credit Rate by State and Gender",
                labels={"CreditRate": "Credit Rate (%)"},
                color_discrete_sequence=["#1e293b","#667eea"],
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False, tickangle=-35)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── BEST & WORST SUBJECTS — horizontal ranked bar ─────────────────────
        elif analysis == "Best & Worst Performing Subjects":
            agg = credit_rate(df, ["Subject"]).sort_values("CreditRate", ascending=False)
            if agg.empty:
                return None
            n   = int(filters.get("_top_n", 5))
            top = agg.head(n).copy()
            bot = agg.tail(n).copy()
            top["Rank"] = "Top " + str(n)
            bot["Rank"] = "Bottom " + str(n)
            combined = pd.concat([top, bot]).sort_values("CreditRate")
            fig = px.bar(
                combined, x="CreditRate", y="Subject", color="Rank",
                orientation="h",
                title=f"Top {n} and Bottom {n} Subjects by Credit Rate",
                color_discrete_map={
                    f"Top {n}":    "#16a34a",
                    f"Bottom {n}": "#dc2626",
                },
                text=combined["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(range=[0,100], ticksuffix="%", title="Credit Rate (%)")
            fig.update_yaxes(showgrid=False)
            return fig

        # ── SUBJECT PASS RATE COMPARISON — horizontal bar ─────────────────────
        elif analysis == "Subject Pass Rate Comparison":
            agg = pass_fail_rate(df, ["Subject"]).sort_values("PassRate", ascending=True)
            if agg.empty:
                return None
            fig = px.bar(
                agg, x="PassRate", y="Subject", orientation="h",
                title="Subject Pass Rate Comparison",
                color="PassRate",
                color_continuous_scale=["#dc2626","#d97706","#16a34a"],
                text=agg["PassRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(range=[0,100], ticksuffix="%", title="Pass Rate (%)")
            fig.update_yaxes(showgrid=False)
            return fig

        # ── SUBJECT PERFORMANCE BY STATE — heatmap-style bar ─────────────────
        elif analysis == "Subject Performance by State":
            if "Subject" not in df.columns or "State" not in df.columns:
                return None
            agg = credit_rate(df, ["Subject","State"])
            fig = px.bar(
                agg, x="State", y="CreditRate", color="Subject",
                barmode="group",
                title="Subject Credit Rate by State",
                labels={"CreditRate": "Credit Rate (%)"},
                color_discrete_sequence=COLOR_PALETTE,
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False, tickangle=-35)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── SUBJECT PERFORMANCE TRENDS — line chart ───────────────────────────
        elif analysis == "Subject Performance Trends":
            if "Subject" not in df.columns or "ExamYear" not in df.columns:
                return None
            agg = credit_rate(df, ["Subject","ExamYear"]).sort_values("ExamYear")
            fig = px.line(
                agg, x="ExamYear", y="CreditRate", color="Subject",
                markers=True,
                title="Subject Credit Rate Trends",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── GENDER PERFORMANCE GAP — line chart of credit rate by year ────────
        elif analysis == "Gender Performance Gap":
            if "Sex" not in df.columns or "ExamYear" not in df.columns:
                return None
            agg = credit_rate(df, ["ExamYear","Sex"]).sort_values("ExamYear")
            fig = px.line(
                agg, x="ExamYear", y="CreditRate", color="Sex",
                markers=True,
                title="Credit Rate by Exam Year — Male vs Female",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=["#1e293b","#667eea"],
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── AGE GROUP PERFORMANCE — horizontal bar ────────────────────────────
        elif analysis == "Age Group Performance Comparison":
            if "AgeGroup" not in df.columns:
                return None
            agg = credit_rate(df, ["AgeGroup"]).sort_values("CreditRate", ascending=True)
            fig = px.bar(
                agg, x="CreditRate", y="AgeGroup", orientation="h",
                title="Credit Rate by Age Group",
                color="CreditRate",
                color_continuous_scale=["#dc2626","#d97706","#16a34a"],
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(range=[0,100], ticksuffix="%", title="Credit Rate (%)")
            fig.update_yaxes(showgrid=False)
            return fig

        # ── DISABILITY ACHIEVEMENT GAP — grouped bar ──────────────────────────
        elif analysis == "Disability Achievement Gap":
            agg = credit_rate(df, ["Disability"]).sort_values("CreditRate", ascending=False)
            if agg.empty:
                return None
            fig = px.bar(
                agg, x="Disability", y="CreditRate",
                title="Credit Rate by Disability Status",
                color="Disability",
                color_discrete_sequence=COLOR_PALETTE,
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── COMBINED DEMOGRAPHIC — faceted bar ────────────────────────────────
        elif analysis == "Combined Demographic Performance":
            grp_cols = [c for c in ["Sex","AgeGroup","Disability"] if c in df.columns]
            if not grp_cols:
                return None
            agg = credit_rate(df, grp_cols).sort_values("CreditRate", ascending=False).head(20)
            agg["Group"] = agg[grp_cols].astype(str).agg(" | ".join, axis=1)
            fig = px.bar(
                agg, x="CreditRate", y="Group", orientation="h",
                title="Credit Rate by Combined Demographics (Top 20 Groups)",
                color="CreditRate",
                color_continuous_scale=["#dc2626","#d97706","#16a34a"],
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(range=[0,100], ticksuffix="%", title="Credit Rate (%)")
            fig.update_yaxes(showgrid=False)
            return fig

        # ── STATE PERFORMANCE RANKINGS — horizontal bar ───────────────────────
        elif analysis == "State Performance Rankings":
            agg = credit_rate(df, ["State"]).sort_values("CreditRate", ascending=True)
            fig = px.bar(
                agg, x="CreditRate", y="State", orientation="h",
                title="State Credit Rate Rankings",
                color="CreditRate",
                color_continuous_scale=["#dc2626","#d97706","#16a34a"],
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(range=[0,100], ticksuffix="%", title="Credit Rate (%)")
            fig.update_yaxes(showgrid=False)
            return fig

        # ── REGIONAL GAPS — grouped bar by zone ──────────────────────────────
        elif analysis == "Regional Performance Gaps":
            if "State" not in df.columns:
                return None
            df2 = df.copy()
            df2["Zone"] = df2["State"].apply(state_to_zone)
            agg = credit_rate(df2, ["Zone"]).sort_values("CreditRate", ascending=False)
            fig = px.bar(
                agg, x="Zone", y="CreditRate",
                title="Credit Rate by Geopolitical Zone",
                color="Zone",
                color_discrete_sequence=COLOR_PALETTE,
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── STATE PERFORMANCE TRENDS — multi-line chart ───────────────────────
        elif analysis == "State Performance Trends":
            if "State" not in df.columns or "ExamYear" not in df.columns:
                return None
            agg = credit_rate(df, ["State","ExamYear"]).sort_values("ExamYear")
            fig = px.line(
                agg, x="ExamYear", y="CreditRate", color="State",
                markers=True,
                title="State Credit Rate Trends",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── SCHOOL VS PRIVATE — grouped bar per year ──────────────────────────
        elif analysis == "School vs Private Candidate Performance":
            if "ExamType" not in df.columns or "ExamYear" not in df.columns:
                return None
            agg = credit_rate(df, ["ExamYear","ExamType"]).sort_values("ExamYear")
            fig = px.bar(
                agg, x="ExamYear", y="CreditRate", color="ExamType",
                barmode="group",
                title="Credit Rate by Exam Type per Year",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=COLOR_PALETTE,
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── EXAM TYPE PASS RATE — bar per exam type ───────────────────────────
        elif analysis == "Exam Type Pass Rate Comparison":
            agg = pass_fail_rate(df, ["ExamType"]).sort_values("PassRate", ascending=False)
            if agg.empty:
                return None
            fig = go.Figure()
            fig.add_bar(
                x=agg["ExamType"], y=agg["PassRate"],
                name="Pass Rate", marker_color="#16a34a",
                text=agg["PassRate"].astype(str) + "%",
                textposition="outside",
            )
            fig.add_bar(
                x=agg["ExamType"], y=agg["FailRate"],
                name="Fail Rate", marker_color="#dc2626",
                text=agg["FailRate"].astype(str) + "%",
                textposition="outside",
            )
            fig.update_layout(
                barmode="group", title="Exam Type Pass vs Fail Rate",
                **{k: v for k, v in _layout().items() if k != "colorway"},
                yaxis_title="Rate (%)", yaxis_range=[0, 100],
                yaxis_ticksuffix="%",
            )
            return fig

        # ── EXAM TYPE PERFORMANCE BY STATE ────────────────────────────────────
        elif analysis == "Exam Type Performance by State":
            if "ExamType" not in df.columns or "State" not in df.columns:
                return None
            agg = credit_rate(df, ["State","ExamType"]).sort_values("CreditRate", ascending=False)
            fig = px.bar(
                agg, x="State", y="CreditRate", color="ExamType",
                barmode="group",
                title="Credit Rate by State and Exam Type",
                labels={"CreditRate": "Credit Rate (%)"},
                color_discrete_sequence=COLOR_PALETTE,
                text=agg["CreditRate"].astype(str) + "%",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False, tickangle=-35)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── EXAM TYPE PERFORMANCE TRENDS — multi-line chart ───────────────────
        elif analysis == "Exam Type Performance Trends":
            if "ExamType" not in df.columns or "ExamYear" not in df.columns:
                return None
            agg = credit_rate(df, ["ExamType","ExamYear"]).sort_values("ExamYear")
            fig = px.line(
                agg, x="ExamYear", y="CreditRate", color="ExamType",
                markers=True,
                title="Exam Type Credit Rate Trends",
                labels={"CreditRate": "Credit Rate (%)", "ExamYear": "Exam Year"},
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", range=[0,100], ticksuffix="%")
            return fig

        # ── NON-ACADEMIC CHARTS (existing handlers) ───────────────────────────
        elif "Exam Type" in analysis or "ExamType" in analysis:
            if "ExamType" in df.columns and "ExamYear" in df.columns:
                g = df.groupby(["ExamYear","ExamType"])["Count"].sum().reset_index()
                fig = px.bar(g, x="ExamYear", y="Count", color="ExamType",
                             barmode="stack",
                             title="Candidates by Exam Year and Type",
                             color_discrete_sequence=COLOR_PALETTE)
                fig.update_layout(**L)
                return fig

        elif "Gender" in analysis or "Male" in analysis or "Female" in analysis:
            if "Sex" in df.columns and "ExamYear" in df.columns:
                g = df.groupby(["ExamYear","Sex"])["Count"].sum().reset_index()
                fig = px.bar(g, x="ExamYear", y="Count", color="Sex",
                             barmode="stack",
                             title="Candidates by Year — Gender Split",
                             color_discrete_sequence=["#1e293b","#667eea"])
                fig.update_layout(**L)
                return fig

        elif "Disability" in analysis:
            if "Disability" in df.columns and "ExamYear" in df.columns:
                g = df.groupby(["ExamYear","Disability"])["Count"].sum().reset_index()
                fig = px.line(g, x="ExamYear", y="Count", color="Disability",
                              markers=True, title="Disability Registrations by Year",
                              color_discrete_sequence=COLOR_PALETTE)
                fig.update_layout(**L)
                return fig

        elif "Registration" in analysis or "Enrollment" in analysis:
            if "ExamYear" in df.columns:
                if "Sex" in df.columns:
                    g = df.groupby(["ExamYear","Sex"])["Count"].sum().reset_index()
                    fig = px.line(g, x="ExamYear", y="Count", color="Sex",
                                  markers=True, title="Registration Trend",
                                  color_discrete_sequence=COLOR_PALETTE)
                else:
                    g = df.groupby("ExamYear")["Count"].sum().reset_index()
                    fig = px.line(g, x="ExamYear", y="Count", markers=True,
                                  title="Registration Trend",
                                  color_discrete_sequence=[COLOR_PALETTE[0]])
                fig.update_layout(**L)
                return fig

        elif "State" in analysis or "Regional" in analysis:
            if "State" in df.columns:
                g = df.groupby("State")["Count"].sum().reset_index()
                g = g.sort_values("Count", ascending=False).head(20)
                fig = px.bar(g, x="Count", y="State", orientation="h",
                             title="Top 20 States by Candidates",
                             color_discrete_sequence=[COLOR_PALETTE[0]])
                fig.update_layout(**L)
                return fig

        elif "Subject" in analysis or "Compulsory" in analysis:
            if "Subject" in df.columns and "Grade" in df.columns:
                top10 = df.groupby("Subject")["Count"].sum().nlargest(10).index
                g = df[df["Subject"].isin(top10)].groupby(["Subject","Grade"])["Count"].sum().reset_index()
                fig = px.bar(g, x="Subject", y="Count", color="Grade",
                             barmode="stack", title="Grade Distribution — Top 10 Subjects",
                             color_discrete_sequence=COLOR_PALETTE)
                fig.update_layout(**L)
                return fig

        # ── GENERIC FALLBACK ──────────────────────────────────────────────────
        else:
            for col in ["ExamYear","State","Sex","AgeGroup","ExamType","Sponsor"]:
                if col in df.columns:
                    g = df.groupby(col)["Count"].sum().reset_index().head(20)
                    g.columns = [col, "Count"]
                    fig = px.bar(g, x=col, y="Count", title=f"Distribution by {col}",
                                 color=col, color_discrete_sequence=COLOR_PALETTE)
                    fig.update_layout(**L)
                    return fig

    except Exception as e:
        st.warning(f"⚠️ Could not render chart: {e}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────
username   = st.session_state.get("user_email", "User").split("@")[0].title()
cart_count = len(report_cart)

st.markdown('<div class="page-header">📊 Your Reports</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="page-subtitle">Generated for {username} &nbsp;•&nbsp; '
    f'{datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>',
    unsafe_allow_html=True,
)
st.markdown(f"""
<div class="info-banner">
    <h3>✅ Payment Confirmed — {cart_count} Report{'s' if cart_count > 1 else ''} Ready</h3>
    <p>All performance metrics show rates (%), not raw candidate volumes.</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# RENDER EACH REPORT
# ─────────────────────────────────────────────────────────────────────────────
# chart_images_by_report stores the PNG paths indexed by report idx.
# These are collected BEFORE PDF generation so they are ready to embed.
chart_images_by_report: dict = {}

for idx, item in enumerate(report_cart, start=1):
    report_group = item.get("report_group", "—")
    subgroup     = item.get("subgroup",     "—")
    analysis     = item.get("analysis",     "—")
    filters      = item.get("filters",      {})
    description  = item.get("description",  "")
    record_count = item.get("record_count", 0)

    # Card header
    st.markdown(f"""
    <div class="report-section">
        <div class="report-section-header">
            Report {idx} of {cart_count} &mdash; {analysis}
        </div>
        <div class="report-meta">
            📂 {report_group} &nbsp;›&nbsp; {subgroup}
            &nbsp;·&nbsp; {record_count:,} candidate records
        </div>
    """, unsafe_allow_html=True)

    if description:
        st.markdown(f"""
        <div style="font-size:0.9rem;color:#475569;margin-bottom:1rem;
                    background:#f1f5f9;padding:10px 14px;border-radius:8px;">
            📌 {description}
        </div>
        """, unsafe_allow_html=True)

    if filters:
        chips_html = ""
        chip_colors = ["","blue","green","orange","red"]
        for i, (k, v) in enumerate(filters.items()):
            if k.startswith("_"):
                continue
            val_str = "All" if v == [] or v is None else (
                ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
            )
            c = chip_colors[i % len(chip_colors)]
            chips_html += f'<span class="stat-chip {c}">{k}: {val_str}</span>'
        st.markdown(f'<div style="margin-bottom:1rem;">{chips_html}</div>',
                    unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Load aggregated data
    with st.spinner(f"Loading Report {idx}: {analysis}…"):
        df = get_item_df(item)

    if df is None or df.empty:
        st.warning(
            f"⚠️ No data returned for Report {idx}. "
            "Try broadening your filter selection."
        )
        st.markdown("---")
        continue

    total = int(df["Count"].sum()) if "Count" in df.columns else 0

    # KPI boxes
    kpi_items = [("Total Results", fmt(record_count))]

    if "ExamYear" in df.columns:
        years = sorted(df["ExamYear"].dropna().unique().astype(int))
        kpi_items.append(("Years",
            f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])))

    # For academic reports, show rates not counts
    if "Grade" in df.columns:
        cr_total = int(df[df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
        kpi_items.append(("Credit Rate", pct(cr_total, total)))
        fail_total = int(df[df["Grade"] == "F9"]["Count"].sum())
        kpi_items.append(("Fail Rate", pct(fail_total, total)))

    if "State" in df.columns:
        top_state = df.groupby("State")["Count"].sum().idxmax()
        kpi_items.append(("Top State", top_state))

    if "Subject" in df.columns:
        top_sub = df.groupby("Subject")["Count"].sum().idxmax()
        kpi_items.append(("Top Subject", top_sub))

    kpi_html = '<div class="kpi-row">'
    for label, value in kpi_items:
        kpi_html += (
            f'<div class="kpi-box">'
            f'<div class="val">{value}</div>'
            f'<div class="lbl">{label}</div>'
            f"</div>"
        )
    kpi_html += "</div>"
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Narrative
    narrative = generate_narrative(analysis, df, filters)
    st.markdown(f'<div class="narrative-box">{narrative}</div>', unsafe_allow_html=True)

    # ── Chart ──────────────────────────────────────────────────────────────
    # Charts are rendered on screen AND their PNG bytes are saved to
    # session_state with a stable key like "chart_bytes_1_0".
    # The key format is: chart_bytes_{report_idx}_{chart_idx}
    # This survives the Streamlit rerun that happens when the user
    # clicks "Generate PDF" — local variables don't survive reruns,
    # but session_state does.
    result = build_chart(analysis, df, filters)

    if result is not None:
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        figs = result if isinstance(result, tuple) else (result,)
        for chart_idx, fig in enumerate(figs):
            # Display on screen
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            # Save bytes to session_state for PDF use
            chart_key = f"chart_bytes_{idx}_{chart_idx}"
            save_chart_to_session(fig, chart_key)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Chart not available for this report type with the current data.")

    # CSV download
    csv_data  = df.to_csv(index=False).encode("utf-8")
    safe_name = analysis.replace(" ", "_")[:40]
    st.download_button(
        label=f"📥 Download Data CSV — Report {idx}",
        data=csv_data,
        file_name=f"report_{idx}_{safe_name}.csv",
        mime="text/csv",
        key=f"csv_download_{idx}",
    )
    st.markdown("---")


# ─────────────────────────────────────────────────────────────────────────────
# COMBINED PDF
# Charts are read from session_state (set during the render loop above).
# Key format: chart_bytes_{report_idx}_{chart_idx}
# We scan up to 5 charts per report (virtually all reports have 1 or 2).
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="download-section">', unsafe_allow_html=True)
st.markdown("### 📄 Download Full Report PDF")
st.markdown("All reports, insights, and charts in one PDF.")

user_email  = st.session_state.get("user_email",  "user@edustat.com")
invoice_ref = st.session_state.get("invoice_ref", "N/A")


def generate_combined_pdf(report_cart, chart_images_by_report, user_email, invoice_ref):
    """
    Builds a PDF from:
    - report_cart: list of report items with filters and analysis names
    - chart_images_by_report: dict of {report_idx: [png_path, ...]}
      PNG paths were saved earlier when charts were rendered on screen.
    """
    styles        = getSampleStyleSheet()
    title_style   = ParagraphStyle("T", parent=styles["Title"],   fontSize=22,
                                   spaceAfter=6,  textColor=colors.HexColor("#1e293b"))
    head_style    = ParagraphStyle("H", parent=styles["Heading2"],fontSize=14,
                                   spaceAfter=4,  textColor=colors.HexColor("#1e293b"))
    sub_style     = ParagraphStyle("S", parent=styles["Normal"],  fontSize=11,
                                   spaceAfter=8,  textColor=colors.HexColor("#6c757d"))
    body_style    = ParagraphStyle("B", parent=styles["Normal"],  fontSize=11,
                                   leading=16,    spaceAfter=8)
    chip_style    = ParagraphStyle("C", parent=styles["Normal"],  fontSize=10,
                                   spaceAfter=6,  textColor=colors.HexColor("#374151"),
                                   backColor=colors.HexColor("#f1f5f9"))

    def footer(c, doc):
        c.saveState()
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#6c757d"))
        pw = landscape(A4)[0]
        c.drawString(40, 20, f"© {datetime.now().year} Edustat — Confidential")
        c.drawString((pw/2)-60, 20, f"Invoice: {invoice_ref}")
        c.drawRightString(pw-40, 20, user_email)
        c.restoreState()

    elements     = []
    user_display = user_email.split("@")[0].replace(".", " ").title()

    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Edustat Analytics Report", title_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Prepared for: {user_display}", sub_style))
    elements.append(Paragraph(
        f"Date: {datetime.now().strftime('%B %d, %Y')}  |  "
        f"Invoice: {invoice_ref}  |  Reports: {len(report_cart)}",
        sub_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#1e293b"), spaceAfter=20))

    for i, item in enumerate(report_cart, start=1):
        analysis    = item.get("analysis",    "—")
        subgroup    = item.get("subgroup",    "—")
        group       = item.get("report_group","—")
        filters_i   = item.get("filters",     {})
        description = item.get("description", "")
        rec_count   = item.get("record_count", 0)

        elements.append(Paragraph(f"Report {i}: {analysis}", head_style))
        elements.append(Paragraph(f"{group}  ›  {subgroup}", sub_style))
        elements.append(Paragraph(f"Candidate records: {rec_count:,}", chip_style))

        if description:
            elements.append(Paragraph(description, chip_style))

        # Filter table
        if filters_i:
            rows = [["Filter", "Value"]]
            for k, v in filters_i.items():
                if k.startswith("_"):
                    continue
                val_str = ("All" if v == [] or v is None else
                           (", ".join(str(x) for x in v) if isinstance(v, list) else str(v)))
                rows.append([k, val_str])
            ft = Table(rows, colWidths=[160, 500])
            ft.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
                ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
                ("FONTSIZE",      (0,0),(-1,-1), 10),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.HexColor("#f8fafc"), colors.white]),
                ("GRID",          (0,0),(-1,-1), 0.25, colors.HexColor("#e2e8f0")),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("TOPPADDING",    (0,0),(-1,-1), 6),
            ]))
            elements.append(Spacer(1, 6))
            elements.append(ft)
            elements.append(Spacer(1, 10))

        # Narrative
        df_item = get_item_df(item)
        if df_item is not None and not df_item.empty:
            narrative = generate_narrative(analysis, df_item, filters_i)
            elements.append(Paragraph("Insights", head_style))
            elements.append(Paragraph(narrative.replace("**", ""), body_style))
            elements.append(Spacer(1, 10))

        # Charts — use pre-saved PNGs from the screen render
        img_paths = chart_images_by_report.get(i, [])
        if img_paths:
            elements.append(Paragraph("Visualisation", head_style))
            for img_path in img_paths:
                if img_path and os.path.exists(img_path):
                    elements.append(Image(img_path, width=660, height=330))
                    elements.append(Spacer(1, 12))
        else:
            # Fallback: try to regenerate chart for PDF
            if df_item is not None and not df_item.empty:
                result = build_chart(analysis, df_item, filters_i)
                if result is not None:
                    elements.append(Paragraph("Visualisation", head_style))
                    for fig in (result if isinstance(result, tuple) else (result,)):
                        p = save_chart_image(fig)
                        if p and os.path.exists(p):
                            elements.append(Image(p, width=660, height=330))
                            elements.append(Spacer(1, 12))

        elements.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#e2e8f0"), spaceAfter=16))
        if i < len(report_cart):
            elements.append(PageBreak())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        doc = SimpleDocTemplate(
            tmp.name, pagesize=landscape(A4),
            leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40,
        )
        doc.build(elements, onFirstPage=footer, onLaterPages=footer)
        return tmp.name


if st.button("🔄 Generate Combined PDF", type="primary"):
    with st.spinner("Building PDF…"):
        try:
            pdf_path = generate_combined_pdf(
                report_cart, chart_images_by_report, user_email, invoice_ref
            )
            with open(pdf_path, "rb") as f:
                pdf_bytes = BytesIO(f.read())
                pdf_bytes.seek(0)
            try:
                pdf_output = add_watermark(
                    input_pdf_stream=pdf_bytes,
                    watermark_image_path="altered_edustat.jpg",
                )
            except Exception:
                pdf_bytes.seek(0)
                pdf_output = pdf_bytes.read()

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "📄 Download Full PDF Report", pdf_output,
                file_name=f"Edustat_Report_{ts}.pdf",
                mime="application/pdf",
                key="final_pdf_download",
            )
            st.success("✅ PDF ready!")
        except Exception as e:
            st.error(f"❌ PDF generation failed: {e}")

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    if st.button("← Back to Dashboard"):
        st.switch_page("pages/dashboard.py")
with col2:
    if st.button("➕ Create Another Report"):
        st.switch_page("pages/create_report.py")
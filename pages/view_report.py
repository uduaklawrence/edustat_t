# ==============================
# 📊 VIEW REPORT — EDUSTAT
# ==============================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import numpy as np
import os
from geo_config import state_to_zone, ZONES
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
                CAST(State AS VARCHAR)    AS State,
                CAST(Sex AS VARCHAR)      AS Sex,
                CAST(AgeGroup AS VARCHAR) AS AgeGroup,
                CAST(Disability AS VARCHAR) AS Disability,
                CAST(Subject AS VARCHAR)  AS Subject,
                CAST(ExamType AS VARCHAR) AS ExamType,
                CAST(Grade AS VARCHAR)    AS Grade,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY ExamYear, State, Sex, AgeGroup,
                     Disability, Subject, ExamType, Grade
            ORDER BY ExamYear, Grade
        """)

    # ── EXAM TYPE VOLUME/GENDER ───────────────────────────────────────────────
    elif analysis == "Exam Type by Gender":
        return _run(f"""
            SELECT
                CAST(ExamType AS VARCHAR) AS ExamType,
                CAST(Sex AS VARCHAR) AS Sex,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY CAST(ExamType AS VARCHAR), CAST(Sex AS VARCHAR)
            ORDER BY ExamType, Sex
        """)

    elif analysis == "Exam Type by State":
        return _run(f"""
            SELECT
                CAST(ExamType AS VARCHAR) AS ExamType,
                CAST(State AS VARCHAR) AS State,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY CAST(ExamType AS VARCHAR), CAST(State AS VARCHAR)
            ORDER BY State, ExamType
        """)

    elif analysis == "Exam Type Volume Comparison":
        return _run(f"""
            SELECT
                CAST(ExamType AS VARCHAR) AS ExamType,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY CAST(ExamType AS VARCHAR)
            ORDER BY Count DESC
        """)

    elif analysis == "Exam Type Share by Year":
        return _run(f"""
            SELECT
                CAST(ExamType AS VARCHAR) AS ExamType,
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY CAST(ExamType AS VARCHAR), TRY_CAST(ExamYear AS INTEGER)
            ORDER BY ExamYear, ExamType
        """)

    elif "Exam Type" in analysis or "ExamType" in analysis:
        return _run(f"""
            SELECT
                CAST(ExamType AS VARCHAR) AS ExamType,
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                CAST(Sex AS VARCHAR) AS Sex,
                COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY CAST(ExamType AS VARCHAR), TRY_CAST(ExamYear AS INTEGER), CAST(Sex AS VARCHAR)
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
    elif analysis == "Age Range of Candidates":
        age_extra = (
            "AND TRY_CAST(DateOfBirth AS DATE) IS NOT NULL "
            "AND (TRY_CAST(ExamYear AS INTEGER) - YEAR(TRY_CAST(DateOfBirth AS DATE))) "
            "BETWEEN 5 AND 70"
        )
        where_age = (w + " " + age_extra) if w else (
            "WHERE TRY_CAST(DateOfBirth AS DATE) IS NOT NULL "
            "AND (TRY_CAST(ExamYear AS INTEGER) - YEAR(TRY_CAST(DateOfBirth AS DATE))) "
            "BETWEEN 5 AND 70"
        )
        raw = _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER)                                          AS ExamYear,
                CAST(State AS VARCHAR)                                                 AS State,
                (TRY_CAST(ExamYear AS INTEGER) - YEAR(TRY_CAST(DateOfBirth AS DATE))) AS Age,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR))                               AS Count
            FROM {s} {where_age}
            GROUP BY
                TRY_CAST(ExamYear AS INTEGER),
                CAST(State AS VARCHAR),
                (TRY_CAST(ExamYear AS INTEGER) - YEAR(TRY_CAST(DateOfBirth AS DATE)))
            ORDER BY ExamYear, State, Age
        """)
        if raw is None or raw.empty:
            return raw
        raw["AgeTotal"] = raw.groupby("Age")["Count"].transform("sum")
        return raw
    
        # Sum counts across all years so each age bucket shows total candidates
        # regardless of how many exam years the user selected
        result = raw.groupby("Age")["Count"].sum().reset_index()
        return result

    elif analysis == "Age Distribution by Exam Year":
        age_extra = "AND AgeGroup != 'Unknown' AND AgeGroup IS NOT NULL"
        where_age = (w + " " + age_extra) if w else (
            "WHERE AgeGroup != 'Unknown' AND AgeGroup IS NOT NULL"
        )
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                AgeGroup,
                COUNT(*) AS Count
        FROM {s} {where_age}
        GROUP BY ExamYear, AgeGroup
        ORDER BY ExamYear, AgeGroup
        """)

    elif analysis == "Generational Education Trends":
        gen_extra = "AND TRY_CAST(DateOfBirth AS DATE) IS NOT NULL"
        where_gen = (w + " " + gen_extra) if w else (
            "WHERE TRY_CAST(DateOfBirth AS DATE) IS NOT NULL"
        )
        return _run(f"""
            SELECT
                CASE
                    WHEN YEAR(TRY_CAST(DateOfBirth AS DATE)) BETWEEN 1928 AND 1945
                        THEN 'Silent Generation (1928–1945)'
                    WHEN YEAR(TRY_CAST(DateOfBirth AS DATE)) BETWEEN 1946 AND 1964
                        THEN 'Baby Boomers (1946–1964)'
                    WHEN YEAR(TRY_CAST(DateOfBirth AS DATE)) BETWEEN 1965 AND 1980
                        THEN 'Gen X (1965–1980)'
                    WHEN YEAR(TRY_CAST(DateOfBirth AS DATE)) BETWEEN 1981 AND 1996
                        THEN 'Millennials (1981–1996)'
                    WHEN YEAR(TRY_CAST(DateOfBirth AS DATE)) BETWEEN 1997 AND 2012
                        THEN 'Gen Z (1997–2012)'
                    WHEN YEAR(TRY_CAST(DateOfBirth AS DATE)) BETWEEN 2013 AND 2025
                        THEN 'Gen Alpha (2013–2025)'
                    ELSE 'Unknown'
                END                                      AS Generation,
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                CAST(State AS VARCHAR)                   AS State,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count
            FROM {s} {where_gen}
            GROUP BY Generation,
                     TRY_CAST(ExamYear AS INTEGER),
                     CAST(State AS VARCHAR)
            ORDER BY ExamYear, Generation
        """)

    elif analysis == "Age-Appropriate Enrollment Assessment":
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
    elif analysis == "State Registration Trends":
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                CAST(State AS VARCHAR)                   AS State,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count
            FROM {s} {w}
            GROUP BY
                TRY_CAST(ExamYear AS INTEGER),
                CAST(State AS VARCHAR)
            ORDER BY ExamYear, State
        """)

    elif analysis == "State Growth Rate Analysis":
        return _run(f"""
            SELECT
                CAST(State AS VARCHAR)                   AS State,
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count
            FROM {s} {w}
            GROUP BY
                CAST(State AS VARCHAR),
                TRY_CAST(ExamYear AS INTEGER)
            ORDER BY State, ExamYear
        """)

    elif analysis == "Registration Trends & Growth Rate":
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count
            FROM {s} {w}
            GROUP BY TRY_CAST(ExamYear AS INTEGER)
            ORDER BY ExamYear
        """)
    
    elif analysis == "Registration by Exam Type":
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                CAST(ExamType AS VARCHAR)                AS ExamType,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count
            FROM {s} {w}
            GROUP BY
                TRY_CAST(ExamYear AS INTEGER),
                CAST(ExamType AS VARCHAR)
            ORDER BY ExamYear, ExamType
        """)

    elif "Registration" in analysis or "Enrollment" in analysis:
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                CAST(State AS VARCHAR)                   AS State,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count
            FROM {s} {w}
            GROUP BY
                TRY_CAST(ExamYear AS INTEGER),
                CAST(State AS VARCHAR)
            ORDER BY ExamYear, State
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
    elif analysis == "Candidate Load per Centre":
        top_n     = int(filters.get("TopN", 10))
        direction = filters.get("LoadDirection", "Highest")
        w_clean   = _where(
            {k: v for k, v in filters.items()
             if k not in ("TopN", "LoadDirection")}
        )

        base_query = f"""
            SELECT
                CAST(centre AS VARCHAR)  AS centre,
                CAST(State  AS VARCHAR)  AS State,
                COUNT(DISTINCT
                    CAST(TRY_CAST(ExamYear AS INTEGER) AS VARCHAR)
                    || '-' || CAST(ExamNum AS VARCHAR)
                )                        AS CandidateLoad
            FROM read_parquet('{_GLOB}',
                              hive_partitioning=true,
                              union_by_name=true)
            {w_clean}
            GROUP BY
                CAST(centre AS VARCHAR),
                CAST(State  AS VARCHAR)
        """

        if "Both" in direction:
            top_df = _run(
                base_query + f" ORDER BY CandidateLoad DESC LIMIT {top_n}"
            )
            bot_df = _run(
                base_query + f" ORDER BY CandidateLoad ASC  LIMIT {top_n}"
            )
            if top_df is not None and bot_df is not None:
                top_df["RankGroup"] = f"Highest {top_n}"
                bot_df["RankGroup"] = f"Lowest {top_n}"
                return pd.concat([top_df, bot_df], ignore_index=True)
            return top_df if top_df is not None else bot_df

        elif "Lowest" in direction:
            return _run(
                base_query + f" ORDER BY CandidateLoad ASC LIMIT {top_n}"
            )
        else:
            return _run(
                base_query + f" ORDER BY CandidateLoad DESC LIMIT {top_n}"
            )
    
    elif "Centre" in analysis or "Center" in analysis:
        return _run(f"""
            SELECT centre, State, COUNT(*) AS Count
            FROM {s} {w}
            GROUP BY centre, State
            ORDER BY Count DESC
            LIMIT 50
        """)

    # TOP & BOTTOM STATES BY CANDIDATE LOAD
    elif analysis == "Top & Bottom States by Candidate Volume":
        top_n      = int(filters.get("TopN", 5))
        sel_years  = filters.get("ExamYear", [])
        w_yr       = _where({"ExamYear": sel_years}) if sel_years else ""

        # Get ranked states across all selected years first
        ranked = _run(f"""
            SELECT
                CAST(State AS VARCHAR)                   AS State,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS TotalCount
            FROM {s} {w_yr}
            GROUP BY CAST(State AS VARCHAR)
            ORDER BY TotalCount DESC
        """)
        if ranked is None or ranked.empty:
            return ranked

        top_states = ranked.head(top_n)["State"].tolist()
        bot_states = ranked.tail(top_n)["State"].tolist()
        combined   = list(dict.fromkeys(top_states + bot_states))
        combined_q = ", ".join(f"'{s}'" for s in combined)

        # Per-year counts for those states
        if sel_years:
            yr_q = ", ".join(str(int(y)) for y in sel_years)
            where_final = (
                f"WHERE CAST(State AS VARCHAR) IN ({combined_q}) "
                f"AND TRY_CAST(ExamYear AS INTEGER) IN ({yr_q})"
            )
        else:
            where_final = f"WHERE CAST(State AS VARCHAR) IN ({combined_q})"

        return _run(f"""
            SELECT
                CAST(State AS VARCHAR)                   AS State,
                TRY_CAST(ExamYear AS INTEGER)            AS ExamYear,
                COUNT(DISTINCT CAST(ExamNum AS VARCHAR)) AS Count,
                CASE
                    WHEN CAST(State AS VARCHAR) IN ({', '.join(f"'{s}'" for s in top_states)})
                    THEN 'Top {top_n}'
                    ELSE 'Bottom {top_n}'
                END AS RankGroup
            FROM read_parquet('{_GLOB}',
                              hive_partitioning=true,
                              union_by_name=true)
            {where_final}
            GROUP BY
                CAST(State AS VARCHAR),
                TRY_CAST(ExamYear AS INTEGER),
                RankGroup
            ORDER BY ExamYear, RankGroup DESC, Count DESC
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
    elif analysis == "Registered vs Sat Candidates":
        filters_no_status = {k: v for k, v in filters.items() if k != "Status"}
        w_no_status = _where(filters_no_status)
        # Get the user-selected statuses to highlight, default to Absent + Cancelled
        selected_statuses = filters.get("Status", ["Absent", "Cancelled"])
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                CAST(State AS VARCHAR) AS State,
                CAST(Status AS VARCHAR) AS Status,
                COUNT(*) AS Count
            FROM read_parquet('{_GLOB}', hive_partitioning=true, union_by_name=true)
            {w_no_status}
            GROUP BY
                TRY_CAST(ExamYear AS INTEGER),
                CAST(State AS VARCHAR),
                CAST(Status AS VARCHAR)
            ORDER BY ExamYear, State
        """)

    elif analysis == "Absenteeism Rate by State":
        filters_no_status = {k: v for k, v in filters.items() if k != "Status"}
        w_no_status = _where(filters_no_status)
        return _run(f"""
            SELECT
                CAST(State AS VARCHAR) AS State,
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                CAST(Status AS VARCHAR) AS Status,
                COUNT(*) AS Count
            FROM {s} {w_no_status}
            GROUP BY State, ExamYear, Status
            ORDER BY State, ExamYear
        """)

    elif analysis == "Absenteeism by Exam Type":
        filters_no_status = {k: v for k, v in filters.items() if k != "Status"}
        w_no_status = _where(filters_no_status)
        return _run(f"""
            SELECT
                CAST(ExamType AS VARCHAR) AS ExamType,
                CAST(Status AS VARCHAR) AS Status,
                COUNT(*) AS Count
            FROM read_parquet('{_GLOB}', hive_partitioning=true, union_by_name=true)
            {w_no_status}
            GROUP BY
                CAST(ExamType AS VARCHAR),
                CAST(Status AS VARCHAR)
            ORDER BY ExamType
        """)

    elif analysis == "Absenteeism by Gender":
        filters_no_status = {k: v for k, v in filters.items() if k != "Status"}
        w_no_status = _where(filters_no_status)
        return _run(f"""
            SELECT
                CAST(Sex AS VARCHAR) AS Sex,
                CAST(Status AS VARCHAR) AS Status,
                COUNT(*) AS Count
            FROM read_parquet('{_GLOB}', hive_partitioning=true, union_by_name=true)
            {w_no_status}
            GROUP BY
                CAST(Sex AS VARCHAR),
                CAST(Status AS VARCHAR)
            ORDER BY Sex
        """)

    elif analysis == "Absenteeism Trends Over Time":
        filters_no_status = {k: v for k, v in filters.items() if k != "Status"}
        w_no_status = _where(filters_no_status)
        return _run(f"""
            SELECT
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                CAST(Status AS VARCHAR) AS Status,
                COUNT(*) AS Count
            FROM {s} {w_no_status}
            GROUP BY ExamYear, Status
            ORDER BY ExamYear
        """)

    elif "Absenteeism" in analysis or "Attendance" in analysis or "Sat" in analysis:
        return _run(f"""
            SELECT
                CAST(Status AS VARCHAR) AS Status,
                TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                CAST(State AS VARCHAR) AS State,
                CAST(Sex AS VARCHAR) AS Sex,
                CAST(ExamType AS VARCHAR) AS ExamType,
                COUNT(*) AS Count
            FROM {s} {w}
            WHERE Status IS NOT NULL
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
def _grade_narrative(analysis: str, df: pd.DataFrame, filters: dict,
                     total: int, filter_desc: str) -> str:
    """Handles all analysis types that require Grade column."""

    if analysis == "Full Grade Breakdown":
        gd    = df.groupby("Grade")["Count"].sum().sort_values(ascending=False)
        top_g = gd.index[0]
        top_ct = int(gd.iloc[0])
        cr_total = int(df[df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
        return (
            f"Full grade breakdown. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. Most common grade: **{top_g}** "
            f"({pct(top_ct, total)}). "
            f"Credit grades (A1–C6): **{fmt(cr_total)}** ({pct(cr_total, total)})."
        )

    elif analysis == "Pass vs Fail Rate":
        pass_grades = filters.get("_pass_grades") or list(PASS_GRADES)
        fail_grades = filters.get("_fail_grades") or ["F9"]
        pass_ct = int(df[df["Grade"].isin(pass_grades)]["Count"].sum())
        fail_ct = int(df[df["Grade"].isin(fail_grades)]["Count"].sum())
        return (
            f"Pass vs Fail analysis. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. "
            f"Pass rate: **{pct(pass_ct, total)}** ({fmt(pass_ct)}). "
            f"Fail rate: **{pct(fail_ct, total)}** ({fmt(fail_ct)}). "
            + ("✅ Majority passed." if pass_ct > fail_ct
               else "⚠️ More candidates failed than passed.")
        )

    elif analysis == "Grade Distribution by Exam Year":
        agg = credit_rate(df, ["ExamYear"]).sort_values("ExamYear")
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        best  = agg.loc[agg["CreditRate"].idxmax()]
        worst = agg.loc[agg["CreditRate"].idxmin()]
        return (
            f"Grade distribution by exam year. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. "
            f"Best year: **{int(best['ExamYear'])}** — {best['CreditRate']}% credit rate. "
            f"Worst year: **{int(worst['ExamYear'])}** — {worst['CreditRate']}%."
        )

    elif analysis == "Grade Distribution by State":
        agg = credit_rate(df, ["State"]).sort_values("CreditRate", ascending=False)
        if agg.empty:
            return f"Total: {fmt(total)}. Filters: {filter_desc}."
        return (
            f"Grade distribution by state. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** across **{agg['State'].nunique()}** states. "
            f"Top: **{agg.iloc[0]['State']}** — {agg.iloc[0]['CreditRate']}%. "
            f"Bottom: **{agg.iloc[-1]['State']}** — {agg.iloc[-1]['CreditRate']}%."
        )

    elif analysis == "Gender Performance Gap":
        sex_agg  = credit_rate(df, ["Sex"])
        male_r   = float(sex_agg.loc[sex_agg["Sex"]=="Male",   "CreditRate"].values[0]) if "Male"   in sex_agg["Sex"].values else 0
        female_r = float(sex_agg.loc[sex_agg["Sex"]=="Female", "CreditRate"].values[0]) if "Female" in sex_agg["Sex"].values else 0
        gap      = round(abs(male_r - female_r), 1)
        better   = "females" if female_r > male_r else "males"
        return (
            f"Gender performance gap. Filters: {filter_desc}. Total: **{fmt(total)}**. "
            f"Male credit rate: **{male_r}%**. Female: **{female_r}%**. "
            f"**{better.title()}** outperform by **{gap}pp**."
        )

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
            f"Total: **{fmt(total)}** across **{agg['State'].nunique()}** states. "
            f"Top 5: {top5}. Bottom 5: {bot5}."
        )

    # Generic grade fallback
    else:
        cr_total = int(df[df["Grade"].isin(CREDIT_GRADES)]["Count"].sum())
        agg = credit_rate(df, ["ExamYear"]).sort_values("ExamYear") if "ExamYear" in df.columns else pd.DataFrame()
        trend = trend_dir(agg.set_index("ExamYear")["CreditRate"]) if not agg.empty else "stable"
        return (
            f"**{analysis}**. Filters: {filter_desc}. Total: **{fmt(total)}**. "
            f"Credit rate (A1–C6): **{pct(cr_total, total)}**. "
            f"Trend: **{trend}**."
        )

    

def generate_narrative(analysis: str, df: pd.DataFrame, filters: dict) -> dict:
    """
    Returns a structured insight dict:
    {
        "summary":         str,
        "key_findings":    [str, ...],
        "observations":    [str, ...],
        "implications":    [str, ...],
        "recommendations": [str, ...],
    }
    """
    def _empty(reason: str) -> dict:
        return {
            "summary":         reason,
            "key_findings":    [],
            "observations":    [],
            "implications":    [],
            "recommendations": [],
        }

    if df is None or df.empty:
        return _empty("No data available for the selected filters.")

    total       = int(df["Count"].sum()) if "Count" in df.columns else 0
    filter_desc = filter_label(filters)

    def has(col):
        return col in df.columns and not df[col].dropna().empty

    # ── AGE REPORTS ───────────────────────────────────────────────────────────
    if analysis == "Age Range of Candidates":
        if "Age" not in df.columns:
            return _empty(f"Age range report. Total: **{fmt(total)}**. Filters: {filter_desc}.")

        age_dist = df.groupby("Age")["Count"].sum()
        youngest = int(age_dist.index.min())
        oldest   = int(age_dist.index.max())
        peak_age = int(age_dist.idxmax())
        peak_ct  = int(age_dist.max())

        def bracket(a):
            if a < 15:  return "Under 15"
            if a <= 17: return "15–17"
            if a <= 20: return "18–20"
            if a <= 25: return "21–25"
            if a <= 35: return "26–35"
            return "Over 35"

        df2             = df.copy()
        df2["Bracket"]  = df2["Age"].apply(bracket)
        bracket_agg     = df2.groupby("Bracket")["Count"].sum().sort_values(ascending=False)
        top_bracket     = bracket_agg.index[0]
        top_bracket_ct  = int(bracket_agg.iloc[0])
        bot_bracket     = bracket_agg.index[-1]
        bot_bracket_ct  = int(bracket_agg.iloc[-1])

        selected_years  = filters.get("ExamYear", [])
        selected_states = filters.get("State", [])
        yr_part  = f"exam years **{', '.join(str(y) for y in selected_years)}**" if selected_years else "all available exam years"
        st_part  = f"states **{', '.join(selected_states)}**"                    if selected_states else "all states"

        # State breakdown if available
        state_obs = []
        if has("State"):
            st_agg = df2.groupby("State")["Count"].sum().sort_values(ascending=False)
            top_st = st_agg.index[0]
            top_st_ct = int(st_agg.iloc[0])
            bot_st = st_agg.index[-1]
            bot_st_ct = int(st_agg.iloc[-1])
            state_obs.append(
                f"**{top_st}** recorded the highest candidate volume — "
                f"{fmt(top_st_ct)} ({pct(top_st_ct, total)})."
            )
            state_obs.append(
                f"**{bot_st}** recorded the lowest — "
                f"{fmt(bot_st_ct)} ({pct(bot_st_ct, total)})."
            )

        # Year trend if available
        yr_obs = []
        if has("ExamYear") and len(selected_years) > 1:
            yr_agg   = df2.groupby("ExamYear")["Count"].sum().sort_values()
            peak_yr  = int(yr_agg.idxmax())
            peak_yr_ct = int(yr_agg.max())
            yr_obs.append(
                f"Candidate volume peaked in **{peak_yr}** with "
                f"{fmt(peak_yr_ct)} unique candidates ({pct(peak_yr_ct, total)})."
            )
            direction = "increased" if yr_agg.iloc[-1] > yr_agg.iloc[0] else "decreased"
            yr_obs.append(
                f"Overall registration {direction} from "
                f"**{fmt(int(yr_agg.iloc[0]))}** in {int(yr_agg.index[0])} "
                f"to **{fmt(int(yr_agg.iloc[-1]))}** in {int(yr_agg.index[-1])}."
            )

        return {
            "summary": (
                f"This report analyses the age distribution of **{fmt(total)}** unique candidates "
                f"across {yr_part} and {st_part}. "
                f"Candidate ages range from **{youngest}** to **{oldest}** years, "
                f"with age **{peak_age}** recording the highest enrolment."
            ),
            "key_findings": [
                f"Total unique candidates analysed: **{fmt(total)}**.",
                f"Age range: **{youngest}** (youngest) to **{oldest}** (oldest).",
                f"Peak age: **{peak_age}** — {fmt(peak_ct)} candidates ({pct(peak_ct, total)}).",
                f"Most dominant age bracket: **{top_bracket}** — "
                f"{fmt(top_bracket_ct)} candidates ({pct(top_bracket_ct, total)}).",
                f"Least represented bracket: **{bot_bracket}** — "
                f"{fmt(bot_bracket_ct)} candidates ({pct(bot_bracket_ct, total)}).",
            ],
            "observations": (
                [
                    f"The **{top_bracket}** age group dominates enrolment, suggesting "
                    f"most candidates sit the examination at the standard school-leaving age.",
                    f"Candidates aged **{youngest}** represent early or exceptional enrolment cases "
                    f"that may warrant further investigation.",
                    f"Candidates aged **{oldest}** represent mature or returning candidates, "
                    f"indicating continued demand for qualification attainment beyond school age.",
                ]
                + yr_obs
                + state_obs
            ),
            "implications": [
                "High concentration in the 15–20 age bracket aligns with standard secondary "
                "school completion ages, indicating the examination system is functioning "
                "as intended for its primary demographic.",
                "The presence of candidates under 15 may indicate grade acceleration or "
                "data quality issues that merit review.",
                f"The spread across {len(bracket_agg)} age brackets suggests diverse "
                "candidate populations including mature students and re-sitters.",
            ],
            "recommendations": [
                "Investigate the under-15 cohort to confirm whether early enrolment "
                "is intentional policy or a data entry anomaly.",
                "Design targeted support programmes for the over-25 age group, "
                "who may face different barriers to performance than school-age candidates.",
                f"Monitor the {bot_bracket} bracket over time — low representation "
                "may indicate structural barriers to access for that age group.",
                "Cross-reference age distribution with performance (Grade) data to assess "
                "whether age correlates with academic outcomes.",
            ],
        }

    elif analysis == "Age Distribution by Exam Year":
        if "AgeGroup" not in df.columns or "ExamYear" not in df.columns:
            return _empty(
                f"Age distribution report. Total: **{fmt(total)}**. Filters: {filter_desc}."
            )

        selected_years  = sorted([int(y) for y in filters.get("ExamYear", [])])
        selected_states = filters.get("State", [])

        yr_part  = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )
        st_part  = (
            f"states **{', '.join(selected_states)}**"
            if selected_states else "all states"
        )

        ag_totals = df.groupby("AgeGroup")["Count"].sum().sort_values(ascending=False)
        dominant  = ag_totals.index[0]
        minor     = ag_totals.index[-1]
        dom_ct    = int(ag_totals.iloc[0])
        min_ct    = int(ag_totals.iloc[-1])
        dom_pct   = round(dom_ct / total * 100, 1)
        min_pct   = round(min_ct / total * 100, 1)

        # Per year breakdown for each age group
        yr_pivot = df.groupby(["ExamYear", "AgeGroup"])["Count"].sum().unstack(fill_value=0)
        yr_list  = sorted(yr_pivot.index.astype(int).tolist())

        # Year-on-year trend for dominant group
        dom_trend = df[df["AgeGroup"] == dominant].groupby("ExamYear")["Count"].sum().sort_index()
        trend_direction = ""
        trend_str       = ""
        if len(dom_trend) >= 2:
            first_yr  = int(dom_trend.index[0])
            last_yr   = int(dom_trend.index[-1])
            first_ct  = int(dom_trend.iloc[0])
            last_ct   = int(dom_trend.iloc[-1])
            change    = last_ct - first_ct
            change_pct = round(abs(change) / first_ct * 100, 1) if first_ct > 0 else 0
            trend_direction = "increased" if change > 0 else "decreased"
            trend_str = (
                f"The **{dominant}** group {trend_direction} by "
                f"**{change_pct}%** — from {fmt(first_ct)} in {first_yr} "
                f"to {fmt(last_ct)} in {last_yr}."
            )

        # Peak year
        yr_totals = df.groupby("ExamYear")["Count"].sum().sort_values(ascending=False)
        peak_yr   = int(yr_totals.index[0])
        peak_yr_ct = int(yr_totals.iloc[0])

        # Build per-year findings
        per_year_findings = []
        for yr in yr_list:
            yr_df = df[df["ExamYear"] == yr]
            yr_total = int(yr_df["Count"].sum())
            for grp, ct in yr_df.groupby("AgeGroup")["Count"].sum().items():
                per_year_findings.append(
                    f"{yr} — **{grp}**: {fmt(int(ct))} candidates "
                    f"({round(int(ct)/yr_total*100, 1)}% of that year's cohort)."
                )

        return {
            "summary": (
                f"This report examines how candidate age groups are distributed across "
                f"{yr_part} and {st_part}. "
                f"A total of **{fmt(total)}** unique candidates were analysed across "
                f"**{len(yr_list)}** exam year{'s' if len(yr_list) > 1 else ''}. "
                f"The data reveals the proportion of candidates falling below and above "
                f"the standard school-leaving age threshold, providing insight into "
                f"enrolment patterns and demographic shifts over time."
            ),
            "key_findings": [
                f"Total unique candidates across all selected years: **{fmt(total)}**.",
                f"Dominant age group: **{dominant}** — {fmt(dom_ct)} candidates ({dom_pct}%).",
                f"Minority age group: **{minor}** — {fmt(min_ct)} candidates ({min_pct}%).",
                f"Peak enrolment year: **{peak_yr}** — {fmt(peak_yr_ct)} candidates.",
                trend_str if trend_str else f"Trend data covers {len(yr_list)} year(s).",
            ],
            "observations": (
                per_year_findings
                + [
                    f"The **{dominant}** age group consistently outnumbers the **{minor}** "
                    f"group across all selected years, confirming the dominance of the "
                    f"standard-age candidate cohort.",
                    f"Year-on-year fluctuations in the **{minor}** group may reflect "
                    f"policy changes, population growth, or improved access to early education.",
                ]
            ),
            "implications": [
                f"The high proportion of **{dominant}** candidates ({dom_pct}%) confirms "
                f"that the examination system is serving its primary demographic effectively. "
                f"However, monitoring year-on-year shifts remains important for policy planning.",
                f"A rising **{minor}** group over successive years would signal increased "
                f"access to early examination opportunities or demographic changes in the "
                f"school-age population.",
                "Year-on-year fluctuations in total enrolment may reflect economic conditions, "
                "school access, or administrative changes in examination administration.",
                f"The gap between the **{dominant}** and **{minor}** groups can inform "
                f"resource allocation decisions — particularly for examination centre capacity "
                f"and invigilator deployment.",
            ],
            "recommendations": [
                f"Track the **{minor}** ({minor}) cohort longitudinally to determine whether "
                f"their proportion is growing, which would indicate shifting demographic patterns.",
                "Cross-reference age group data with performance outcomes (Grade column) to "
                "determine whether age at examination correlates with academic achievement.",
                "Investigate years with significant enrolment drops or spikes — these may "
                "indicate data quality issues or genuine policy-driven changes worth reporting.",
                "Expand this analysis to include state-level breakdown to identify regions "
                "with disproportionately high under-age or over-age candidate populations.",
                "Use this data to inform examination centre capacity planning, ensuring "
                "adequate facilities are available for the dominant age cohort in each region.",
            ],
        }

    elif analysis == "Generational Education Trends":
        if "Generation" not in df.columns:
            return _empty(
                f"Generational trends report. Total: **{fmt(total)}**. Filters: {filter_desc}."
            )

        gen_order = [
            "Silent Generation (1928–1945)",
            "Baby Boomers (1946–1964)",
            "Gen X (1965–1980)",
            "Millennials (1981–1996)",
            "Gen Z (1997–2012)",
            "Gen Alpha (2013–2025)",
        ]

        clean      = df[~df["Generation"].isin(["Unknown", None, "Other"])].copy()
        gen_totals = clean.groupby("Generation")["Count"].sum()
        gen_totals = gen_totals.reindex(
            [g for g in gen_order if g in gen_totals.index]
        ).dropna()

        if gen_totals.empty:
            return _empty(
                "No generational data found for the selected filters. "
                "Ensure DateOfBirth data is available for the selected exam years."
            )

        dominant_gen = gen_totals.idxmax()
        dominant_ct  = int(gen_totals.max())
        dominant_pct = round(dominant_ct / total * 100, 1)
        gen_count    = len(gen_totals)

        selected_years  = sorted([int(y) for y in filters.get("ExamYear", [])])
        selected_states = filters.get("State", [])
        yr_part = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )
        st_part = (
            f"states **{', '.join(selected_states)}**"
            if selected_states else "all states"
        )

        mean_per_yr = round(total / max(len(selected_years), 1))

        # ── Per generation key findings ───────────────────────────────────────
        gen_findings = []
        for gen in gen_order:
            if gen not in gen_totals.index:
                continue
            ct      = int(gen_totals[gen])
            pct_val = round(ct / total * 100, 1)
            gen_findings.append(
                f"**{gen}**: {fmt(ct)} unique candidates ({pct_val}% of total)."
            )

        # ── Per generation trend observations ─────────────────────────────────
        gen_obs = []
        for gen in gen_order:
            if gen not in gen_totals.index:
                continue
            gen_yr = (
                clean[clean["Generation"] == gen]
                .groupby("ExamYear")["Count"].sum().sort_index()
            )
            ct      = int(gen_totals[gen])
            pct_val = round(ct / total * 100, 1)
            if len(gen_yr) >= 2:
                first_yr   = int(gen_yr.index[0])
                last_yr    = int(gen_yr.index[-1])
                first_ct   = int(gen_yr.iloc[0])
                last_ct    = int(gen_yr.iloc[-1])
                peak_yr    = int(gen_yr.idxmax())
                peak_ct    = int(gen_yr.max())
                direction  = "grew" if last_ct > first_ct else "declined"
                change_amt = abs(last_ct - first_ct)
                change_pct = round(change_amt / first_ct * 100, 1) if first_ct > 0 else 0
                gen_obs.append(
                    f"**{gen}** — participation {direction} by {change_pct}% "
                    f"from {fmt(first_ct)} ({first_yr}) to {fmt(last_ct)} ({last_yr}), "
                    f"peaking in **{peak_yr}** with {fmt(peak_ct)} candidates."
                )
            else:
                gen_obs.append(
                    f"**{gen}** — {fmt(ct)} candidates ({pct_val}%) across "
                    f"the selected period."
                )

        # ── Dominant generation year-on-year trend ────────────────────────────
        dom_yr = (
            clean[clean["Generation"] == dominant_gen]
            .groupby("ExamYear")["Count"].sum().sort_index()
        )
        trend_str = ""
        peak_yr   = None
        if len(dom_yr) >= 2:
            first_yr   = int(dom_yr.index[0])
            last_yr    = int(dom_yr.index[-1])
            first_ct   = int(dom_yr.iloc[0])
            last_ct    = int(dom_yr.iloc[-1])
            peak_yr    = int(dom_yr.idxmax())
            peak_yr_ct = int(dom_yr.max())
            direction  = "grown" if last_ct > first_ct else "declined"
            change_pct = round(
                abs(last_ct - first_ct) / first_ct * 100, 1
            ) if first_ct > 0 else 0
            trend_str = (
                f"Participation by **{dominant_gen}** has {direction} by "
                f"**{change_pct}%** — from {fmt(first_ct)} in {first_yr} "
                f"to {fmt(last_ct)} in {last_yr}, peaking in "
                f"**{peak_yr}** with {fmt(peak_yr_ct)} candidates."
            )

        # ── Generational shift observation ────────────────────────────────────
        years_available = sorted(clean["ExamYear"].unique())
        if len(years_available) >= 2:
            first_yr_dom = (
                clean[clean["ExamYear"] == years_available[0]]
                .groupby("Generation")["Count"].sum().idxmax()
            )
            last_yr_dom = (
                clean[clean["ExamYear"] == years_available[-1]]
                .groupby("Generation")["Count"].sum().idxmax()
            )
            if first_yr_dom != last_yr_dom:
                shift_obs = (
                    f"A clear generational shift is visible — in **{years_available[0]}**, "
                    f"**{first_yr_dom}** candidates were most prevalent. "
                    f"By **{years_available[-1]}**, **{last_yr_dom}** candidates "
                    f"had become dominant, confirming a cohort transition in the "
                    f"examination population over the selected period."
                )
            else:
                shift_obs = (
                    f"**{first_yr_dom}** candidates have consistently dominated "
                    f"across all selected exam years from "
                    f"**{years_available[0]}** to **{years_available[-1]}**."
                )
        else:
            shift_obs = (
                f"**{dominant_gen}** is the dominant generation for the "
                f"selected exam year."
            )

        return {
            "summary": (
                f"This report analyses examination participation patterns across "
                f"**{gen_count}** birth generation{'s' if gen_count > 1 else ''} "
                f"for {yr_part} and {st_part}. "
                f"A total of **{fmt(total)}** unique candidates were analysed, "
                f"averaging **{fmt(mean_per_yr)}** candidates per exam year. "
                f"Generations are classified by birth year using standard demographic "
                f"cohort definitions — from the Silent Generation (born 1928–1945) "
                f"through to Generation Alpha (born 2013–2025). "
                f"The dominant generation is **{dominant_gen}**, accounting for "
                f"**{dominant_pct}%** of all candidates. "
                f"This analysis reveals how the examination population has evolved "
                f"generationally, reflecting broader demographic and educational "
                f"trends across Nigeria over multiple decades."
            ),
            "key_findings": (
                [
                    f"Total unique candidates across all generations: **{fmt(total)}**.",
                    f"Generations represented: **{gen_count}** distinct cohorts.",
                    f"Average unique candidates per exam year: **{fmt(mean_per_yr)}**.",
                    f"Dominant generation: **{dominant_gen}** — "
                    f"{fmt(dominant_ct)} candidates ({dominant_pct}%).",
                ]
                + gen_findings
                + ([trend_str] if trend_str else [])
            ),
            "observations": (
                gen_obs
                + [
                    shift_obs,
                    "The **Silent Generation (1928–1945)** appearing in the dataset "
                    "represents candidates aged 48 or older during the earliest exam "
                    "years. Their presence indicates mature adult learners pursuing "
                    "formal qualifications — a small but meaningful cohort reflecting "
                    "lifelong learning behaviour in Nigeria.",
                    "**Baby Boomers (1946–1964)** would have been the primary exam "
                    "cohort through the 1960s–1980s. Their presence here indicates "
                    "re-sitting, mature enrolment, or delayed qualification pursuit "
                    "in the years covered by this dataset.",
                    "**Gen X (1965–1980)** candidates form the transitional generation "
                    "— representing the core examination cohort through the 1980s–2000s "
                    "and gradually giving way to Millennials as the dominant group.",
                    "**Millennials (1981–1996)** became the backbone of the mid-period "
                    "examination population, entering the system from the late 1990s "
                    "onward and remaining dominant through most of the 2010s.",
                    "**Gen Z (1997–2012)** are the current and growing primary cohort — "
                    "their increasing numbers in recent years reflect Nigeria's youth "
                    "population bulge reaching examination age.",
                    "**Gen Alpha (2013–2025)** appearing in the dataset should be "
                    "investigated carefully — candidates born after 2013 would be "
                    "under 12 years old even by 2025, making their presence "
                    "statistically anomalous and likely indicative of data entry errors "
                    "in the DateOfBirth column.",
                ]
            ),
            "implications": [
                "The generational shift from Baby Boomers through Gen X, Millennials, "
                "and now Gen Z as the dominant cohort mirrors Nigeria's population "
                "growth trajectory and the decades-long expansion of secondary "
                "education access.",
                "The growing size of the Gen Z cohort has direct implications for "
                "examination infrastructure — more examination centres, invigilators, "
                "question papers, and digital capacity will be required in coming years "
                "as this cohort's numbers continue to rise.",
                "The presence of Gen Alpha candidates warrants immediate data quality "
                "review — candidates born after 2013 would be biologically too young "
                "to sit secondary examinations. These records should be flagged before "
                "inclusion in official statistics.",
                "Declining Baby Boomer and Gen X participation in recent years is "
                "structurally expected as these cohorts age beyond typical examination "
                "demographics. A policy question exists around whether adult education "
                "pathways adequately serve older returning candidates.",
                "Cross-generational performance comparison — layering Grade data onto "
                "this analysis — could reveal whether educational quality and attainment "
                "rates have improved across successive generations, a critical metric "
                "for national education policy evaluation.",
            ],
            "recommendations": [
                "Flag and investigate all Gen Alpha records for potential DateOfBirth "
                "data entry errors. These candidates should be verified before inclusion "
                "in any official examination statistics or policy documents.",
                "Track the Gen Z cohort longitudinally across successive exam years to "
                "model future examination demand and plan centre capacity expansions "
                "accordingly — particularly in high-growth states.",
                "Examine states where Silent Generation or Baby Boomer candidates "
                "represent an unusually high share — this may point to strong adult "
                "education programmes or regions where school-age completion "
                "historically lagged behind the national average.",
                "Cross-reference generational data with Grade outcomes to assess whether "
                "attainment rates have improved across successive generations, providing "
                "evidence for curriculum and teaching quality policy decisions.",
                "Use generational participation trends to inform long-term examination "
                "centre expansion planning, particularly prioritising states and regions "
                "with the highest Gen Z population growth rates.",
                "Explore the relationship between generation and exam type "
                "(School Exams vs Private Examination) to understand whether different "
                "generations access the examination system through different pathways — "
                "this could inform targeted outreach and accessibility strategies.",
            ],
        }

    elif analysis == "Age-Appropriate Enrollment Assessment":
        if not has("AgeGroup"):
            return f"Enrollment assessment. Total: **{fmt(total)}**. Filters: {filter_desc}."
        ag = df.groupby("AgeGroup")["Count"].sum().sort_values(ascending=False)
        top = ag.index[0]
        return (
            f"Age-appropriate enrollment. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. "
            f"Peak enrollment age group: **{top}**."
        )

    elif analysis == "Cohort Tracking Across Years":
        if not has("computed_age"):
            return f"Cohort tracking. Total: **{fmt(total)}**. Filters: {filter_desc}."
        age_min = filters.get("_age_min", 12)
        age_max = filters.get("_age_max", 25)
        return (
            f"Cohort tracking across years (ages {age_min}–{age_max}). "
            f"Filters: {filter_desc}. Total: **{fmt(total)}** records."
        )

    # ── GENDER REPORTS ────────────────────────────────────────────────────────
    elif analysis in ("Male-to-Female Ratio Overview", "Gender Balance by Exam Year",
                      "Gender Distribution by State & Centre", "Gender Equity Trends Over Time",
                      "Registration by Gender", "Gender Growth Rate Comparison"):
        if not has("Sex"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        male_ct   = int(df[df["Sex"].str.lower() == "male"]["Count"].sum())   if has("Sex") else 0
        female_ct = int(df[df["Sex"].str.lower() == "female"]["Count"].sum()) if has("Sex") else 0
        bias      = "Male" if male_ct > female_ct else "Female" if female_ct > male_ct else "Balanced"
        top_year  = df.groupby("ExamYear")["Count"].sum().idxmax() if has("ExamYear") else "N/A"
        return (
            f"{analysis}. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. "
            f"Male: **{fmt(male_ct)}** ({pct(male_ct, total)}). "
            f"Female: **{fmt(female_ct)}** ({pct(female_ct, total)}). "
            f"Gender balance: **{bias}**."
            + (f" Peak year: **{top_year}**." if top_year != "N/A" else "")
        )

    # ── DISABILITY REPORTS ────────────────────────────────────────────────────
    elif analysis in ("Disability Inclusion Rate", "Disability Trends by Exam Year",
                      "Disability by Gender & Age Group", "Regional Disability Patterns",
                      "Registration by Disability Status"):
        if not has("Disability"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        dis = df.groupby("Disability")["Count"].sum().sort_values(ascending=False)
        top = dis.index[0]
        top_ct = int(dis.iloc[0])
        return (
            f"{analysis}. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. "
            f"Most recorded disability status: **{top}** — {fmt(top_ct)} ({pct(top_ct, total)})."
        )

    # ── STATE / GEOGRAPHIC REPORTS ────────────────────────────────────────────
    elif analysis == "Centre Count by State & Region":
        if (
            "State" not in df.columns
            or "Count" not in df.columns
            or df.empty
        ):
            return _empty(
                "No examination-centre information was available "
                "for the selected geographic filters."
            )

        selected_states = filters.get("State", []) or []
        data = df.copy()

        if "Region" not in data.columns:
            data["Region"] = data["State"].apply(state_to_zone)

        # ── State scope ───────────────────────────────────────────────────
        if selected_states:
            state_scope = data[data["State"].isin(selected_states)].copy()
        else:
            state_scope = data.copy()

        # ── Region scope — derived automatically from selected states ─────
        region_scope_states = state_scope.copy()
        region_totals = (
            region_scope_states
            .groupby("Region", as_index=False)["Count"]
            .sum()
            .sort_values("Count", ascending=False)
        )
        region_totals = region_totals[region_totals["Region"] != "Other"]

        total_centres  = int(data["Count"].sum())
        states_covered = int(data["State"].nunique())

        key_findings    = []
        observations    = []
        implications    = []
        recommendations = []

        # ── State analysis ────────────────────────────────────────────────
        if not state_scope.empty:
            state_rank = (
                state_scope
                .groupby("State", as_index=False)["Count"]
                .sum()
                .sort_values("Count", ascending=False)
            )
            state_total  = int(state_rank["Count"].sum())
            state_count  = int(state_rank["State"].nunique())
            top_state    = state_rank.iloc[0]
            bottom_state = state_rank.iloc[-1]
            avg_state    = round(state_total / state_count, 1) if state_count else 0
            median_state = round(float(state_rank["Count"].median()), 1) if state_count else 0
            top_share    = round(int(top_state["Count"]) / state_total * 100, 1) if state_total else 0

            key_findings.extend([
                f"The selected state scope contains **{fmt(state_total)} distinct "
                f"examination centres** across **{state_count} "
                f"state{'s' if state_count != 1 else ''}**.",
                f"**{top_state['State']}** has the highest centre count with "
                f"**{fmt(int(top_state['Count']))} centres**, representing "
                f"**{top_share}%** of centres within the selected state scope.",
                f"**{bottom_state['State']}** has the lowest centre count among "
                f"the selected states with "
                f"**{fmt(int(bottom_state['Count']))} centres**.",
                f"The average number of centres per selected state is "
                f"**{avg_state:,.1f}**, while the median is **{median_state:,.1f}**.",
            ])

            for _, row in state_rank.head(10).iterrows():
                share = round(
                    int(row["Count"]) / state_total * 100, 1
                ) if state_total else 0
                observations.append(
                    f"**{row['State']}**: {fmt(int(row['Count']))} centres "
                    f"({share}% of the selected-state total)."
                )

            spread = int(top_state["Count"]) - int(bottom_state["Count"])
            observations.append(
                f"The difference between the highest- and lowest-count selected "
                f"states is **{fmt(spread)} centres**, indicating the degree of "
                f"geographic variation in examination-centre availability."
            )

        # ── Region analysis ───────────────────────────────────────────────
        if not region_totals.empty:
            region_total     = int(region_totals["Count"].sum())
            region_count     = int(region_totals["Region"].nunique())
            top_region       = region_totals.iloc[0]
            bottom_region    = region_totals.iloc[-1]
            avg_region       = round(region_total / region_count, 1) if region_count else 0
            top_region_share = round(
                int(top_region["Count"]) / region_total * 100, 1
            ) if region_total else 0

            key_findings.extend([
                f"The selected scope spans **{region_count} geopolitical "
                f"zone{'s' if region_count != 1 else ''}** when states are "
                f"grouped by Nigeria's six geopolitical regions.",
                f"**{top_region['Region']}** has the largest centre network with "
                f"**{fmt(int(top_region['Count']))} centres** "
                f"({top_region_share}% of the regional total).",
                f"**{bottom_region['Region']}** records the smallest centre network "
                f"with **{fmt(int(bottom_region['Count']))} centres**.",
                f"The selected zones average approximately "
                f"**{avg_region:,.1f} centres per geopolitical zone**.",
            ])

            for _, row in region_totals.iterrows():
                share = round(
                    int(row["Count"]) / region_total * 100, 1
                ) if region_total else 0
                observations.append(
                    f"**{row['Region']}** contains "
                    f"**{fmt(int(row['Count']))} centres**, "
                    f"representing **{share}%** of centres across the "
                    f"selected scope."
                )

            for region in region_totals["Region"].tolist():
                reg_states = (
                    region_scope_states[
                        region_scope_states["Region"] == region
                    ].sort_values("Count", ascending=False)
                )
                if reg_states.empty:
                    continue
                top_reg_state = reg_states.iloc[0]
                low_reg_state = reg_states.iloc[-1]
                observations.append(
                    f"Within **{region}**, **{top_reg_state['State']}** has the "
                    f"highest centre count ({fmt(int(top_reg_state['Count']))}), "
                    f"while **{low_reg_state['State']}** has the lowest "
                    f"({fmt(int(low_reg_state['Count']))})."
                )

        # ── Implications ──────────────────────────────────────────────────
        implications.extend([
            "Large differences in centre counts indicate that examination "
            "infrastructure is not evenly distributed geographically. States "
            "or regions with larger centre networks have more physical "
            "examination locations in the dataset.",
            "Centre count alone measures infrastructure presence, not whether "
            "it is adequate for candidate demand. A state with fewer centres "
            "may still be adequately served if its candidate population is small.",
            "Having many centres does not automatically indicate sufficient "
            "capacity — candidate volumes may be heavily concentrated "
            "within those centres.",
        ])

        # ── Recommendations ───────────────────────────────────────────────
        recommendations.extend([
            "Use the **Candidate Load per Centre** report alongside this report "
            "to determine how many candidates each examination centre is serving.",
            "Use **Underserved Area Identification** to compare candidate demand "
            "against centre availability before flagging any state as "
            "infrastructure-deficient.",
            "Review states with substantially lower centre counts relative to "
            "comparable states and determine whether additional examination "
            "locations may be required.",
            "Track centre distribution periodically to determine whether "
            "examination infrastructure expansion is keeping pace with changes "
            "in candidate participation.",
        ])

        # ── Summary ───────────────────────────────────────────────────────
        state_text = (
            f"**{len(selected_states)} selected "
            f"state{'s' if len(selected_states) != 1 else ''}**"
            if selected_states
            else "all available states"
        )

        return {
            "summary": (
                f"This report examines the geographic distribution of distinct "
                f"examination centres across {state_text}, grouped by Nigeria's "
                f"six geopolitical zones for regional comparison. "
                f"The dataset covers **{fmt(total_centres)} centres across "
                f"{states_covered} states** in the selected scope. "
                f"The analysis reveals where examination infrastructure is "
                f"concentrated and where centre availability is comparatively lower."
            ),
            "key_findings":    key_findings,
            "observations":    observations,
            "implications":    implications,
            "recommendations": recommendations,
        }

    elif analysis == "Candidate Load per Centre":
        if "centre" not in df.columns or "CandidateLoad" not in df.columns:
            return _empty(
                f"Candidate Load per Centre. Total: **{fmt(total)}**. "
                f"Filters: {filter_desc}."
            )

        top_n          = int(filters.get("TopN", 10))
        direction      = filters.get("LoadDirection", "Highest")
        selected_years = filters.get("ExamYear", [])
        selected_states = filters.get("State", [])
        is_both        = "Both" in direction
        is_highest     = "Lowest" not in direction or is_both

        yr_part = (
            f"exam years **{', '.join(str(y) for y in sorted(selected_years))}**"
            if selected_years else "all available exam years"
        )
        st_part = (
            f"states **{', '.join(selected_states)}**"
            if selected_states else "all states"
        )

        direction_label = (
            "Highest & Lowest" if is_both
            else "Highest" if is_highest
            else "Lowest"
        )

        # Split df if Both
        if is_both and "RankGroup" in df.columns:
            top_df = df[df["RankGroup"].str.startswith("Highest")]
            bot_df = df[df["RankGroup"].str.startswith("Lowest")]
        elif is_highest:
            top_df = df.sort_values("CandidateLoad", ascending=False).head(top_n)
            bot_df = pd.DataFrame()
        else:
            top_df = pd.DataFrame()
            bot_df = df.sort_values("CandidateLoad", ascending=True).head(top_n)

        key_findings    = []
        observations    = []
        implications    = []
        recommendations = []

        def _analyse_group(gdf: pd.DataFrame, group_label: str) -> None:
            if gdf.empty:
                return
            total_load   = int(gdf["CandidateLoad"].sum())
            avg_load     = round(float(gdf["CandidateLoad"].mean()), 1)
            median_load  = round(float(gdf["CandidateLoad"].median()), 1)
            max_load     = int(gdf["CandidateLoad"].max())
            min_load     = int(gdf["CandidateLoad"].min())
            spread       = max_load - min_load
            top_row      = gdf.loc[gdf["CandidateLoad"].idxmax()]
            bot_row      = gdf.loc[gdf["CandidateLoad"].idxmin()]
            states_rep   = gdf["State"].nunique()

            key_findings.extend([
                f"**{group_label} {top_n} centres** collectively served "
                f"**{fmt(total_load)}** unique candidates.",
                f"Average candidate load ({group_label.lower()} group): "
                f"**{fmt(int(avg_load))}** | Median: **{fmt(int(median_load))}**.",
                f"Load spread within {group_label.lower()} group: "
                f"**{fmt(spread)} candidates** "
                f"(from {fmt(min_load)} to {fmt(max_load)}).",
                f"**{top_row['centre']}** ({top_row['State']}) — "
                f"highest in {group_label.lower()} group: "
                f"**{fmt(int(top_row['CandidateLoad']))}** candidates.",
                f"States represented in {group_label.lower()} ranking: "
                f"**{states_rep}**.",
            ])

            for rank, (_, row) in enumerate(
                gdf.sort_values(
                    "CandidateLoad",
                    ascending=(group_label == "Lowest")
                ).iterrows(), 1
            ):
                share = round(
                    int(row["CandidateLoad"]) / total_load * 100, 1
                ) if total_load else 0
                observations.append(
                    f"**#{rank} [{group_label}] — {row['centre']}** "
                    f"({row['State']}): "
                    f"{fmt(int(row['CandidateLoad']))} unique candidates "
                    f"({share}% of the {group_label.lower()} group total)."
                )

            state_counts = gdf["State"].value_counts()
            for state, count in state_counts.items():
                observations.append(
                    f"**{state}** has **{count}** centre"
                    f"{'s' if count > 1 else ''} in the "
                    f"{group_label.lower()} {top_n} ranking."
                )

            if group_label == "Highest":
                implications.extend([
                    f"The highest-load centres collectively carry "
                    f"**{fmt(total_load)}** candidates across just {top_n} "
                    f"locations — a significant concentration of examination "
                    f"demand that may indicate infrastructure stress.",
                    f"**{top_row['centre']}** ({top_row['State']}) with "
                    f"**{fmt(int(top_row['CandidateLoad']))}** candidates "
                    f"represents the most congested centre in the scope. "
                    f"Hall capacity must be verified to ensure safe operations.",
                    "States with multiple centres in the highest-load ranking "
                    "may face system-wide demand pressure rather than "
                    "isolated centre congestion.",
                ])
                recommendations.extend([
                    f"Prioritise capacity assessment at "
                    f"**{top_row['centre']}** ({top_row['State']}) given "
                    f"its position as the highest-load centre.",
                    "Cross-reference these centres with hall capacity data "
                    "to confirm candidate load is within safe operating limits.",
                    "Consider redistributing candidates from the "
                    "highest-load centres to nearby underutilised locations "
                    "identified in the Lowest Load report.",
                    "Track whether these centres are consistently "
                    "high-load across multiple years — a persistent pattern "
                    "requires structural intervention.",
                ])
            else:
                implications.extend([
                    f"The lowest-load centres collectively served only "
                    f"**{fmt(total_load)}** candidates across {top_n} "
                    f"locations, suggesting significant underutilisation of "
                    f"examination infrastructure at these sites.",
                    f"**{bot_row['centre']}** ({bot_row['State']}) with only "
                    f"**{fmt(int(bot_row['CandidateLoad']))}** candidates "
                    f"is the most underutilised centre in the scope.",
                    "Low candidate load does not automatically indicate a "
                    "centre should be closed — geographic remoteness and "
                    "community access considerations must be weighed carefully.",
                ])
                recommendations.extend([
                    "Before consolidating or closing low-load centres, "
                    "investigate geographic context and accessibility — "
                    "these centres may serve critical roles in remote areas.",
                    f"Assess whether **{bot_row['centre']}** and other "
                    "low-load centres could absorb redistributed candidates "
                    "from the highest-load locations.",
                    "Compare low-load centres against the Highest Load "
                    "report to identify redistribution opportunities.",
                    "Investigate whether consistently low-load centres "
                    "reflect genuine low demand or a registration barrier "
                    "preventing candidates from accessing those centres.",
                ])

        _analyse_group(top_df, "Highest")
        _analyse_group(bot_df, "Lowest")

        return {
            "summary": (
                f"This report analyses candidate load distribution across "
                f"examination centres for {yr_part} and {st_part}. "
                f"Candidate load is measured as the count of unique candidates "
                f"(distinct ExamNum per ExamYear) registered at each centre. "
                f"The report focuses on the **{direction_label} {top_n} centres** "
                f"by load — providing a targeted view of the most congested "
                f"and/or most underutilised examination infrastructure within "
                f"the selected scope. This analysis supports evidence-based "
                f"decisions on centre capacity, candidate redistribution, "
                f"and infrastructure investment."
            ),
            "key_findings":    key_findings,
            "observations":    observations,
            "implications":    implications,
            "recommendations": recommendations,
        }

    elif any(x in analysis for x in ["State", "Regional", "Geographic",
                                      "Centre Count", "Candidate Load",
                                      "Underserved", "Accessibility"]):
    
        if has("State"):
            st_agg = df.groupby("State")["Count"].sum().sort_values(ascending=False)
            top_st = st_agg.index[0]
            top_ct = int(st_agg.iloc[0])
            bot_st = st_agg.index[-1]
            bot_ct = int(st_agg.iloc[-1])
            return (
                f"{analysis}. Filters: {filter_desc}. "
                f"Total: **{fmt(total)}** records across **{st_agg.nunique()}** states. "
                f"Highest: **{top_st}** — {fmt(top_ct)} ({pct(top_ct, total)}). "
                f"Lowest: **{bot_st}** — {fmt(bot_ct)}."
            )
        return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."

    # ── REGISTRATION / ENROLLMENT REPORTS ────────────────────────────────────
    elif analysis == "State Registration Trends":
        if "ExamYear" not in df.columns or "State" not in df.columns:
            return _empty(
                f"State Registration Trends. Total: **{fmt(total)}**. "
                f"Filters: {filter_desc}."
            )

        selected_years  = sorted([int(y) for y in filters.get("ExamYear", [])])
        selected_states = filters.get("State", [])

        yr_part = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )
        st_part = (
            f"states **{', '.join(selected_states)}**"
            if selected_states else "all states"
        )

        # ── Per state analysis ────────────────────────────────────────────
        state_totals = df.groupby("State")["Count"].sum().sort_values(ascending=False)
        top_state    = state_totals.index[0]
        top_state_ct = int(state_totals.iloc[0])
        bot_state    = state_totals.index[-1]
        bot_state_ct = int(state_totals.iloc[-1])
        avg_state    = round(float(state_totals.mean()), 1)
        spread       = top_state_ct - bot_state_ct
        states_count = int(state_totals.nunique())

        # ── Year-on-year trend per state ──────────────────────────────────
        yr_totals    = df.groupby("ExamYear")["Count"].sum().sort_index()
        years_list   = sorted(yr_totals.index.astype(int).tolist())
        overall_dir  = "increased" if yr_totals.iloc[-1] > yr_totals.iloc[0] else "decreased"
        peak_yr      = int(yr_totals.idxmax())
        peak_yr_ct   = int(yr_totals.max())
        trough_yr    = int(yr_totals.idxmin())
        trough_yr_ct = int(yr_totals.min())

        # ── Per state trend observations ──────────────────────────────────
        state_obs = []
        for state in state_totals.index:
            s_yr = df[df["State"] == state].groupby("ExamYear")["Count"].sum().sort_index()
            s_total = int(s_yr.sum())
            share   = round(s_total / total * 100, 1) if total else 0
            if len(s_yr) >= 2:
                s_dir  = "grew" if s_yr.iloc[-1] > s_yr.iloc[0] else "declined"
                s_chg  = round(
                    abs(s_yr.iloc[-1] - s_yr.iloc[0]) / s_yr.iloc[0] * 100, 1
                ) if s_yr.iloc[0] > 0 else 0
                state_obs.append(
                    f"**{state}**: {fmt(s_total)} total candidates "
                    f"({share}% of scope total) — registration {s_dir} "
                    f"by {s_chg}% from "
                    f"{int(s_yr.index[0])} to {int(s_yr.index[-1])}."
                )
            else:
                state_obs.append(
                    f"**{state}**: {fmt(s_total)} total candidates "
                    f"({share}% of scope total)."
                )

        yr_range = f"{years_list[0]}–{years_list[-1]}" if len(years_list) > 1 else str(years_list[0]) if years_list else "N/A"

        return {
            "summary": (
                f"This report tracks candidate registration trends across "
                f"**{states_count} state{'s' if states_count != 1 else ''}** "
                f"for {yr_part} and {st_part}. "
                f"A total of **{fmt(total)}** unique candidates were registered "
                f"across the selected scope. "
                f"Overall registration {overall_dir} between "
                f"**{years_list[0] if years_list else 'N/A'}** and "
                f"**{years_list[-1] if years_list else 'N/A'}**, "
                f"peaking in **{peak_yr}** with **{fmt(peak_yr_ct)}** candidates. "
                f"This report helps identify which states are growing, declining, "
                f"or stagnating in candidate registration over time."
            ),
            "key_findings": [
                f"Total unique candidates across all selected states and years: "
                f"**{fmt(total)}**.",
                f"States analysed: **{states_count}** over **{yr_range}**.",
                f"Highest registration state: **{top_state}** — "
                f"{fmt(top_state_ct)} candidates "
                f"({round(top_state_ct/total*100,1)}% of total).",
                f"Lowest registration state: **{bot_state}** — "
                f"{fmt(bot_state_ct)} candidates "
                f"({round(bot_state_ct/total*100,1)}% of total).",
                f"Average registration per state across the period: "
                f"**{fmt(int(avg_state))}** candidates.",
                f"Registration spread between highest and lowest state: "
                f"**{fmt(spread)} candidates**.",
                f"Peak registration year overall: **{peak_yr}** — "
                f"{fmt(peak_yr_ct)} candidates.",
                f"Lowest registration year overall: **{trough_yr}** — "
                f"{fmt(trough_yr_ct)} candidates.",
            ],
            "observations": state_obs + [
                f"Overall candidate registration across the selected states "
                f"**{overall_dir}** between {years_list[0] if years_list else 'N/A'} "
                f"and {years_list[-1] if years_list else 'N/A'}.",
                f"The gap of **{fmt(spread)} candidates** between **{top_state}** "
                f"and **{bot_state}** indicates significant geographic inequality "
                f"in examination participation across the selected states.",
            ],
            "implications": [
                f"States showing consistent registration growth — such as "
                f"**{top_state}** — may face increasing pressure on examination "
                f"centre capacity in coming years.",
                f"States with declining registration trends may indicate "
                f"demographic shifts, migration, school access challenges, "
                f"or data quality issues worth investigating.",
                f"The peak year of **{peak_yr}** represents the highest demand "
                f"point in the selected scope — understanding what drove this "
                f"peak can inform future planning.",
                "Large differences in registration volumes between states "
                "reflect broader inequalities in educational access and "
                "infrastructure that may require targeted policy intervention.",
            ],
            "recommendations": [
                f"Investigate states with declining registration trends to "
                f"determine whether the cause is demographic, infrastructural, "
                f"or administrative — particularly **{bot_state}** which records "
                f"the lowest total across the selected period.",
                f"Use the **Centre Count by State & Region** and "
                f"**Candidate Load per Centre** reports alongside this one to "
                f"determine whether high-registration states like **{top_state}** "
                f"have adequate examination infrastructure.",
                "Track states showing sudden spikes or drops in a single year — "
                "these anomalies may indicate data quality issues or significant "
                "policy changes that affected registration.",
                "Cross-reference registration trends with performance data "
                "(Grade outcomes) to assess whether growth in registration "
                "volume is accompanied by maintained or improved pass rates.",
                "Use multi-year trend data to build registration forecasts "
                "for the next 3–5 years, supporting long-term centre capacity "
                "and resource planning.",
            ],
        }

    elif analysis == "State Growth Rate Analysis":
        if "State" not in df.columns or "ExamYear" not in df.columns:
            return _empty(
                f"State Registration Growth Rate. Total: **{fmt(total)}**. "
                f"Filters: {filter_desc}."
            )

        selected_years  = sorted([int(y) for y in filters.get("ExamYear", [])])
        selected_states = filters.get("State", [])

        yr_part = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )
        st_part = (
            f"states **{', '.join(selected_states)}**"
            if selected_states else "all states"
        )

        # ── Compute growth rates ──────────────────────────────────────────
        df2 = df.copy()
        df2["ExamYear"] = df2["ExamYear"].astype(int)
        df2 = df2.sort_values(["State", "ExamYear"])
        df2["PrevCount"] = df2.groupby("State")["Count"].shift(1)
        df2["GrowthRate"] = (
            (df2["Count"] - df2["PrevCount"])
            / df2["PrevCount"].replace(0, float("nan"))
            * 100
        ).round(2)
        df2 = df2.dropna(subset=["GrowthRate"])

        if df2.empty:
            return _empty(
                "Growth rate could not be calculated — at least two "
                "consecutive exam years are required per state. "
                "Please select a broader year range."
            )

        # ── Overall growth rate ───────────────────────────────────────────
        overall_growth = round(float(df2["GrowthRate"].mean()), 2)

        # ── Fastest growing state ─────────────────────────────────────────
        state_avg_growth = df2.groupby("State")["GrowthRate"].mean().sort_values(ascending=False)
        fastest_state    = state_avg_growth.index[0]
        fastest_rate     = round(float(state_avg_growth.iloc[0]), 2)

        # ── Highest single-year peak ──────────────────────────────────────
        peak_idx         = df2["GrowthRate"].idxmax()
        peak_state       = df2.loc[peak_idx, "State"]
        peak_yr          = int(df2.loc[peak_idx, "ExamYear"])
        peak_rate        = round(float(df2.loc[peak_idx, "GrowthRate"]), 2)

        # ── Largest decline ───────────────────────────────────────────────
        decline_avg      = state_avg_growth.sort_values(ascending=True)
        decline_state    = decline_avg.index[0]
        decline_rate     = round(float(decline_avg.iloc[0]), 2)

        # ── Growing vs declining states ───────────────────────────────────
        growing_states  = state_avg_growth[state_avg_growth > 0].index.tolist()
        declining_states = state_avg_growth[state_avg_growth < 0].index.tolist()
        stable_states   = state_avg_growth[state_avg_growth == 0].index.tolist()

        # ── Per state observations ────────────────────────────────────────
        state_obs = []
        for state, avg_rate in state_avg_growth.items():
            state_yrs = df2[df2["State"] == state].sort_values("ExamYear")
            yr_range  = (
                f"{int(state_yrs['ExamYear'].min())}–"
                f"{int(state_yrs['ExamYear'].max())}"
                if len(state_yrs) > 1
                else str(int(state_yrs["ExamYear"].iloc[0]))
            )
            direction = "grew" if avg_rate > 0 else "declined" if avg_rate < 0 else "remained stable"
            state_obs.append(
                f"**{state}** averaged **{avg_rate:+.1f}%** annual growth "
                f"over {yr_range} — registration {direction} on average."
            )

        # ── Year-on-year observations ─────────────────────────────────────
        yr_obs = []
        for yr in sorted(df2["ExamYear"].unique()):
            yr_df     = df2[df2["ExamYear"] == yr]
            yr_avg    = round(float(yr_df["GrowthRate"].mean()), 1)
            yr_top    = yr_df.loc[yr_df["GrowthRate"].idxmax(), "State"]
            yr_top_r  = round(float(yr_df["GrowthRate"].max()), 1)
            yr_bot    = yr_df.loc[yr_df["GrowthRate"].idxmin(), "State"]
            yr_bot_r  = round(float(yr_df["GrowthRate"].min()), 1)
            yr_obs.append(
                f"**{yr}** — Average growth across selected states: "
                f"**{yr_avg:+.1f}%**. "
                f"Fastest: **{yr_top}** ({yr_top_r:+.1f}%). "
                f"Slowest: **{yr_bot}** ({yr_bot_r:+.1f}%)."
            )

        return {
            "summary": (
                f"This report analyses year-on-year candidate registration "
                f"growth rates across **{len(selected_states or state_avg_growth.index)} "
                f"states** for {yr_part} and {st_part}. "
                f"Growth rate is calculated as the percentage change in unique "
                f"candidate registrations from one exam year to the next. "
                f"The overall average growth rate across the selected scope is "
                f"**{overall_growth:+.2f}%**. "
                f"**{fastest_state}** is the fastest-growing state with an "
                f"average annual growth of **{fastest_rate:+.1f}%**, while "
                f"**{decline_state}** recorded the largest average decline "
                f"at **{decline_rate:+.1f}%** per year."
            ),
            "key_findings": [
                f"Overall average growth rate across selected scope: "
                f"**{overall_growth:+.2f}%**.",
                f"Fastest growing state (average): **{fastest_state}** — "
                f"{fastest_rate:+.1f}% per year.",
                f"Highest single-year growth: **{peak_state}** in **{peak_yr}** "
                f"— {peak_rate:+.1f}%.",
                f"State with largest average decline: **{decline_state}** — "
                f"{decline_rate:+.1f}% per year.",
                f"States with positive average growth: "
                f"**{len(growing_states)}** "
                f"({', '.join(growing_states[:5])}"
                f"{'...' if len(growing_states) > 5 else ''}).",
                f"States with negative average growth (declining): "
                f"**{len(declining_states)}** "
                f"({', '.join(declining_states[:5]) if declining_states else 'None'}"
                f"{'...' if len(declining_states) > 5 else ''}).",
            ],
            "observations": state_obs + yr_obs,
            "implications": [
                f"**{fastest_state}'s** consistent growth suggests expanding "
                f"school enrolment, population growth, or improved examination "
                f"access — factors worth studying and replicating elsewhere.",
                f"**{decline_state}'s** declining registration is a policy "
                f"concern. Declining candidate volumes may indicate school "
                f"closures, migration, or growing barriers to examination access "
                f"in that state.",
                f"An overall average growth of **{overall_growth:+.2f}%** "
                + (
                    "suggests the examination system is expanding its reach "
                    "across the selected states."
                    if overall_growth > 0
                    else "suggests candidate registration is contracting "
                    "across the selected scope — this warrants investigation."
                ),
                "States showing volatile growth (large swings between years) "
                "may have data quality issues or be subject to irregular "
                "administrative factors affecting registration counts.",
                "The State × Year growth matrix (Chart 3) highlights which "
                "specific year-state combinations drove the overall trend — "
                "sudden spikes or drops in a single year deserve closer scrutiny.",
            ],
            "recommendations": [
                f"Prioritise policy investment in **{decline_state}** and "
                f"other declining states to reverse falling registration trends "
                f"before they become structural.",
                f"Study the factors behind **{fastest_state}'s** growth "
                f"— school density, centre availability, government programmes — "
                f"and assess whether those conditions can be replicated in "
                f"slower-growing states.",
                "Use the growth matrix to identify states with consistent "
                "multi-year decline rather than a single-year dip, as these "
                "represent the most urgent cases for intervention.",
                "Cross-reference growth rate data with Centre Count and "
                "Candidate Load reports to determine whether infrastructure "
                "expansion is keeping pace with registration growth in "
                "fast-growing states.",
                "Build a 3–5 year registration forecast using the growth "
                "rate trends from this report to support long-term examination "
                "centre capacity planning across all states.",
                "Investigate years where the overall growth rate turned "
                "negative — these may coincide with policy changes, economic "
                "disruptions, or external events that affected school attendance.",
            ],
        }

    elif analysis == "Registration Trends & Growth Rate":
        if "ExamYear" not in df.columns or "Count" not in df.columns:
            return _empty(
                f"Registration Trends & Growth Rate. "
                f"Total: **{fmt(total)}**. Filters: {filter_desc}."
            )

        df2 = df.copy()
        df2["ExamYear"]   = df2["ExamYear"].astype(int)
        df2 = df2.sort_values("ExamYear")
        df2["PrevCount"]  = df2["Count"].shift(1)
        df2["GrowthRate"] = (
            (df2["Count"] - df2["PrevCount"])
            / df2["PrevCount"].replace(0, float("nan"))
            * 100
        ).round(2)

        years        = df2["ExamYear"].tolist()
        yr_range     = f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])
        total_cands  = int(df2["Count"].sum())
        peak_row     = df2.loc[df2["Count"].idxmax()]
        peak_yr      = int(peak_row["ExamYear"])
        peak_ct      = int(peak_row["Count"])
        low_row      = df2.loc[df2["Count"].idxmin()]
        low_yr       = int(low_row["ExamYear"])
        low_ct       = int(low_row["Count"])
        latest_row   = df2.iloc[-1]
        latest_yr    = int(latest_row["ExamYear"])
        latest_g     = latest_row["GrowthRate"]

        df_growth    = df2.dropna(subset=["GrowthRate"])
        avg_growth   = round(float(df_growth["GrowthRate"].mean()), 2) if not df_growth.empty else 0
        positive_yrs = df_growth[df_growth["GrowthRate"] > 0]["ExamYear"].tolist()
        negative_yrs = df_growth[df_growth["GrowthRate"] < 0]["ExamYear"].tolist()
        peak_g_row   = df_growth.loc[df_growth["GrowthRate"].idxmax()] if not df_growth.empty else None
        low_g_row    = df_growth.loc[df_growth["GrowthRate"].idxmin()] if not df_growth.empty else None

        yr_obs = []
        for _, row in df2.iterrows():
            yr  = int(row["ExamYear"])
            ct  = int(row["Count"])
            g   = row["GrowthRate"]
            g_str = f"{g:+.1f}%" if pd.notna(g) else "first year (no prior)"
            yr_obs.append(
                f"**{yr}**: {fmt(ct)} unique candidates — "
                f"growth rate: {g_str}."
            )

        return {
            "summary": (
                f"This report tracks the total number of unique candidates "
                f"registered for examinations across **{yr_range}** "
                f"({len(years)} exam year{'s' if len(years) > 1 else ''}). "
                f"A total of **{fmt(total_cands)}** unique candidates were "
                f"registered across the selected period. "
                f"Registration peaked in **{peak_yr}** with "
                f"**{fmt(peak_ct)}** candidates and was lowest in "
                f"**{low_yr}** with **{fmt(low_ct)}**. "
                f"The average year-on-year growth rate over the period is "
                f"**{avg_growth:+.2f}%**."
            ),
            "key_findings": [
                f"Total unique candidates across **{yr_range}**: "
                f"**{fmt(total_cands)}**.",
                f"Highest registration year: **{peak_yr}** — "
                f"{fmt(peak_ct)} candidates.",
                f"Lowest registration year: **{low_yr}** — "
                f"{fmt(low_ct)} candidates.",
                f"Latest year growth rate (**{latest_yr}**): "
                f"**{f'{latest_g:+.1f}%' if pd.notna(latest_g) else 'N/A'}**.",
                f"Average annual growth rate: **{avg_growth:+.2f}%**.",
                f"Years with positive growth: **{len(positive_yrs)}** "
                f"({', '.join(str(y) for y in positive_yrs[:6])}"
                f"{'...' if len(positive_yrs) > 6 else ''}).",
                f"Years with negative growth (decline): **{len(negative_yrs)}** "
                f"({', '.join(str(y) for y in negative_yrs) if negative_yrs else 'None'}).",
                + ([f"Highest single-year growth: **{int(peak_g_row['ExamYear'])}** — "
                    f"{peak_g_row['GrowthRate']:+.1f}%."]
                   if peak_g_row is not None else [])
                + ([f"Largest single-year decline: **{int(low_g_row['ExamYear'])}** — "
                    f"{low_g_row['GrowthRate']:+.1f}%."]
                   if low_g_row is not None and low_g_row["GrowthRate"] < 0 else []),
            ],
            "observations": yr_obs,
            "implications": [
                f"An average growth rate of **{avg_growth:+.2f}%** "
                + (
                    "indicates the examination system has been expanding its "
                    "candidate base over the selected period — a positive "
                    "signal for educational access and participation."
                    if avg_growth > 0
                    else "indicates the examination system has been contracting "
                    "in candidate volumes over the selected period — "
                    "this warrants investigation into root causes."
                ),
                f"The peak year of **{peak_yr}** represents the highest "
                f"point of examination demand in the selected scope. "
                f"Understanding what drove this peak — policy changes, "
                f"demographic bulge, or improved access — can inform "
                f"future planning.",
                f"The trough year of **{low_yr}** represents the lowest "
                f"registration point. If this coincides with an external "
                f"event (economic disruption, conflict, pandemic), it may "
                f"explain the dip and signal a recovery pattern to monitor.",
                "Years showing negative growth are particularly important "
                "to investigate — a single-year dip may be noise, but "
                "consecutive negative years signal a structural problem.",
                "Sustained growth in registration places increasing pressure "
                "on examination infrastructure — centre capacity, invigilators, "
                "and marking resources must scale accordingly.",
            ],
            "recommendations": [
                f"Investigate the factors behind the **{peak_yr}** peak — "
                f"if driven by a specific policy or programme, assess whether "
                f"it can be sustained or replicated.",
                f"Examine the **{low_yr}** trough in detail — determine "
                f"whether it represents a data anomaly, an administrative "
                f"change, or a genuine decline in participation.",
                "Use the year-on-year growth rate chart (Chart 2) to identify "
                "any structural trend breaks — years where growth shifted "
                "suddenly from positive to negative or vice versa deserve "
                "contextual investigation.",
                "Project future registration volumes using the average growth "
                "rate to support 3–5 year infrastructure and resource planning.",
                "Cross-reference registration growth with centre capacity data "
                "to ensure examination infrastructure is scaling at the same "
                "pace as candidate volume growth.",
                "Compare this national trend against state-level trends using "
                "the **State Registration Trends** and "
                "**State Registration Growth Rate** reports to identify "
                "which states are driving or lagging behind the overall trend.",
            ],
        }

    elif analysis == "Registration by Exam Type":
        if "ExamType" not in df.columns or "Count" not in df.columns:
            return _empty(
                f"Registration by Exam Type. Total: **{fmt(total)}**. "
                f"Filters: {filter_desc}."
            )

        selected_years = sorted([int(y) for y in filters.get("ExamYear", [])])
        yr_part = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )

        et_totals = df.groupby("ExamType")["Count"].sum().sort_values(ascending=False)
        dominant_et  = et_totals.index[0]
        dominant_ct  = int(et_totals.iloc[0])
        dominant_pct = round(dominant_ct / total * 100, 1)
        et_count     = len(et_totals)

        et_findings = [
            f"**{et}**: {fmt(int(ct))} candidates "
            f"({round(int(ct)/total*100,1)}%)."
            for et, ct in et_totals.items()
        ]

        # Year trend per exam type
        et_obs = []
        if "ExamYear" in df.columns:
            for et in et_totals.index:
                et_yr = (
                    df[df["ExamType"] == et]
                    .groupby("ExamYear")["Count"].sum().sort_index()
                )
                if len(et_yr) >= 2:
                    direction = "grew" if et_yr.iloc[-1] > et_yr.iloc[0] else "declined"
                    chg = round(
                        abs(et_yr.iloc[-1] - et_yr.iloc[0])
                        / et_yr.iloc[0] * 100, 1
                    ) if et_yr.iloc[0] > 0 else 0
                    et_obs.append(
                        f"**{et}** registration {direction} by "
                        f"**{chg}%** from "
                        f"{fmt(int(et_yr.iloc[0]))} "
                        f"({int(et_yr.index[0])}) to "
                        f"{fmt(int(et_yr.iloc[-1]))} "
                        f"({int(et_yr.index[-1])})."
                    )

        return {
            "summary": (
                f"This report breaks down total candidate registration by "
                f"examination type across {yr_part}. "
                f"A total of **{fmt(total)}** unique candidates are covered "
                f"across **{et_count}** exam type"
                f"{'s' if et_count > 1 else ''}. "
                f"**{dominant_et}** is the dominant exam type, accounting for "
                f"**{dominant_pct}%** of all registrations "
                f"({fmt(dominant_ct)} candidates). "
                f"This report reveals how different examination pathways "
                f"attract candidates and how that balance shifts over time."
            ),
            "key_findings": [
                f"Total unique candidates across all exam types: **{fmt(total)}**.",
                f"Exam types represented: **{et_count}**.",
                f"Dominant exam type: **{dominant_et}** — "
                f"{fmt(dominant_ct)} candidates ({dominant_pct}%).",
            ] + et_findings,
            "observations": et_obs + [
                f"**{dominant_et}** consistently dominates registrations, "
                f"suggesting it is the primary examination pathway for the "
                f"majority of candidates in the selected scope.",
                f"The distribution across exam types reveals the relative "
                f"popularity of each examination pathway — a useful indicator "
                f"of how candidates and schools prefer to access the "
                f"examination system.",
            ],
            "implications": [
                f"The dominance of **{dominant_et}** with {dominant_pct}% "
                f"of registrations means examination infrastructure, "
                f"centre allocation, and marking resources must be heavily "
                f"weighted toward this exam type.",
                "Shifts in exam type proportions over time may reflect "
                "policy changes, school type demographics, or changes in "
                "candidate preferences — worth monitoring annually.",
                "A growing minority exam type may signal an emerging "
                "demographic shift that could affect infrastructure "
                "planning in coming years.",
                "Exam types with very low registration volumes may warrant "
                "review — whether they are adequately resourced or whether "
                "barriers to access exist for those pathways.",
            ],
            "recommendations": [
                f"Ensure examination centre capacity and invigilator "
                f"allocation is proportional to the **{dominant_et}** "
                f"share of total registrations.",
                "Track exam type proportions annually to detect any "
                "structural shifts — particularly if a minority type "
                "begins growing rapidly.",
                "Cross-reference exam type registration with Grade "
                "outcomes to assess whether different exam pathways "
                "produce different performance distributions.",
                "Investigate states where the exam type distribution "
                "differs significantly from the national average — "
                "this may reveal regional policy differences or "
                "infrastructure constraints.",
                "Use the stacked bar chart (Chart 1) to identify "
                "specific years where the exam type mix changed "
                "significantly — these inflection points may coincide "
                "with policy or demographic events worth documenting.",
            ],
        }

    elif analysis == "Registration Forecast":
        if "ExamYear" not in df.columns or "Count" not in df.columns:
            return _empty(
                f"Registration Forecast. Total: **{fmt(total)}**. "
                f"Filters: {filter_desc}."
            )

        import numpy as np

        horizon = int(filters.get("ForecastHorizon", 3))
        selected_years = sorted([int(y) for y in filters.get("ExamYear", [])])
        yr_part = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )

        df2 = df.copy()
        df2["ExamYear"] = df2["ExamYear"].astype(int)
        df2 = df2.sort_values("ExamYear")

        years    = df2["ExamYear"].values
        counts   = df2["Count"].values
        x        = years - years[0]
        slope, intercept = np.polyfit(x, counts, 1)

        residuals  = counts - (slope * x + intercept)
        std_err    = np.std(residuals)
        r_squared  = 1 - (np.sum(residuals**2) /
                         np.sum((counts - counts.mean())**2))
        r_squared  = round(float(r_squared), 4)

        last_yr    = int(years[-1])
        last_ct    = int(counts[-1])
        first_yr   = int(years[0])
        first_ct   = int(counts[0])

        # Forecast values
        forecast_rows = []
        for h in range(1, horizon + 1):
            f_yr  = last_yr + h
            f_x   = f_yr - years[0]
            f_ct  = max(int(slope * f_x + intercept), 0)
            ci    = 1.96 * std_err * np.sqrt(
                1 + 1/len(x) + (f_x - x.mean())**2
                / ((x - x.mean())**2).sum()
            )
            f_lo  = max(int(f_ct - ci), 0)
            f_hi  = int(f_ct + ci)
            forecast_rows.append({
                "year": f_yr,
                "forecast": f_ct,
                "lower": f_lo,
                "upper": f_hi,
            })

        trend_direction = "upward" if slope > 0 else "downward"
        model_quality   = (
            "strong" if r_squared >= 0.8
            else "moderate" if r_squared >= 0.5
            else "weak"
        )

        forecast_findings = [
            f"**{row['year']}**: forecast **{fmt(row['forecast'])}** candidates "
            f"(95% CI: {fmt(row['lower'])} – {fmt(row['upper'])})."
            for row in forecast_rows
        ]

        hist_obs = []
        for _, row in df2.iterrows():
            hist_obs.append(
                f"**{int(row['ExamYear'])}**: "
                f"{fmt(int(row['Count']))} unique candidates (actual)."
            )

        return {
            "summary": (
                f"This report projects candidate registration volumes for the "
                f"next **{horizon} year{'s' if horizon > 1 else ''}** "
                f"({last_yr + 1}–{last_yr + horizon}) based on historical "
                f"trends from {yr_part}. "
                f"Using linear regression on **{len(years)} years** of "
                f"historical data ({first_yr}–{last_yr}), the model identifies "
                f"a **{trend_direction}** trend of approximately "
                f"**{abs(slope):,.0f} candidates per year**. "
                f"The model fit quality is **{model_quality}** "
                f"(R² = {r_squared:.4f}). "
                f"Forecast values include a **95% confidence interval** "
                f"reflecting the uncertainty inherent in any projection."
            ),
            "key_findings": [
                f"Historical period: **{first_yr}–{last_yr}** "
                f"({len(years)} exam years).",
                f"Historical registration range: "
                f"**{fmt(int(counts.min()))}** to "
                f"**{fmt(int(counts.max()))}** candidates per year.",
                f"Most recent actual count (**{last_yr}**): "
                f"**{fmt(last_ct)}** candidates.",
                f"Trend: **{'+' if slope > 0 else ''}{slope:,.0f} "
                f"candidates per year** on average.",
                f"Model R²: **{r_squared:.4f}** — "
                f"{model_quality} predictive fit.",
            ] + forecast_findings,
            "observations": hist_obs + [
                f"The linear trend line "
                + (
                    f"projects **growth** of approximately "
                    f"**{fmt(abs(int(slope)))} candidates per year**, "
                    f"suggesting the examination system will continue expanding "
                    f"if historical patterns hold."
                    if slope > 0 else
                    f"projects **decline** of approximately "
                    f"**{fmt(abs(int(slope)))} candidates per year**, "
                    f"suggesting the examination candidate base is contracting "
                    f"if historical patterns continue."
                ),
                f"The 95% confidence interval widens with each forecast year — "
                f"the {last_yr + 1} projection is more reliable than the "
                f"{last_yr + horizon} projection, as uncertainty accumulates "
                f"over longer horizons.",
                f"An R² of **{r_squared:.4f}** means the linear trend explains "
                f"**{round(r_squared*100, 1)}%** of the variation in historical "
                f"registration counts. "
                + (
                    "This is a strong fit — the forecast is relatively reliable."
                    if r_squared >= 0.8
                    else "This is a moderate fit — the forecast should be "
                    "treated as a directional guide, not a precise prediction."
                    if r_squared >= 0.5
                    else "This is a weak fit — historical data is highly "
                    "variable and the forecast carries significant uncertainty. "
                    "Use with caution."
                ),
            ],
            "implications": [
                f"If the **{trend_direction}** trend continues, the examination "
                f"system can expect approximately "
                f"**{fmt(forecast_rows[-1]['forecast'])}** candidates "
                f"by **{forecast_rows[-1]['year']}**. "
                + (
                    "This growth requires proportional expansion of examination "
                    "infrastructure — centres, invigilators, and marking capacity."
                    if slope > 0 else
                    "This decline signals a need to review policies affecting "
                    "school enrolment and examination access."
                ),
                "Forecasts based on linear regression assume that past trends "
                "will continue at the same rate. Structural breaks — policy "
                "changes, demographic shifts, economic disruptions — can "
                "invalidate the projection.",
                f"The widening confidence interval by **{last_yr + horizon}** "
                f"reflects increasing uncertainty over longer horizons. "
                f"Short-range forecasts ({last_yr + 1}–{last_yr + 2}) "
                f"should be treated as more reliable than long-range ones.",
                "This forecast should be updated annually with new data to "
                "maintain its accuracy — a forecast based on 5 additional "
                "years of data will be materially more reliable.",
            ],
            "recommendations": [
                f"Use the **{last_yr + 1}** forecast of "
                f"**{fmt(forecast_rows[0]['forecast'])}** candidates as the "
                f"planning baseline for the next examination cycle — "
                f"centre capacity, paper printing, and invigilator deployment "
                f"should be sized accordingly.",
                f"Treat the **{last_yr + horizon}** projection of "
                f"**{fmt(forecast_rows[-1]['forecast'])}** as a long-range "
                f"planning signal, not a precise target — revisit annually "
                f"as new data becomes available.",
                "Cross-reference this forecast with the **State Registration "
                "Growth Rate** report to identify which states are driving "
                "the overall trend and where regional projections diverge "
                "from the national picture.",
                "If the model R² is below 0.5, consider requesting a "
                "more advanced forecasting analysis using non-linear models "
                "— the data may contain cycles or structural breaks that "
                "linear regression cannot capture.",
                "Monitor actual registration counts annually against the "
                "forecast — consistent under- or over-shooting of the "
                "projection may indicate a structural change that requires "
                "the model to be recalibrated.",
            ],
        }
    
    elif any(x in analysis for x in ["Registration", "Enrollment", "Forecast",
                                      "Growth Rate", "Cyclical", "Compound"]):
        lines = [f"{analysis}. Filters: {filter_desc}. Total: **{fmt(total)}**."]
        if has("ExamYear"):
            yr_agg = df.groupby("ExamYear")["Count"].sum().sort_values()
            yrs    = sorted(yr_agg.index.astype(int))
            yr_range = f"{yrs[0]}–{yrs[-1]}" if len(yrs) > 1 else str(yrs[0])
            lines.append(f"Years: **{yr_range}**.")
            if len(yrs) >= 2:
                first = int(yr_agg.iloc[0])
                last  = int(yr_agg.iloc[-1])
                direction = "increased" if last > first else "decreased"
                lines.append(
                    f"Registration {direction} from **{fmt(first)}** "
                    f"to **{fmt(last)}** over the period."
                )
        if has("Sex"):
            male_ct   = int(df[df["Sex"].str.lower() == "male"]["Count"].sum())
            female_ct = int(df[df["Sex"].str.lower() == "female"]["Count"].sum())
            lines.append(
                f"Gender split — Male: {pct(male_ct, total)}, "
                f"Female: {pct(female_ct, total)}."
            )
        return " ".join(lines)

    # ---TOP & BOTTOM REPORTS (GENERAL)────────────────────────────────────────────
    elif analysis == "Top & Bottom States by Candidate Volume":
        if "State" not in df.columns or "Count" not in df.columns:
            return _empty(
                f"Top & Bottom States. Total: **{fmt(total)}**. "
                f"Filters: {filter_desc}."
            )

        top_n          = int(filters.get("TopN", 5))
        selected_years = sorted([int(y) for y in filters.get("ExamYear", [])])
        yr_part        = (
            f"exam years **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else "all available exam years"
        )

        # Split top and bottom
        if "RankGroup" in df.columns:
            top_df = df[df["RankGroup"] == f"Top {top_n}"]
            bot_df = df[df["RankGroup"] == f"Bottom {top_n}"]
        else:
            state_totals = df.groupby("State")["Count"].sum().sort_values(ascending=False)
            top_states   = state_totals.head(top_n).index.tolist()
            bot_states   = state_totals.tail(top_n).index.tolist()
            top_df       = df[df["State"].isin(top_states)]
            bot_df       = df[df["State"].isin(bot_states)]

        top_totals = top_df.groupby("State")["Count"].sum().sort_values(ascending=False)
        bot_totals = bot_df.groupby("State")["Count"].sum().sort_values(ascending=True)

        top_state    = top_totals.index[0]  if not top_totals.empty else "N/A"
        top_ct       = int(top_totals.iloc[0]) if not top_totals.empty else 0
        bot_state    = bot_totals.index[0]  if not bot_totals.empty else "N/A"
        bot_ct       = int(bot_totals.iloc[0]) if not bot_totals.empty else 0
        total_top    = int(top_totals.sum())
        total_bot    = int(bot_totals.sum())
        spread       = top_ct - bot_ct

        # Per-year trend for leading state
        yr_obs = []
        if "ExamYear" in df.columns and len(selected_years) > 1:
            top_yr = (
                top_df[top_df["State"] == top_state]
                .groupby("ExamYear")["Count"].sum().sort_index()
            )
            if len(top_yr) >= 2:
                direction = "grew" if top_yr.iloc[-1] > top_yr.iloc[0] else "declined"
                yr_obs.append(
                    f"**{top_state}** registration {direction} from "
                    f"{fmt(int(top_yr.iloc[0]))} in {int(top_yr.index[0])} "
                    f"to {fmt(int(top_yr.iloc[-1]))} in {int(top_yr.index[-1])}."
                )
            bot_yr = (
                bot_df[bot_df["State"] == bot_state]
                .groupby("ExamYear")["Count"].sum().sort_index()
            )
            if len(bot_yr) >= 2:
                direction = "grew" if bot_yr.iloc[-1] > bot_yr.iloc[0] else "declined"
                yr_obs.append(
                    f"**{bot_state}** registration {direction} from "
                    f"{fmt(int(bot_yr.iloc[0]))} in {int(bot_yr.index[0])} "
                    f"to {fmt(int(bot_yr.iloc[-1]))} in {int(bot_yr.index[-1])}."
                )

        top_findings = [
            f"**#{i+1} {state}**: {fmt(int(ct))} unique candidates "
            f"({round(int(ct)/total*100,1)}% of total scope)."
            for i, (state, ct) in enumerate(top_totals.items())
        ]
        bot_findings = [
            f"**#{i+1} {state}**: {fmt(int(ct))} unique candidates "
            f"({round(int(ct)/total*100,1)}% of total scope)."
            for i, (state, ct) in enumerate(bot_totals.items())
        ]

        return {
            "summary": (
                f"This report identifies the **top {top_n}** and "
                f"**bottom {top_n}** states by unique candidate registration "
                f"volume for {yr_part}. "
                f"A total of **{fmt(total)}** unique candidates are captured "
                f"across the {top_n * 2} ranked states. "
                f"The top {top_n} states collectively account for "
                f"**{fmt(total_top)}** candidates, while the bottom {top_n} "
                f"account for **{fmt(total_bot)}**. "
                f"This analysis reveals where examination participation is most "
                f"and least concentrated geographically, supporting "
                f"infrastructure and policy planning decisions."
            ),
            "key_findings": [
                f"Total unique candidates across ranked states: **{fmt(total)}**.",
                f"Top {top_n} states combined: **{fmt(total_top)}** candidates.",
                f"Bottom {top_n} states combined: **{fmt(total_bot)}** candidates.",
                f"Highest registration state: **{top_state}** — "
                f"{fmt(top_ct)} candidates.",
                f"Lowest registration state: **{bot_state}** — "
                f"{fmt(bot_ct)} candidates.",
                f"Registration spread between highest and lowest: "
                f"**{fmt(spread)} candidates**.",
            ],
            "observations": (
                [f"**TOP {top_n} STATES:**"]
                + top_findings
                + [f"**BOTTOM {top_n} STATES:**"]
                + bot_findings
                + yr_obs
                + [
                    f"The top {top_n} states account for "
                    f"**{round(total_top/total*100,1)}%** of all candidates "
                    f"in the ranked scope, indicating significant geographic "
                    f"concentration of examination demand.",
                    f"The bottom {top_n} states account for only "
                    f"**{round(total_bot/total*100,1)}%** of the ranked scope "
                    f"total, highlighting substantial disparity in "
                    f"examination participation.",
                ]
            ),
            "implications": [
                f"**{top_state}** dominates candidate registration with "
                f"{fmt(top_ct)} candidates. This concentration may reflect "
                f"population size, urbanisation, school density, or strong "
                f"examination infrastructure in that state.",
                f"**{bot_state}** records the lowest registration at "
                f"{fmt(bot_ct)} candidates. This may reflect geographic "
                f"remoteness, lower school enrolment, infrastructure gaps, "
                f"or socioeconomic barriers to examination access.",
                "The large gap between top and bottom states signals significant "
                "inequality in examination participation that may warrant "
                "targeted educational investment in lower-performing states.",
                "States consistently appearing in the bottom ranking across "
                "multiple years may face structural barriers requiring "
                "long-term policy intervention rather than short-term fixes.",
            ],
            "recommendations": [
                f"Investigate the factors driving **{top_state}'s** high "
                f"registration volume — school density, population, and "
                f"infrastructure — and consider replicating successful elements "
                f"in lower-performing states.",
                f"Prioritise infrastructure assessment in **{bot_state}** and "
                f"other bottom-ranking states to identify whether examination "
                f"centre availability is a limiting factor for registration.",
                "Cross-reference registration volume with performance outcomes "
                "(Grade data) to determine whether high-registration states "
                "also achieve proportionally high pass rates.",
                "Use this report alongside **Centre Count by State & Region** "
                "and **Candidate Load per Centre** to build a complete picture "
                "of where demand meets or exceeds available infrastructure.",
                f"Track bottom-ranking states across multiple exam years — "
                f"states showing declining registration over time may need "
                f"urgent policy attention to prevent further disengagement.",
            ],
        }
 
    # ── SPONSOR REPORTS ───────────────────────────────────────────────────────
    elif "Sponsor" in analysis:
        if not has("Sponsor"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        sp = df.groupby("Sponsor")["Count"].sum().sort_values(ascending=False)
        top = sp.index[0]
        top_ct = int(sp.iloc[0])
        return (
            f"{analysis}. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. "
            f"Leading sponsor type: **{top}** — {fmt(top_ct)} ({pct(top_ct, total)})."
        )

    # ── EXAM TYPE REPORTS ─────────────────────────────────────────────────────
    elif "Exam Type" in analysis or analysis in (
        "Exam Type Volume Comparison", "Exam Type Share by Year",
        "Exam Type by State", "Exam Type by Gender"
    ):
        if not has("ExamType"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        et = df.groupby("ExamType")["Count"].sum().sort_values(ascending=False)
        top = et.index[0]
        top_ct = int(et.iloc[0])
        lines = [
            f"{analysis}. Filters: {filter_desc}. Total: **{fmt(total)}**. "
            f"Most common exam type: **{top}** — {fmt(top_ct)} ({pct(top_ct, total)})."
        ]
        if has("Grade"):
            # Only compute credit rate if Grade is actually in this data
            agg = credit_rate(df, ["ExamType"])
            for _, row in agg.sort_values("CreditRate", ascending=False).iterrows():
                lines.append(f"**{row['ExamType']}**: {row['CreditRate']}% credit rate.")
        return " ".join(lines)

    # ── SUBJECT REPORTS ───────────────────────────────────────────────────────
    elif "Subject" in analysis:
        if not has("Subject"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        sub = df.groupby("Subject")["Count"].sum().sort_values(ascending=False)
        top = sub.index[0]
        top_ct = int(sub.iloc[0])
        lines = [
            f"{analysis}. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** across **{sub.nunique()}** subjects. "
            f"Most registered: **{top}** — {fmt(top_ct)} ({pct(top_ct, total)})."
        ]
        if has("Grade"):
            agg = credit_rate(df, ["Subject"]).sort_values("CreditRate", ascending=False)
            if not agg.empty:
                lines.append(
                    f"Highest credit rate: **{agg.iloc[0]['Subject']}** "
                    f"({agg.iloc[0]['CreditRate']}%)."
                )
        return " ".join(lines)

    # ── ABSENTEEISM REPORTS ───────────────────────────────────────────────────
    elif analysis == "Registered vs Sat Candidates":
        if not has("Status"):
            return f"Registered vs Sat. Total: **{fmt(total)}**. Filters: {filter_desc}."

        status_counts = df.groupby("Status")["Count"].sum()

        # Candidates who sat = those with a result status
        sat_statuses    = ["Excellent", "Very Good", "Credit", "Pass", "Fail"]
        non_sat_statuses = ["Absent", "Cancelled", "Pending", "Withheld"]

        sat_ct    = int(df[df["Status"].isin(sat_statuses)]["Count"].sum())
        absent_ct = int(df[df["Status"] == "Absent"]["Count"].sum())
        other_ct  = int(df[df["Status"].isin(
            ["Cancelled", "Pending", "Withheld"])]["Count"].sum())

        selected_years  = filters.get("ExamYear", [])
        selected_states = filters.get("State", [])
        yr_part = (
            f" for **{', '.join(str(y) for y in selected_years)}**"
            if selected_years else ""
        )
        st_part = (
            f" in **{', '.join(selected_states)}**"
            if selected_states else ""
        )

        return (
            f"Your **Registered vs Sat Candidates** report{yr_part}{st_part} covers "
            f"**{fmt(total)}** registered candidates. "
            f"**{fmt(sat_ct)}** ({pct(sat_ct, total)}) sat and received a result. "
            f"**{fmt(absent_ct)}** ({pct(absent_ct, total)}) were absent. "
            f"**{fmt(other_ct)}** ({pct(other_ct, total)}) had other statuses "
            f"(Cancelled, Pending, or Withheld). "
            + ("✅ Attendance rate is strong." if sat_ct / total > 0.85
               else "⚠️ A significant number of registered candidates did not sit.")
        )

    elif analysis == "Absenteeism Rate by State":
        if not has("Status") or not has("State"):
            return f"Absenteeism by state. Total: **{fmt(total)}**. Filters: {filter_desc}."

        selected_states = filters.get("State", [])
        st_part = (
            f" in **{', '.join(selected_states)}**"
            if selected_states else " across all states"
        )

        absent_by_state = df[df["Status"] == "Absent"].groupby(
            "State")["Count"].sum().sort_values(ascending=False)
        total_by_state  = df.groupby("State")["Count"].sum()

        if absent_by_state.empty:
            return (
                f"Absenteeism by state{st_part}. "
                f"Total: **{fmt(total)}**. No absent candidates found."
            )

        rate_by_state = (
            absent_by_state / total_by_state * 100
        ).dropna().sort_values(ascending=False)

        top_state    = rate_by_state.index[0]
        top_rate     = round(float(rate_by_state.iloc[0]), 1)
        top_absent   = int(absent_by_state.get(top_state, 0))
        bot_state    = rate_by_state.index[-1]
        bot_rate     = round(float(rate_by_state.iloc[-1]), 1)
        absent_total = int(absent_by_state.sum())
        overall_rate = round(absent_total / total * 100, 1)

        return (
            f"Your **Absenteeism Rate by State** report{st_part} covers "
            f"**{fmt(total)}** total registered candidates. "
            f"**{fmt(absent_total)}** ({overall_rate}%) were absent overall. "
            f"Highest absenteeism rate: **{top_state}** — {top_rate}% "
            f"({fmt(top_absent)} absent candidates). "
            f"Lowest: **{bot_state}** — {bot_rate}%."
        )

    elif analysis == "Absenteeism by Exam Type & Gender":
        if not has("Status"):
            return f"Absenteeism by exam type and gender. Total: **{fmt(total)}**. Filters: {filter_desc}."
        absent_ct = int(df[df["Status"].str.lower() == "absent"]["Count"].sum())
        lines = [
            f"Absenteeism by exam type and gender. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}**. Overall absent: **{fmt(absent_ct)}** ({pct(absent_ct, total)})."
        ]
        if has("ExamType"):
            et_absent = df[df["Status"].str.lower() == "absent"].groupby(
                "ExamType")["Count"].sum().sort_values(ascending=False)
            et_total  = df.groupby("ExamType")["Count"].sum()
            for et in et_absent.index[:3]:
                rate = round(et_absent[et] / et_total[et] * 100, 1)
                lines.append(f"**{et}**: {rate}% absenteeism.")
        return " ".join(lines)

    elif analysis == "Absenteeism Trends Over Time":
        if not has("Status") or not has("ExamYear"):
            return f"Absenteeism trends. Total: **{fmt(total)}**. Filters: {filter_desc}."
        yr_total  = df.groupby("ExamYear")["Count"].sum()
        yr_absent = df[df["Status"].str.lower() == "absent"].groupby(
            "ExamYear")["Count"].sum()
        yr_rate   = (yr_absent / yr_total * 100).dropna().sort_values()
        yrs       = sorted(yr_rate.index.astype(int))
        direction = "improved" if yr_rate.iloc[-1] < yr_rate.iloc[0] else "worsened"
        return (
            f"Absenteeism trends over time. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** across **{len(yrs)}** exam years. "
            f"Attendance has **{direction}** from "
            f"**{round(float(yr_rate.iloc[0]), 1)}%** absenteeism in **{yrs[0]}** "
            f"to **{round(float(yr_rate.iloc[-1]), 1)}%** in **{yrs[-1]}**."
        )

    elif any(x in analysis for x in ["Absenteeism", "Attendance", "Sat"]):
        if not has("Status"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        st_agg = df.groupby("Status")["Count"].sum()
        lines  = [f"{analysis}. Filters: {filter_desc}. Total: **{fmt(total)}**."]
        for status, ct in st_agg.items():
            lines.append(f"**{status}**: {fmt(int(ct))} ({pct(int(ct), total)}).")
        return " ".join(lines)

    # ── CENTRE REPORTS ────────────────────────────────────────────────────────
    elif "Centre" in analysis or "Center" in analysis:
        if not has("centre"):
            return f"{analysis}. Total: **{fmt(total)}**. Filters: {filter_desc}."
        ct_agg = df.groupby("centre")["Count"].sum().sort_values(ascending=False)
        top    = ct_agg.index[0]
        top_ct = int(ct_agg.iloc[0])
        return (
            f"{analysis}. Filters: {filter_desc}. "
            f"Total: **{fmt(total)}** records across **{ct_agg.nunique()}** centres. "
            f"Highest volume centre: **{top}** — {fmt(top_ct)} candidates."
        )

    # ── GRADE-BASED REPORTS (only when Grade column exists) ───────────────────
    elif has("Grade"):
        return _grade_narrative(analysis, df, filters, total, filter_desc)

    # ── GENERIC FALLBACK ──────────────────────────────────────────────────────
    else:
        lines = [f"**{analysis}**. Filters: {filter_desc}. Total: **{fmt(total)}**."]
        for col in ["ExamYear", "State", "Sex", "AgeGroup", "Disability",
                    "ExamType", "Sponsor"]:
            if has(col):
                top_val = df.groupby(col)["Count"].sum().idxmax()
                top_ct  = int(df.groupby(col)["Count"].sum().max())
                lines.append(
                    f"Top **{col}**: {top_val} "
                    f"({fmt(top_ct)}, {pct(top_ct, total)})."
                )
        return {
            "summary":         lines[0] if lines else f"{analysis}. Total: **{fmt(total)}**.",
            "key_findings":    lines[1:] if len(lines) > 1 else [],
            "observations":    [],
            "implications":    [],
            "recommendations": [],
        }


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

        # ── GENERATIONAL EDUCATION TRENDS ──
        elif analysis == "Generational Education Trends":
            if "Generation" not in df.columns or "ExamYear" not in df.columns:
                return None

            gen_order = [
                "Silent Generation (1928–1945)",
                "Baby Boomers (1946–1964)",
                "Gen X (1965–1980)",
                "Millennials (1981–1996)",
                "Gen Z (1997–2012)",
                "Gen Alpha (2013–2025)",
            ]

            clean = df[~df["Generation"].isin(["Unknown", None])].copy()
            if clean.empty:
                return None

            clean = clean.sort_values(["ExamYear", "Generation"])

            # ── Chart 1: Area chart — participation over time per generation ──
            g1 = clean.groupby(
                ["ExamYear", "Generation"])["Count"].sum().reset_index()

            fig1 = px.area(
                g1,
                x="ExamYear",
                y="Count",
                color="Generation",
                title="Candidate Participation by Generation Over Time",
                labels={
                    "Count":      "Unique Candidates",
                    "ExamYear":   "Examination Year",
                    "Generation": "Birth Generation",
                },
                color_discrete_sequence=COLOR_PALETTE,
                category_orders={"Generation": gen_order},
                line_group="Generation",
            )
            fig1.update_layout(**L)
            fig1.update_xaxes(showgrid=False, title="Examination Year")
            fig1.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")

            # ── Chart 2: Horizontal bar — total share per generation ──────────
            g2 = clean.groupby("Generation")["Count"].sum().reset_index()
            g2["Pct"] = (g2["Count"] / g2["Count"].sum() * 100).round(1)
            g2 = g2.sort_values("Count", ascending=True)

            fig2 = px.bar(
                g2,
                x="Count",
                y="Generation",
                orientation="h",
                title="Total Candidate Share by Generation",
                text=g2["Pct"].astype(str) + "%",
                color="Generation",
                color_discrete_sequence=COLOR_PALETTE,
                category_orders={"Generation": gen_order},
                labels={
                    "Count":      "Unique Candidates",
                    "Generation": "Birth Generation",
                },
            )
            fig2.update_traces(textposition="outside")
            fig2.update_layout(**L)
            fig2.update_xaxes(showgrid=False, title="Unique Candidates")
            fig2.update_yaxes(showgrid=False)

            # ── Chart 3: Stacked bar — generation mix per exam year ───────────
            g3 = clean.groupby(
                ["ExamYear", "Generation"])["Count"].sum().reset_index()
            g3["ExamYear"] = g3["ExamYear"].astype(str)

            fig3 = px.bar(
                g3,
                x="ExamYear",
                y="Count",
                color="Generation",
                barmode="stack",
                title="Generational Mix per Exam Year",
                labels={
                    "Count":      "Unique Candidates",
                    "ExamYear":   "Exam Year",
                    "Generation": "Birth Generation",
                },
                color_discrete_sequence=COLOR_PALETTE,
                category_orders={"Generation": gen_order},
            )
            fig3.update_layout(**L)
            fig3.update_xaxes(
                showgrid=False,
                title="Exam Year",
                tickangle=-45,
            )
            fig3.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")

            return (fig1, fig2, fig3)

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
       # ── SUBJECT PERFORMANCE TRENDS — multi-line chart ───────────────────
        elif analysis == "Subject Performance Trends":
            if "Subject" not in df.columns or "ExamYear" not in df.columns:
                return None

            # Aggregate data for the selected subjects and years
            agg = credit_rate(df, ["Subject", "ExamYear"]).sort_values("ExamYear")
            
            if agg.empty:
                return None # Return None if no data after aggregation

            fig = px.line(
                agg,
                x="ExamYear",           # X-axis: Exam Year
                y="CreditRate",         # Y-axis: Credit Rate (%)
                color="Subject",        # Line color based on Subject
                markers=True,           # Show markers on each data point
                title="Subject Credit Rate Trends",
                labels={
                    "CreditRate": "Credit Rate (%)",
                    "ExamYear": "Exam Year"
                },
                color_discrete_sequence=COLOR_PALETTE, # Use your defined color palette
            )
            
            # Layout adjustments for clarity
            fig.update_layout(
                **{k: v for k, v in _layout().items() if k not in ("xaxis", "yaxis")}, # Update base layout
                margin=dict(l=50, r=50, t=80, b=80), # Adjust margins for X-axis labels
                xaxis=dict(
                    showgrid=False,
                    type='category', # Treat ExamYear as discrete categories (years)
                    title_font=dict(size=12, color="#6c757d"),
                    tickfont=dict(color="#1e293b"), # Ensure tick labels are visible
                    tickangle=45 # Angle labels to prevent overlap if many years
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor="#f1f3f5",
                    range=[0, 100],       # Ensure Y-axis is always 0-100%
                    ticksuffix="%",
                    title="Credit Rate (%)",
                    titlefont=dict(size=12, color="#6c757d"),
                    tickfont=dict(color="#1e293b")
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3, # Position legend below the chart
                    xanchor="center",
                    x=0.5,
                ),
            )
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
        
        # Top & Bottom states by candidate volume — horizontal bar chart(s)
        elif analysis == "Top & Bottom States by Candidate Volume":
            if "State" not in df.columns or "Count" not in df.columns:
                return None

            top_n     = int(filters.get("TopN", 5))
            sel_years = sorted(df["ExamYear"].dropna().unique().astype(int).tolist()) \
                        if "ExamYear" in df.columns else []

            if not sel_years:
                # No year breakdown — single horizontal bar chart
                state_totals = (
                    df.groupby(["State", "RankGroup"])["Count"]
                    .sum().reset_index()
                    .sort_values("Count", ascending=True)
                )
                state_totals["StateLabel"] = state_totals["State"]

                fig = px.bar(
                    state_totals,
                    x="Count", y="StateLabel",
                    orientation="h",
                    color="RankGroup",
                    color_discrete_map={
                        f"Top {top_n}":    "#16a34a",
                        f"Bottom {top_n}": "#dc2626",
                    },
                    title=f"Top & Bottom {top_n} States by Candidate Volume",
                    labels={
                        "Count":      "Unique Candidates",
                        "StateLabel": "State",
                        "RankGroup":  "Group",
                    },
                    text=state_totals["Count"].apply(lambda x: f"{int(x):,}"),
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(**L)
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(showgrid=False)
                return fig

            # One chart per selected ExamYear
            figs = []
            for yr in sel_years:
                yr_df = df[df["ExamYear"] == yr].copy()
                if yr_df.empty:
                    continue
                yr_df = yr_df.sort_values("Count", ascending=True)
                yr_df["StateLabel"] = yr_df["State"]

                fig = px.bar(
                    yr_df,
                    x="Count", y="StateLabel",
                    orientation="h",
                    color="RankGroup",
                    color_discrete_map={
                        f"Top {top_n}":    "#16a34a",
                        f"Bottom {top_n}": "#dc2626",
                    },
                    title=f"Top & Bottom {top_n} States — {yr}",
                    labels={
                        "Count":      "Unique Candidates",
                        "StateLabel": "State",
                        "RankGroup":  "Group",
                    },
                    text=yr_df["Count"].apply(lambda x: f"{int(x):,}"),
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(**L)
                fig.update_xaxes(showgrid=False, title="Unique Candidates")
                fig.update_yaxes(showgrid=False, title="")
                figs.append(fig)

            return tuple(figs) if figs else None
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
        elif analysis == "Exam Type by Gender":
            if "ExamType" not in df.columns or "Sex" not in df.columns:
                return None
            g = df.groupby(["ExamType", "Sex"])["Count"].sum().reset_index()
            fig = px.bar(
                g, x="ExamType", y="Count", color="Sex",
                barmode="group",
                title="Candidates by Exam Type and Gender",
                labels={"Count": "Candidates", "ExamType": "Exam Type"},
                color_discrete_sequence=["#1e293b", "#667eea"],
                text=g["Count"].apply(lambda x: f"{int(x):,}"),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", title="Candidates")
            return fig

        elif analysis == "Exam Type by State":
            if "ExamType" not in df.columns or "State" not in df.columns:
                return None
            g = df.groupby(["State", "ExamType"])["Count"].sum().reset_index()
            fig = px.bar(
                g, x="State", y="Count", color="ExamType",
                barmode="group",
                title="Candidates by State and Exam Type",
                labels={"Count": "Candidates", "State": "State"},
                color_discrete_sequence=COLOR_PALETTE,
                text=g["Count"].apply(lambda x: f"{int(x):,}"),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False, tickangle=-35)
            fig.update_yaxes(gridcolor="#f1f3f5", title="Candidates")
            return fig

        elif analysis == "Exam Type Volume Comparison":
            if "ExamType" not in df.columns:
                return None
            g = df.groupby("ExamType")["Count"].sum().reset_index()
            g = g.sort_values("Count", ascending=False)
            fig = px.bar(
                g, x="ExamType", y="Count",
                title="Candidate Volume by Exam Type",
                color="ExamType",
                color_discrete_sequence=COLOR_PALETTE,
                text=g["Count"].apply(lambda x: f"{int(x):,}"),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", title="Candidates")
            return fig

        elif analysis == "Exam Type Share by Year":
            if "ExamType" not in df.columns or "ExamYear" not in df.columns:
                return None
            g = df.groupby(["ExamYear", "ExamType"])["Count"].sum().reset_index()
            fig = px.bar(
                g, x="ExamYear", y="Count", color="ExamType",
                barmode="stack",
                title="Exam Type Share by Year",
                labels={"Count": "Candidates", "ExamYear": "Exam Year"},
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5", title="Candidates")
            return fig

        elif "Exam Type" in analysis or "ExamType" in analysis:
            if "ExamType" in df.columns and "ExamYear" in df.columns:
                g = df.groupby(["ExamYear", "ExamType"])["Count"].sum().reset_index()
                fig = px.bar(
                    g, x="ExamYear", y="Count", color="ExamType",
                    barmode="stack",
                    title="Candidates by Exam Year and Type",
                    color_discrete_sequence=COLOR_PALETTE,
                )
                fig.update_layout(**L)
                return fig

        elif analysis == "Age Range of Candidates":
            if "Age" not in df.columns:
                return None

            bracket_order = ["Under 15", "15–17", "18–20", "21–25", "26–35", "Over 35"]

            def bracket(a):
                if a < 15:  return "Under 15"
                if a <= 17: return "15–17"
                if a <= 20: return "18–20"
                if a <= 25: return "21–25"
                if a <= 35: return "26–35"
                return "Over 35"

            df2 = df.copy()
            df2["Bracket"] = df2["Age"].apply(bracket)

            # ── Chart 1: Overall age spread (collapsed across years/states) ──
            age_summary = df2.groupby("Age")["Count"].sum().reset_index()
            peak_age    = int(age_summary.set_index("Age")["Count"].idxmax())

            fig1 = px.bar(
                age_summary.sort_values("Age"),
                x="Age", y="Count",
                title="Full Age Spread of Candidates (All Selected Years & States)",
                labels={"Age": "Candidate Age", "Count": "Unique Candidates"},
                color="Count",
                color_continuous_scale=["#e2e8f0", "#1e293b"],
            )
            fig1.add_vline(
                x=peak_age, line_dash="dash", line_color="#dc2626",
                annotation_text=f"Peak age: {peak_age}",
                annotation_position="top right",
            )
            fig1.update_layout(**L)
            fig1.update_coloraxes(showscale=False)
            fig1.update_xaxes(showgrid=False, title="Age")
            fig1.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")

            # ── Chart 2: Age bracket × ExamYear × State faceted grouped bar ──
            has_year  = "ExamYear" in df2.columns and df2["ExamYear"].nunique() > 0
            has_state = "State"    in df2.columns and df2["State"].nunique()    > 0

            if has_year and has_state:
                yr_br = (
                    df2.groupby(["ExamYear", "State", "Bracket"])["Count"]
                    .sum().reset_index()
                )
                yr_br["ExamYear"] = yr_br["ExamYear"].astype(str)

                n_years  = yr_br["ExamYear"].nunique()
                col_wrap = min(n_years, 3)

                fig2 = px.bar(
                    yr_br,
                    x="Bracket",
                    y="Count",
                    color="State",
                    barmode="group",
                    facet_col="ExamYear",
                    facet_col_wrap=col_wrap,
                    title="Age Bracket Distribution by Exam Year and State",
                    labels={
                        "Count":    "Unique Candidates",
                        "Bracket":  "Age Bracket",
                        "ExamYear": "Exam Year",
                        "State":    "State",
                    },
                    color_discrete_sequence=COLOR_PALETTE,
                    category_orders={
                        "Bracket":  bracket_order,
                        "ExamYear": sorted(yr_br["ExamYear"].unique().tolist()),
                    },
                    height=420 * ((n_years // col_wrap) + 1),
                )
                fig2.update_layout(**L)
                fig2.update_xaxes(showgrid=False, tickangle=-35)
                fig2.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")
                fig2.for_each_annotation(
                    lambda a: a.update(text=a.text.split("=")[-1])
                )
                return (fig1, fig2)

            elif has_year:
                # No state filter — group by year only
                yr_br = (
                    df2.groupby(["ExamYear", "Bracket"])["Count"]
                    .sum().reset_index()
                )
                yr_br["ExamYear"] = yr_br["ExamYear"].astype(str)
                fig2 = px.bar(
                    yr_br,
                    x="Bracket", y="Count",
                    color="ExamYear",
                    barmode="group",
                    title="Age Bracket Distribution by Exam Year",
                    labels={
                        "Count":    "Unique Candidates",
                        "Bracket":  "Age Bracket",
                        "ExamYear": "Exam Year",
                    },
                    color_discrete_sequence=COLOR_PALETTE,
                    category_orders={"Bracket": bracket_order},
                )
                fig2.update_layout(**L)
                fig2.update_xaxes(showgrid=False)
                fig2.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")
                return (fig1, fig2)

            else:
                # No year or state — plain bracket summary
                br_agg = (
                    df2.groupby("Bracket")["Count"].sum()
                    .reindex(bracket_order).dropna().reset_index()
                )
                br_agg.columns = ["Bracket", "Count"]
                br_agg["Pct"]  = (
                    br_agg["Count"] / br_agg["Count"].sum() * 100
                ).round(1)
                fig2 = px.bar(
                    br_agg, x="Bracket", y="Count",
                    title="Candidates by Age Bracket",
                    color="Bracket",
                    color_discrete_sequence=COLOR_PALETTE,
                    text=br_agg["Pct"].astype(str) + "%",
                    category_orders={"Bracket": bracket_order},
                )
                fig2.update_traces(textposition="outside")
                fig2.update_layout(**L)
                fig2.update_xaxes(showgrid=False)
                fig2.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")
                return (fig1, fig2)

        elif analysis == "Age Distribution by Exam Year":
            if "AgeGroup" not in df.columns or "ExamYear" not in df.columns:
                return None
            clean = df[~df["AgeGroup"].isin(["Unknown", None])].copy()
            if clean.empty:
                return None
            fig = px.bar(
                clean, x="ExamYear", y="Count", color="AgeGroup",
                barmode="group",
                title="Age Group Distribution by Exam Year",
                labels={"Count": "Candidates", "ExamYear": "Exam Year",
                        "AgeGroup": "Age Group"},
                color_discrete_sequence=["#1e293b", "#667eea", "#16a34a"],
                text=clean["Count"].apply(lambda x: f"{x:,}"),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5")
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
            
        elif analysis == "Registered vs Sat Candidates":
            if "Status" not in df.columns:
                return None

            sat_statuses = ["Excellent", "Very Good", "Credit", "Pass", "Fail"]

            total_per_year = df.groupby("ExamYear")["Count"].sum().reset_index()
            total_per_year.columns = ["ExamYear", "Total"]

            sat_per_year = df[df["Status"].isin(sat_statuses)].groupby(
                "ExamYear")["Count"].sum().reset_index()
            sat_per_year.columns = ["ExamYear", "Sat"]

            absent_per_year = df[df["Status"] == "Absent"].groupby(
                "ExamYear")["Count"].sum().reset_index()
            absent_per_year.columns = ["ExamYear", "Absent"]

            other_per_year = df[df["Status"].isin(
                ["Cancelled", "Pending", "Withheld"])].groupby(
                "ExamYear")["Count"].sum().reset_index()
            other_per_year.columns = ["ExamYear", "Other"]

            merged = (
                total_per_year
                .merge(sat_per_year,    on="ExamYear", how="left")
                .merge(absent_per_year, on="ExamYear", how="left")
                .merge(other_per_year,  on="ExamYear", how="left")
                .fillna(0)
                .sort_values("ExamYear")
            )

            fig = go.Figure()
            fig.add_bar(
                x=merged["ExamYear"], y=merged["Sat"],
                name="Sat (with result)", marker_color="#16a34a",
                text=merged["Sat"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.add_bar(
                x=merged["ExamYear"], y=merged["Absent"],
                name="Absent", marker_color="#dc2626",
                text=merged["Absent"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.add_bar(
                x=merged["ExamYear"], y=merged["Other"],
                name="Cancelled / Withheld / Pending",
                marker_color="#d97706",
                text=merged["Other"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.update_layout(
                barmode="group",
                title="Registered vs Sat Candidates by Year",
                **L,
            )
            fig.update_xaxes(showgrid=False, title="Exam Year")
            fig.update_yaxes(gridcolor="#f1f3f5", title="Candidates")
            return fig

        elif analysis == "Absenteeism Rate by State":
            if "Status" not in df.columns or "State" not in df.columns:
                return None

            absent_st = df[df["Status"] == "Absent"].groupby(
                "State")["Count"].sum().reset_index()
            absent_st.columns = ["State", "AbsentCount"]

            if absent_st.empty:
                return None

            absent_st = absent_st.sort_values("AbsentCount", ascending=True)

            fig = px.bar(
                absent_st, x="AbsentCount", y="State", orientation="h",
                title="Absent Candidates by State",
                color="AbsentCount",
                color_continuous_scale=["#fef9c3", "#dc2626"],
                text=absent_st["AbsentCount"].apply(lambda x: f"{int(x):,}"),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(**L)
            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(title="Number of Absent Candidates")
            fig.update_yaxes(showgrid=False)
            return fig

        elif analysis == "Absenteeism by Exam Type":
            if "Status" not in df.columns or "ExamType" not in df.columns:
                return None

            absent_et = df[df["Status"] == "Absent"].groupby(
                "ExamType")["Count"].sum().reset_index()
            absent_et.columns = ["ExamType", "AbsentCount"]
            total_et  = df.groupby("ExamType")["Count"].sum().reset_index()
            total_et.columns  = ["ExamType", "Total"]

            merged = total_et.merge(absent_et, on="ExamType", how="left").fillna(0)
            merged["AbsentRate"] = (
                merged["AbsentCount"] / merged["Total"].replace(0, float("nan")) * 100
            ).round(1)

            fig = go.Figure()
            fig.add_bar(
                x=merged["ExamType"], y=merged["Total"],
                name="Total Registered", marker_color="#1e293b",
                text=merged["Total"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.add_bar(
                x=merged["ExamType"], y=merged["AbsentCount"],
                name="Absent", marker_color="#dc2626",
                text=merged["AbsentCount"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.update_layout(
                barmode="group",
                title="Absenteeism by Exam Type",
                **L,
            )
            fig.update_xaxes(showgrid=False, title="Exam Type")
            fig.update_yaxes(gridcolor="#f1f5f9", title="Candidates")
            return fig

        elif analysis == "Absenteeism by Gender":
            if "Status" not in df.columns or "Sex" not in df.columns:
                return None

            absent_sex = df[df["Status"] == "Absent"].groupby(
                "Sex")["Count"].sum().reset_index()
            absent_sex.columns = ["Sex", "AbsentCount"]
            total_sex  = df.groupby("Sex")["Count"].sum().reset_index()
            total_sex.columns  = ["Sex", "Total"]

            merged = total_sex.merge(absent_sex, on="Sex", how="left").fillna(0)
            merged["AbsentRate"] = (
                merged["AbsentCount"] / merged["Total"].replace(0, float("nan")) * 100
            ).round(1)

            fig = go.Figure()
            fig.add_bar(
                x=merged["Sex"], y=merged["Total"],
                name="Total Registered", marker_color="#1e293b",
                text=merged["Total"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.add_bar(
                x=merged["Sex"], y=merged["AbsentCount"],
                name="Absent", marker_color="#dc2626",
                text=merged["AbsentCount"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            )
            fig.update_layout(
                barmode="group",
                title="Absenteeism by Gender",
                **L,
            )
            fig.update_xaxes(showgrid=False, title="Gender")
            fig.update_yaxes(gridcolor="#f1f5f9", title="Candidates")
            return fig

        elif analysis == "Absenteeism Trends Over Time":
            if "Status" not in df.columns or "ExamYear" not in df.columns:
                return None

            total_yr = df.groupby("ExamYear")["Count"].sum().reset_index()
            total_yr.columns = ["ExamYear", "Total"]
            absent_yr = df[df["Status"] == "Absent"].groupby("ExamYear")["Count"].sum().reset_index()
            absent_yr.columns = ["ExamYear", "Absent"]
            
            merged = total_yr.merge(absent_yr, on="ExamYear", how="left").fillna(0)
            merged["AbsentRate"] = (merged["Absent"] / merged["Total"].replace(0, float("nan")) * 100).round(1)
            merged = merged.sort_values("ExamYear")

            fig = go.Figure()

            # 1. THE BAR (Added first so it is in the background)
            fig.add_trace(go.Bar(
                x=merged["ExamYear"],
                y=merged["Absent"],
                name="Absent Count",
                # CHANGES HERE:
                # rgba(217, 119, 6, 0.3) is Orange with 30% opacity
                marker_color="rgba(217, 119, 6, 0.3)", 
                marker_line_color="rgb(217, 119, 6)", # Solid orange border so it looks clean
                marker_line_width=1.5,
                yaxis="y2",
                text=merged["Absent"].apply(lambda x: f"{int(x):,}"),
                textposition="outside",
            ))

            # 2. THE LINE (Added second so it draws ON TOP of the bars)
            fig.add_trace(go.Scatter(
                x=merged["ExamYear"],
                y=merged["AbsentRate"],
                name="Absenteeism Rate (%)",
                mode="lines+markers",
                line=dict(color="#dc2626", width=3), # Solid Red Line
                marker=dict(size=8, line=dict(width=2, color="white")),
                yaxis="y1",
            ))

            fig.update_layout(
                title="Absenteeism Trends: Volume vs. Rate",
                yaxis=dict(
                    title="Absenteeism Rate (%)",
                    ticksuffix="%",
                    range=[0, max(merged["AbsentRate"].max() * 1.3, 10)],
                    showgrid=True,
                    gridcolor="#f1f3f5",
                ),
                yaxis2=dict(
                    title="Absent Candidates",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                ),
                **{k: v for k, v in L.items() if k not in ("yaxis", "yaxis2", "legend")},
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
            )
            fig.update_xaxes(showgrid=False, type='category')
            return fig

        elif analysis == "State Registration Trends":
            if "ExamYear" not in df.columns or "State" not in df.columns:
                return None

            g = df.groupby(["ExamYear", "State"])["Count"].sum().reset_index()
            g["ExamYear"] = g["ExamYear"].astype(int)
            g = g.sort_values("ExamYear")

            fig = px.line(
                g,
                x="ExamYear",
                y="Count",
                color="State",
                markers=True,
                title="Candidate Registration Trends by State Over Time",
                labels={
                    "Count":    "Unique Candidates",
                    "ExamYear": "Exam Year",
                    "State":    "State",
                },
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False, title="Exam Year", dtick=1)
            fig.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")
            return fig

        elif analysis == "State Growth Rate Analysis":
            if "State" not in df.columns or "ExamYear" not in df.columns:
                return None

            df2 = df.copy()
            df2["ExamYear"] = df2["ExamYear"].astype(int)
            df2 = df2.sort_values(["State", "ExamYear"])

            # ── Compute year-on-year growth rate per state ────────────────
            df2["PrevCount"] = df2.groupby("State")["Count"].shift(1)
            df2["GrowthRate"] = (
                (df2["Count"] - df2["PrevCount"])
                / df2["PrevCount"].replace(0, float("nan"))
                * 100
            ).round(2)
            df2 = df2.dropna(subset=["GrowthRate"])

            if df2.empty:
                return None

            # ── Chart 1: Bar chart — overall growth rate by state ─────────
            # Use last available year's growth rate per state as summary
            state_summary = (
                df2.sort_values("ExamYear")
                .groupby("State")
                .last()
                .reset_index()
                [["State", "GrowthRate"]]
                .sort_values("GrowthRate", ascending=True)
            )
            state_summary["Color"] = state_summary["GrowthRate"].apply(
                lambda x: "#16a34a" if x >= 0 else "#dc2626"
            )

            fig1 = px.bar(
                state_summary,
                x="GrowthRate",
                y="State",
                orientation="h",
                title="Registration Growth Rate by State (Most Recent Year)",
                labels={
                    "GrowthRate": "Growth Rate (%)",
                    "State":      "State",
                },
                color="GrowthRate",
                color_continuous_scale=[
                    [0.0, "#dc2626"],
                    [0.5, "#f9fafb"],
                    [1.0, "#16a34a"],
                ],
                text=state_summary["GrowthRate"].apply(lambda x: f"{x:+.1f}%"),
            )
            fig1.update_traces(textposition="outside")
            fig1.update_layout(**L)
            fig1.update_coloraxes(showscale=False)
            fig1.add_vline(x=0, line_dash="dash", line_color="#64748b")
            fig1.update_xaxes(ticksuffix="%", showgrid=False)
            fig1.update_yaxes(showgrid=False)

            # ── Chart 2: Line chart — growth rate over time per state ─────
            fig2 = px.line(
                df2,
                x="ExamYear",
                y="GrowthRate",
                color="State",
                markers=True,
                title="Registration Growth Rate Over Time by State",
                labels={
                    "GrowthRate": "Growth Rate (%)",
                    "ExamYear":   "Exam Year",
                    "State":      "State",
                },
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig2.add_hline(
                y=0, line_dash="dash", line_color="#64748b",
                annotation_text="No growth",
                annotation_position="top right",
            )
            fig2.update_layout(**L)
            fig2.update_xaxes(showgrid=False, dtick=1, title="Exam Year")
            fig2.update_yaxes(
                gridcolor="#f1f3f5",
                ticksuffix="%",
                title="Growth Rate (%)",
            )

            # ── Chart 3: Heatmap table — state × year growth matrix ───────
            pivot = df2.pivot_table(
                index="State",
                columns="ExamYear",
                values="GrowthRate",
                aggfunc="mean",
            ).round(1)

            fig3 = px.imshow(
                pivot,
                title="State × Year Growth Rate Matrix (%)",
                labels={
                    "x":     "Exam Year",
                    "y":     "State",
                    "color": "Growth Rate (%)",
                },
                color_continuous_scale=[
                    [0.0, "#dc2626"],
                    [0.5, "#f9fafb"],
                    [1.0, "#16a34a"],
                ],
                text_auto=".1f",
                aspect="auto",
            )
            fig3.update_layout(**L)
            fig3.update_xaxes(showgrid=False)
            fig3.update_yaxes(showgrid=False)
            fig3.update_coloraxes(colorbar_ticksuffix="%")

            return (fig1, fig2, fig3)

        elif analysis == "Registration Trends & Growth Rate":
            if "ExamYear" not in df.columns or "Count" not in df.columns:
                return None

            df2 = df.copy()
            df2["ExamYear"] = df2["ExamYear"].astype(int)
            df2 = df2.sort_values("ExamYear")

            # Compute year-on-year growth rate
            df2["PrevCount"]  = df2["Count"].shift(1)
            df2["GrowthRate"] = (
                (df2["Count"] - df2["PrevCount"])
                / df2["PrevCount"].replace(0, float("nan"))
                * 100
            ).round(2)

            # ── Chart 1: Line chart — total registration by year ──────────
            fig1 = px.line(
                df2,
                x="ExamYear",
                y="Count",
                markers=True,
                title="Total Candidate Registration by Exam Year",
                labels={
                    "Count":    "Unique Candidates",
                    "ExamYear": "Exam Year",
                },
                color_discrete_sequence=[COLOR_PALETTE[0]],
            )
            fig1.update_layout(**L)
            fig1.update_xaxes(showgrid=False, dtick=1, title="Exam Year")
            fig1.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")

            # ── Chart 2: Bar chart — year-on-year growth % ────────────────
            df_growth = df2.dropna(subset=["GrowthRate"]).copy()
            df_growth["Color"] = df_growth["GrowthRate"].apply(
                lambda x: "#16a34a" if x >= 0 else "#dc2626"
            )

            fig2 = px.bar(
                df_growth,
                x="ExamYear",
                y="GrowthRate",
                title="Year-on-Year Registration Growth Rate (%)",
                labels={
                    "GrowthRate": "Growth Rate (%)",
                    "ExamYear":   "Exam Year",
                },
                color="GrowthRate",
                color_continuous_scale=[
                    [0.0, "#dc2626"],
                    [0.5, "#f9fafb"],
                    [1.0, "#16a34a"],
                ],
                text=df_growth["GrowthRate"].apply(lambda x: f"{x:+.1f}%"),
            )
            fig2.add_hline(
                y=0, line_dash="dash", line_color="#64748b",
                annotation_text="No change",
                annotation_position="top right",
            )
            fig2.update_traces(textposition="outside")
            fig2.update_layout(**L)
            fig2.update_coloraxes(showscale=False)
            fig2.update_xaxes(showgrid=False, dtick=1, title="Exam Year")
            fig2.update_yaxes(ticksuffix="%", gridcolor="#f1f3f5")

            return (fig1, fig2)

        elif analysis == "Registration by Exam Type":
            if "ExamYear" not in df.columns or "ExamType" not in df.columns:
                return None

            df2 = df.copy()
            df2["ExamYear"] = df2["ExamYear"].astype(int)
            df2 = df2.sort_values("ExamYear")

            # ── Chart 1: Stacked bar — registration by exam type per year ─
            fig1 = px.bar(
                df2,
                x="ExamYear",
                y="Count",
                color="ExamType",
                barmode="stack",
                title="Total Registration by Exam Type per Year",
                labels={
                    "Count":    "Unique Candidates",
                    "ExamYear": "Exam Year",
                    "ExamType": "Exam Type",
                },
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig1.update_layout(**L)
            fig1.update_xaxes(showgrid=False, dtick=1, title="Exam Year")
            fig1.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")

            # ── Chart 2: Line chart — registration trend by exam type ─────
            fig2 = px.line(
                df2,
                x="ExamYear",
                y="Count",
                color="ExamType",
                markers=True,
                title="Registration Trend by Exam Type Over Time",
                labels={
                    "Count":    "Unique Candidates",
                    "ExamYear": "Exam Year",
                    "ExamType": "Exam Type",
                },
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig2.update_layout(**L)
            fig2.update_xaxes(showgrid=False, dtick=1, title="Exam Year")
            fig2.update_yaxes(gridcolor="#f1f3f5", title="Unique Candidates")

            return (fig1, fig2)

        elif "Registration" in analysis or "Enrollment" in analysis:
            if "ExamYear" not in df.columns:
                return None
            if "State" in df.columns:
                g = df.groupby(["ExamYear", "State"])["Count"].sum().reset_index()
                fig = px.line(
                    g, x="ExamYear", y="Count", color="State",
                    markers=True,
                    title="Registration Trend by State",
                    color_discrete_sequence=COLOR_PALETTE,
                )
            else:
                g = df.groupby("ExamYear")["Count"].sum().reset_index()
                fig = px.line(
                    g, x="ExamYear", y="Count",
                    markers=True,
                    title="Registration Trend",
                    color_discrete_sequence=[COLOR_PALETTE[0]],
                )
            fig.update_layout(**L)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="#f1f3f5")
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
            
        # CANDIDATE LOAD PER CENTRE — horizontal bar chart
        elif analysis == "Candidate Load per Centre":
            if "centre" not in df.columns or "CandidateLoad" not in df.columns:
                return None

            top_n     = int(filters.get("TopN", 10))
            direction = filters.get("LoadDirection", "Highest")

            df = df.copy()
            df["CentreLabel"] = (
                df["centre"].astype(str)
                + " (" + df["State"].astype(str) + ")"
            )

            if "Both" in direction and "RankGroup" in df.columns:
                # Two charts — one for highest, one for lowest
                top_df = df[df["RankGroup"].str.startswith("Highest")].sort_values(
                    "CandidateLoad", ascending=True
                )
                bot_df = df[df["RankGroup"].str.startswith("Lowest")].sort_values(
                    "CandidateLoad", ascending=False
                )

                fig1 = px.bar(
                    top_df, x="CandidateLoad", y="CentreLabel",
                    orientation="h",
                    title=f"Highest {top_n} Centres by Candidate Load",
                    color="CandidateLoad",
                    color_continuous_scale=["#fef9c3", "#dc2626"],
                    text=top_df["CandidateLoad"].apply(lambda x: f"{int(x):,}"),
                    labels={"CandidateLoad": "Unique Candidates",
                            "CentreLabel":   "Centre"},
                )
                fig1.update_traces(textposition="outside")
                fig1.update_layout(**L)
                fig1.update_coloraxes(showscale=False)
                fig1.update_xaxes(showgrid=False)
                fig1.update_yaxes(showgrid=False)

                fig2 = px.bar(
                    bot_df, x="CandidateLoad", y="CentreLabel",
                    orientation="h",
                    title=f"Lowest {top_n} Centres by Candidate Load",
                    color="CandidateLoad",
                    color_continuous_scale=["#dcfce7", "#16a34a"],
                    text=bot_df["CandidateLoad"].apply(lambda x: f"{int(x):,}"),
                    labels={"CandidateLoad": "Unique Candidates",
                            "CentreLabel":   "Centre"},
                )
                fig2.update_traces(textposition="outside")
                fig2.update_layout(**L)
                fig2.update_coloraxes(showscale=False)
                fig2.update_xaxes(showgrid=False)
                fig2.update_yaxes(showgrid=False)

                return (fig1, fig2)

            else:
                is_highest = "Lowest" not in direction
                df_sorted  = df.sort_values(
                    "CandidateLoad", ascending=not is_highest
                )
                color_scale = (
                    ["#fef9c3", "#dc2626"] if is_highest
                    else ["#dcfce7", "#16a34a"]
                )
                title = (
                    f"{'Highest' if is_highest else 'Lowest'} "
                    f"{top_n} Centres by Candidate Load"
                )
                fig = px.bar(
                    df_sorted.sort_values("CandidateLoad", ascending=True),
                    x="CandidateLoad", y="CentreLabel",
                    orientation="h",
                    title=title,
                    color="CandidateLoad",
                    color_continuous_scale=color_scale,
                    text=df_sorted.sort_values(
                        "CandidateLoad", ascending=True
                    )["CandidateLoad"].apply(lambda x: f"{int(x):,}"),
                    labels={"CandidateLoad": "Unique Candidates",
                            "CentreLabel":   "Centre"},
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(**L)
                fig.update_coloraxes(showscale=False)
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(showgrid=False)
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


# Added a helper to render the structured dict
def render_narrative(narrative: dict) -> None:
    """Renders a structured narrative dict as a professional insight panel."""

    if isinstance(narrative, str):
        # Legacy fallback — plain string
        st.markdown(
            f'<div class="narrative-box">{narrative}</div>',
            unsafe_allow_html=True,
        )
        return

    def bullet_html(items: list, color: str = "#1e293b") -> str:
        if not items:
            return ""
        rows = "".join(
            f'<li style="margin-bottom:6px;color:{color};">{item}</li>'
            for item in items
        )
        return f'<ul style="margin:0;padding-left:1.2rem;">{rows}</ul>'

    section_style = (
        "margin-bottom:1.2rem;"
        "padding:1rem 1.2rem;"
        "border-radius:10px;"
        "font-family:'DM Sans',sans-serif;"
    )

    html = '<div style="font-family:\'DM Sans\',sans-serif;">'

    # ── Executive Summary ────────────────────────────────────────────────────
    if narrative.get("summary"):
        html += f"""
        <div style="{section_style}background:#f0f4ff;border-left:4px solid #2563eb;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                        text-transform:uppercase;color:#2563eb;margin-bottom:6px;">
                Executive Summary
            </div>
            <div style="font-size:0.93rem;color:#1e293b;line-height:1.7;">
                {narrative['summary']}
            </div>
        </div>
        """

    # ── Key Findings ─────────────────────────────────────────────────────────
    if narrative.get("key_findings"):
        html += f"""
        <div style="{section_style}background:#f0fdf4;border-left:4px solid #16a34a;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                        text-transform:uppercase;color:#16a34a;margin-bottom:8px;">
                Key Findings
            </div>
            {bullet_html(narrative['key_findings'], "#166534")}
        </div>
        """

    # ── Observations ─────────────────────────────────────────────────────────
    if narrative.get("observations"):
        html += f"""
        <div style="{section_style}background:#fafafa;border-left:4px solid #64748b;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                        text-transform:uppercase;color:#64748b;margin-bottom:8px;">
                Observations
            </div>
            {bullet_html(narrative['observations'], "#374151")}
        </div>
        """

    # ── Business Implications ─────────────────────────────────────────────────
    if narrative.get("implications"):
        html += f"""
        <div style="{section_style}background:#fffbeb;border-left:4px solid #d97706;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                        text-transform:uppercase;color:#d97706;margin-bottom:8px;">
                Business Implications
            </div>
            {bullet_html(narrative['implications'], "#92400e")}
        </div>
        """

    # ── Recommendations ───────────────────────────────────────────────────────
    if narrative.get("recommendations"):
        html += f"""
        <div style="{section_style}background:#fdf4ff;border-left:4px solid #9333ea;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;
                        text-transform:uppercase;color:#9333ea;margin-bottom:8px;">
                Recommendations
            </div>
            {bullet_html(narrative['recommendations'], "#581c87")}
        </div>
        """

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
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

    # KPI CARDS FOR STATE GROWTH RATE ANALYSIS
    # ── KPI cards for State Registration Growth Rate Analysis ──────────────────
    if analysis == "State Growth Rate Analysis" and df is not None and not df.empty:
            try:
                df_kpi = df.copy()
                df_kpi["ExamYear"]   = df_kpi["ExamYear"].astype(int)
                df_kpi = df_kpi.sort_values(["State", "ExamYear"])
                df_kpi["PrevCount"]  = df_kpi.groupby("State")["Count"].shift(1)
                df_kpi["GrowthRate"] = (
                    (df_kpi["Count"] - df_kpi["PrevCount"])
                    / df_kpi["PrevCount"].replace(0, float("nan"))
                    * 100
                ).round(2)
                df_kpi = df_kpi.dropna(subset=["GrowthRate"])

                if not df_kpi.empty:
                    overall_g  = round(float(df_kpi["GrowthRate"].mean()), 1)
                    state_avg  = df_kpi.groupby("State")["GrowthRate"].mean()
                    fast_state = state_avg.idxmax()
                    fast_rate  = round(float(state_avg.max()), 1)
                    high_idx   = df_kpi["GrowthRate"].idxmax()
                    high_state = df_kpi.loc[high_idx, "State"]
                    high_yr    = int(df_kpi.loc[high_idx, "ExamYear"])
                    high_rate  = round(float(df_kpi.loc[high_idx, "GrowthRate"]), 1)
                    dec_state  = state_avg.idxmin()
                    dec_rate   = round(float(state_avg.min()), 1)

                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric(
                        "Overall Avg Growth",
                        f"{overall_g:+.1f}%",
                        help="Average year-on-year growth across all selected states",
                    )
                    k2.metric(
                        "Fastest Growing State",
                        fast_state,
                        f"{fast_rate:+.1f}% avg/year",
                        help="State with highest average annual growth rate",
                    )
                    k3.metric(
                        f"Peak Growth — {high_yr}",
                        high_state,
                        f"{high_rate:+.1f}% that year",
                        help="State and year with the single highest growth rate",
                    )
                    k4.metric(
                        "Largest Decline",
                        dec_state,
                        f"{dec_rate:+.1f}% avg/year",
                        delta_color="inverse",
                        help="State with the largest average annual decline",
                    )
                    st.markdown("---")
            except Exception:
                pass


    if analysis == "Registration Trends & Growth Rate" and df is not None and not df.empty:
            try:
                df_kpi = df.copy()
                df_kpi["ExamYear"] = df_kpi["ExamYear"].astype(int)
                df_kpi = df_kpi.sort_values("ExamYear")
                df_kpi["PrevCount"]  = df_kpi["Count"].shift(1)
                df_kpi["GrowthRate"] = (
                    (df_kpi["Count"] - df_kpi["PrevCount"])
                    / df_kpi["PrevCount"].replace(0, float("nan"))
                    * 100
                ).round(2)

                total_cands  = int(df_kpi["Count"].sum())
                latest_row   = df_kpi.iloc[-1]
                latest_yr    = int(latest_row["ExamYear"])
                latest_g     = latest_row["GrowthRate"]
                latest_g_str = f"{latest_g:+.1f}%" if pd.notna(latest_g) else "N/A"
                peak_row     = df_kpi.loc[df_kpi["Count"].idxmax()]
                peak_yr      = int(peak_row["ExamYear"])
                peak_ct      = int(peak_row["Count"])
                low_row      = df_kpi.loc[df_kpi["Count"].idxmin()]
                low_yr       = int(low_row["ExamYear"])
                low_ct       = int(low_row["Count"])

                k1, k2, k3, k4 = st.columns(4)
                k1.metric(
                    "Total Candidates",
                    f"{total_cands:,}",
                    help="Sum of unique candidates across all selected years",
                )
                k2.metric(
                    f"Growth Rate ({latest_yr})",
                    latest_g_str,
                    help=f"Year-on-year growth rate in {latest_yr}",
                )
                k3.metric(
                    "Highest Registration Year",
                    str(peak_yr),
                    f"{peak_ct:,} candidates",
                    help="Year with the most unique candidates registered",
                )
                k4.metric(
                    "Lowest Registration Year",
                    str(low_yr),
                    f"{low_ct:,} candidates",
                    delta_color="inverse",
                    help="Year with the fewest unique candidates registered",
                )
                st.markdown("---")
            except Exception:
                pass        


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
    render_narrative(narrative)

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
            st.plotly_chart(fig, key=f"chart_{idx}_{chart_idx}", use_container_width=True, config={"displayModeBar": False})
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
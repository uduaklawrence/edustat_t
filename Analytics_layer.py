"""
Analytics_layer.py
──────────────────────────────────────────────────────────────────────────────
This module serves as the data access layer for the Streamlit dashboard."""

import duckdb
import pandas as pd
from pathlib import Path
import streamlit as st

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
PARQUET_FOLDER = Path(r"C:\Users\uludoh\Documents\DB-PARQUET\chunks_data")
PARQUET_GLOB   = str(PARQUET_FOLDER / "**" / "*.parquet").replace("\\", "/")

DASHBOARD_RECENT_YEARS = 2


# ── DUCKDB CONNECTION ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_conn():
    conn = duckdb.connect()
    conn.execute("SET memory_limit='3GB';")
    conn.execute("SET threads=4;")
    print("DuckDB connection ready")
    return conn


# ── HELPER: resolve most-recent years ─────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def _get_recent_years(n: int = DASHBOARD_RECENT_YEARS) -> list:
    _check_folder()
    conn = _get_conn()
    rows = conn.execute(f"""
        SELECT DISTINCT TRY_CAST(ExamYear AS INTEGER) AS yr
        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
        WHERE yr IS NOT NULL
        ORDER BY yr DESC
        LIMIT {n}
    """).fetchall()
    return sorted([int(r[0]) for r in rows])


# ── 1a. DASHBOARD KPIs ────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading dashboard KPIs...", ttl=3600)
def get_dashboard_kpis() -> dict:
    try:
        _check_folder()
        conn         = _get_conn()
        recent_years = _get_recent_years()
        years_sql    = ", ".join(str(y) for y in recent_years)

        row = conn.execute(f"""
            SELECT
                COUNT(*)                                                AS total,
                COUNT(*) FILTER (WHERE LOWER(Sex) = 'male')            AS males,
                COUNT(*) FILTER (WHERE LOWER(Sex) = 'female')          AS females,
                COUNT(*) FILTER (WHERE Disability = 'Present')         AS disabled
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            WHERE TRY_CAST(ExamYear AS INTEGER) IN ({years_sql})
        """).fetchone()

        return {
            "total_candidates": int(row[0]),
            "male_count":       int(row[1]),
            "female_count":     int(row[2]),
            "disability_count": int(row[3]),
        }
    except FileNotFoundError as e:
        st.error(f"❌ {e}")
        return {"total_candidates": 0, "male_count": 0,
                "female_count": 0, "disability_count": 0}
    except Exception as e:
        st.error(f"❌ KPI load failed: {e}")
        return {"total_candidates": 0, "male_count": 0,
                "female_count": 0, "disability_count": 0}


# ── 1b. YEARLY CHART DATA ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_dashboard_yearly_chart() -> pd.DataFrame:
    try:
        _check_folder()
        conn         = _get_conn()
        recent_years = _get_recent_years()
        years_sql    = ", ".join(str(y) for y in recent_years)

        df = conn.execute(f"""
            SELECT TRY_CAST(ExamYear AS INTEGER) AS ExamYear, COUNT(*) AS Count
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            WHERE TRY_CAST(ExamYear AS INTEGER) IN ({years_sql})
            GROUP BY ExamYear ORDER BY ExamYear
        """).df()

        df["ExamYear"] = df["ExamYear"].astype(int)
        return df
    except Exception as e:
        st.error(f"❌ Yearly chart load failed: {e}")
        return pd.DataFrame(columns=["ExamYear", "Count"])


# ── 1c. GENDER CHART DATA ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_dashboard_gender_chart() -> pd.DataFrame:
    try:
        _check_folder()
        conn         = _get_conn()
        recent_years = _get_recent_years()
        years_sql    = ", ".join(str(y) for y in recent_years)

        df = conn.execute(f"""
            SELECT Sex, COUNT(*) AS Count
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            WHERE TRY_CAST(ExamYear AS INTEGER) IN ({years_sql}) AND Sex IS NOT NULL
            GROUP BY Sex ORDER BY Sex
        """).df()
        return df
    except Exception as e:
        st.error(f"❌ Gender chart load failed: {e}")
        return pd.DataFrame(columns=["Sex", "Count"])


# ── 1d. TOP CENTRES ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_dashboard_top_centres(top_n: int = 5) -> pd.DataFrame:
    try:
        _check_folder()
        conn         = _get_conn()
        recent_years = _get_recent_years()
        years_sql    = ", ".join(str(y) for y in recent_years)

        df = conn.execute(f"""
            SELECT centre, State, COUNT(*) AS "Registered Candidates"
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            WHERE TRY_CAST(ExamYear AS INTEGER) IN ({years_sql}) AND centre IS NOT NULL
            GROUP BY centre, State
            ORDER BY "Registered Candidates" DESC
            LIMIT {top_n}
        """).df()

        df.index = range(1, len(df) + 1)
        return df
    except Exception as e:
        st.error(f"❌ Top centres load failed: {e}")
        return pd.DataFrame(columns=["centre", "State", "Registered Candidates"])


# ── 1e. STATE SUMMARY ─────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_dashboard_state_summary() -> pd.DataFrame:
    try:
        _check_folder()
        conn         = _get_conn()
        recent_years = _get_recent_years()
        years_sql    = ", ".join(str(y) for y in recent_years)

        df = conn.execute(f"""
            SELECT TRY_CAST(ExamYear AS INTEGER) AS ExamYear, State,
                   COUNT(*) AS NumberOfCandidates
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            WHERE TRY_CAST(ExamYear AS INTEGER) IN ({years_sql}) AND State IS NOT NULL
            GROUP BY ExamYear, State ORDER BY ExamYear, State
        """).df()

        df["ExamYear"] = df["ExamYear"].astype(int)
        return df
    except Exception as e:
        st.error(f"❌ State summary load failed: {e}")
        return pd.DataFrame(columns=["ExamYear", "State", "NumberOfCandidates"])


# ── TOP / BOTTOM STATES ───────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_top_bottom_states(exam_years: tuple = (), top_n: int = 5) -> dict:
    try:
        _check_folder()
        conn  = _get_conn()
        where = ""
        if exam_years:
            joined = ", ".join(str(int(y)) for y in exam_years)
            where  = f"WHERE TRY_CAST(ExamYear AS INTEGER) IN ({joined})"

        df = conn.execute(f"""
            SELECT State, COUNT(*) AS Candidates
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            {where}
            GROUP BY State ORDER BY Candidates DESC
        """).df()

        if df.empty:
            return {"top": [], "bottom": [], "all_ranked": df}

        return {
            "top":        df.head(top_n)["State"].tolist(),
            "bottom":     df.tail(top_n)["State"].tolist(),
            "all_ranked": df,
        }
    except Exception as e:
        st.error(f"❌ Top/Bottom states failed: {e}")
        return {"top": [], "bottom": [], "all_ranked": pd.DataFrame()}


# ── LEGACY SHIM ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading dashboard data...", ttl=3600)
def get_exam_dataset() -> pd.DataFrame:
    try:
        _check_folder()
        conn         = _get_conn()
        recent_years = _get_recent_years()
        years_sql    = ", ".join(str(y) for y in recent_years)

        df = conn.execute(f"""
            SELECT TRY_CAST(ExamYear AS INTEGER) AS ExamYear,
                   State, Sex, Disability, centre, COUNT(*) AS n
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            WHERE TRY_CAST(ExamYear AS INTEGER) IN ({years_sql})
            GROUP BY ExamYear, State, Sex, Disability, centre
            ORDER BY ExamYear
        """).df()

        df["ExamYear"] = df["ExamYear"].astype(int)
        return df
    except Exception as e:
        st.error(f"❌ Dashboard data load failed: {e}")
        return pd.DataFrame()


# ── 2. RECORD COUNT (used by configure_filters for invoice validation) ─────────
@st.cache_data(show_spinner="Counting matching records...", ttl=1800)
def get_record_count(
    exam_years : tuple = (),
    states     : tuple = (),
    sex        : tuple = (),
    disability : tuple = (),
    sponsor    : tuple = (),
    age_groups : tuple = (),
    centres    : tuple = (),
    exam_types : tuple = (),
    subjects   : tuple = (),
    grades     : tuple = (),
    statuses   : tuple = (),
) -> int:
    """
    Fast COUNT(*) only — no raw data enters Python RAM.
    Used on the configure_filters page to show how many records
    a report will cover, and to validate that filters return data.
    When all filters are empty (Select All), counts the full dataset.
    """
    try:
        _check_folder()
        conn    = _get_conn()
        clauses = _build_where(
            exam_years, states, sex, disability, (), sponsor,
            age_groups, centres, exam_types, subjects, grades, statuses,
        )
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            {where}
        """).fetchone()
        return int(row[0]) if row else 0

    except Exception as e:
        st.error(f"❌ Record count failed: {e}")
        return 0


# ── 3. FILTERED QUERY (only used when raw rows are genuinely needed) ───────────
@st.cache_data(show_spinner="Fetching filtered data...", ttl=1800)
def query_exam_data(
    exam_years : tuple = (),
    states     : tuple = (),
    sex        : tuple = (),
    disability : tuple = (),
    origin     : tuple = (),
    sponsor    : tuple = (),
    age_groups : tuple = (),
    centres    : tuple = (),
    exam_types : tuple = (),
    subjects   : tuple = (),
    grades     : tuple = (),
    statuses   : tuple = (),
) -> pd.DataFrame:
    """
    Returns raw rows. Use get_record_count() on the filter page instead —
    this function is for report rendering pages that need actual data.
    union_by_name=True fixes DATE→NULL cast errors across mixed-schema files.
    """
    try:
        _check_folder()
        conn    = _get_conn()
        clauses = _build_where(
            exam_years, states, sex, disability, origin, sponsor,
            age_groups, centres, exam_types, subjects, grades, statuses,
        )
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        df = conn.execute(f"""
            SELECT *
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            {where}
        """).df()

        if "ExamYear" in df.columns:
            df["ExamYear"] = pd.to_numeric(df["ExamYear"], errors="coerce")
            df = df.dropna(subset=["ExamYear"])
            df["ExamYear"] = df["ExamYear"].astype(int)

        print(f"query_exam_data: {len(df):,} rows | clauses → {clauses}")
        return df

    except Exception as e:
        st.error(f"❌ Query failed: {e}")
        return pd.DataFrame()


# ── 4. FILTER DROPDOWN OPTIONS ────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=86400)
def get_filter_options() -> dict:
    try:
        _check_folder()
        conn = _get_conn()

        # Origin intentionally excluded — all Origin-based reports removed
        columns = [
            "ExamYear", "Sex", "State",
            "AgeGroup", "Disability", "Sponsor", "centre",
            "ExamType", "Subject", "Grade", "Status",
        ]

        options: dict = {}

        for col in columns:
            try:
                if col == "ExamYear":
                    rows = conn.execute(f"""
                        SELECT DISTINCT TRY_CAST(ExamYear AS INTEGER) AS ExamYear
                        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
                        WHERE TRY_CAST(ExamYear AS INTEGER) IS NOT NULL
                        ORDER BY ExamYear
                    """).fetchall()
                    options[col] = [int(r[0]) for r in rows if r[0] is not None]
                else:
                    rows = conn.execute(f"""
                        SELECT DISTINCT {col}
                        FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
                        WHERE {col} IS NOT NULL
                        ORDER BY {col}
                    """).fetchall()
                    options[col] = [r[0] for r in rows]
            except Exception:
                options[col] = []

        print(f"Filter options ready — {sum(len(v) for v in options.values())} total values")
        return options

    except Exception as e:
        st.error(f"❌ Could not load filter options: {e}")
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# 5. AGGREGATED QUERY — PRIMARY DATA SOURCE FOR view_report.py
# ══════════════════════════════════════════════════════════════════════════════
#
# WHY THIS EXISTS:
#   view_report.py previously called query_exam_data() which returns SELECT *
#   (all raw rows). With 178M records and "ExamType: All" selected, this
#   transferred ~178M rows into Python RAM → Out of Memory crash.
#
# HOW IT WORKS:
#   This function accepts a list of column names to GROUP BY, plus the same
#   filter parameters as every other function in this file.
#   It runs entirely inside DuckDB:
#
#       SELECT ExamYear, Sex, COUNT(*) AS Count
#       FROM parquet files
#       WHERE ExamYear IN (2000, 2001, ...)   ← only if filters were set
#       GROUP BY ExamYear, Sex
#       ORDER BY ExamYear, Sex
#
#   The result is a tiny DataFrame — one row per unique combination of the
#   group_by_cols values. For example, grouping by ["ExamYear", "Sex"] across
#   6 years with 2 genders returns exactly 12 rows, not 85 million.
#
# WHAT view_report.py DOES WITH IT:
#   - build_chart() receives the aggregated df and plots the "Count" column
#     directly. No further .groupby() needed in Python.
#   - generate_narrative() reads summary stats from the Count column.
#   - KPI boxes read female count, top state, etc. from the aggregated df.
#
# EXAMPLE RETURN — group_by_cols=["ExamType"], no filters:
#
#     ExamType    | Count
#     Private     | 83,201,797
#     School      | 95,402,111
#
#   That is 2 rows in Python RAM, not 178 million.
#
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner="Loading report data...", ttl=1800)
def query_aggregated_data(
    group_by_cols : tuple,        # e.g. ("ExamYear", "Sex")
    exam_years    : tuple = (),
    states        : tuple = (),
    sex           : tuple = (),
    disability    : tuple = (),
    sponsor       : tuple = (),
    age_groups    : tuple = (),
    centres       : tuple = (),
    exam_types    : tuple = (),
    subjects      : tuple = (),
    grades        : tuple = (),
    statuses      : tuple = (),
) -> pd.DataFrame:
    """
    Runs a GROUP BY aggregation inside DuckDB and returns a small summary
    DataFrame. Never loads raw rows into Python.

    Parameters
    ----------
    group_by_cols : tuple of str
        Column names to group by. Must be valid column names in the parquet
        files, e.g. ("ExamYear", "Sex") or ("ExamType",) or ("State", "Grade").
        Passed as a tuple (not list) so Streamlit can hash it for caching.

    exam_years, states, sex, ... : tuple
        Same filter parameters as get_record_count() and query_exam_data().
        Empty tuple = no filter on that column (include all values).

    Returns
    -------
    pd.DataFrame
        Columns: the requested group_by_cols + "Count".
        Rows: one per unique combination of group_by values that exists in
        the filtered dataset.

    Notes
    -----
    - ExamYear is cast with TRY_CAST to INTEGER, matching existing patterns.
    - If group_by_cols is empty or invalid, returns an empty DataFrame.
    - The @st.cache_data decorator caches results for 30 minutes, so
      repeated renders of the same report (e.g. PDF generation) do not
      re-query DuckDB.
    """
    # ── Guard: need at least one column to group by ───────────────────────────
    if not group_by_cols:
        return pd.DataFrame(columns=["Count"])

    try:
        _check_folder()
        conn = _get_conn()

        # ── Build WHERE clause using the existing _build_where helper ─────────
        # _build_where expects origin as positional arg 5 — pass empty tuple.
        clauses = _build_where(
            exam_years, states, sex, disability, (), sponsor,
            age_groups, centres, exam_types, subjects, grades, statuses,
        )
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        # ── Build SELECT list ─────────────────────────────────────────────────
        # ExamYear needs TRY_CAST to INTEGER so it matches the int type used
        # everywhere else (charts, narrative comparisons, sorting).
        # All other columns are selected as-is.
        select_parts = []
        group_parts  = []

        for col in group_by_cols:
            if col == "ExamYear":
                # Cast to integer and alias back to ExamYear
                select_parts.append("TRY_CAST(ExamYear AS INTEGER) AS ExamYear")
                group_parts.append("TRY_CAST(ExamYear AS INTEGER)")
            else:
                select_parts.append(col)
                group_parts.append(col)

        select_sql = ", ".join(select_parts)
        group_sql  = ", ".join(group_parts)
        order_sql  = group_sql   # ORDER BY same columns for consistent output

        sql = f"""
            SELECT {select_sql}, COUNT(*) AS Count
            FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=true, union_by_name=true)
            {where}
            GROUP BY {group_sql}
            ORDER BY {order_sql}
        """

        df = conn.execute(sql).df()

        # ── Post-process ExamYear to plain int if present ─────────────────────
        if "ExamYear" in df.columns:
            df["ExamYear"] = pd.to_numeric(df["ExamYear"], errors="coerce")
            df = df.dropna(subset=["ExamYear"])
            df["ExamYear"] = df["ExamYear"].astype(int)

        print(
            f"query_aggregated_data: group_by={group_by_cols} | "
            f"{len(df)} result rows | clauses → {clauses}"
        )
        return df

    except Exception as e:
        st.error(f"❌ Aggregated query failed: {e}")
        # Return empty DataFrame with expected columns so callers don't crash
        return pd.DataFrame(columns=list(group_by_cols) + ["Count"])


# ── INTERNAL HELPERS ───────────────────────────────────────────────────────────

def _check_folder():
    if not PARQUET_FOLDER.exists():
        raise FileNotFoundError(
            f"Parquet folder not found:\n  {PARQUET_FOLDER}\n"
            "Check PARQUET_FOLDER in Analytics_layer.py"
        )
    if not any(PARQUET_FOLDER.rglob("*.parquet")):
        raise FileNotFoundError(
            f"No .parquet files found in:\n  {PARQUET_FOLDER}\n"
            "Make sure extraction is complete."
        )


def _build_where(
    exam_years, states, sex, disability,
    origin, sponsor, age_groups, centres,
    exam_types=(), subjects=(), grades=(), statuses=(),
) -> list:
    clauses: list = []

    def add(col: str, vals: tuple):
        if not vals:
            return
        if vals and isinstance(vals[0], (int, float)):
            joined = ", ".join(str(v) for v in vals)
        else:
            joined = ", ".join(
                f"'{str(v).replace(chr(39), chr(39)*2)}'" for v in vals
            )
        clauses.append(f"{col} IN ({joined})")

    if exam_years:
        joined = ", ".join(str(int(v)) for v in exam_years)
        clauses.append(f"TRY_CAST(ExamYear AS INTEGER) IN ({joined})")

    add("State",      states)
    add("Sex",        sex)
    add("Disability", disability)
    add("Origin",     origin)
    add("Sponsor",    sponsor)
    add("AgeGroup",   age_groups)
    add("centre",     centres)
    add("ExamType",   exam_types)
    add("Subject",    subjects)
    add("Grade",      grades)
    add("Status",     statuses)

    return clauses
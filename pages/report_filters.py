import streamlit as st
import sys
from pathlib import Path

# -------------------- AUTH CHECK --------------------
try:
    sys.path.append(str(Path(__file__).parent.parent))
    from auth_utils import require_authentication
    require_authentication()
except ImportError:
    if not st.session_state.get("logged_in", False):
        st.warning("Please sign in to view the report.")
        st.stop()

st.set_page_config(page_title="Select Filter Group", layout="wide")

with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
    .breadcrumb { font-size: 14px; color: var(--text-secondary); margin-bottom: 24px; }
    .breadcrumb a { color: var(--text-secondary); text-decoration: none; }
    .breadcrumb a:hover { color: var(--primary-blue); }
    .filter-group-header { margin-bottom: 32px; }
    .filter-group-title {
        font-size: 32px; font-weight: 700;
        color: var(--text-primary); margin-bottom: 12px;
    }
    .filter-group-subtitle {
        font-size: 16px; color: var(--text-secondary);
        line-height: 1.6; max-width: 900px;
    }
    .analysis-card {
        background: white; border-radius: 12px; padding: 28px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
        display: flex; flex-direction: column; min-height: 240px;
    }
    .analysis-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-4px);
        border-color: var(--accent-blue);
    }
    .analysis-card-title {
        font-size: 19px; font-weight: 700;
        color: var(--text-primary); margin-bottom: 16px;
        min-height: 50px; display: flex; align-items: center;
    }
    .analysis-card-description {
        color: var(--text-secondary); font-size: 14px;
        line-height: 1.6; flex-grow: 1; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- GUARD --------------------
if not st.session_state.get("selected_subgroup"):
    st.error("❌ No subgroup selected. Please go back and select a report type.")
    if st.button("← Go Back"):
        st.switch_page("pages/create_report.py")
    st.stop()

selected_main_group = st.session_state.get("selected_main_group", "")
selected_subgroup   = st.session_state.get("selected_subgroup", "")

analysis_options = {

    # ── GROUP 1: DEMOGRAPHIC ANALYSIS ────────────────────────────────────────
    "Age Distribution & Group Segmentation": {
        "options": [
            (
                "Age Range of Candidates",
                "View the full spread of candidate ages, identifying the youngest, "
                "oldest and most dominant age brackets across the dataset.",
            ),
            (
                "Age Distribution by Exam Year",
                "Analyse how candidate age groups are distributed across different "
                "examination years, revealing shifts in enrollment demographics over time.",
            ),
            (
                "Generational Education Trends",
                "Compare educational participation patterns across different birth "
                "generations to identify long-term demographic shifts.",
            ),
        ]
    },
    "Gender Equity Analysis": {
        "options": [
            (
                "Male-to-Female Ratio Overview",
                "Calculate overall gender balance across the full dataset and "
                "identify where disparities are most pronounced.",
            ),
            (
                "Gender Balance by Exam Year",
                "Track how the male-to-female ratio changes across examination years "
                "to identify improving or worsening gender equity. Visualise historical gender equity patterns and track whether "
                "the system is becoming more or less balanced over time.",
            ),
            (
                "Gender Distribution by State & Centre",
                "Compare gender representation across states and examination centres "
                "to reveal geographic gender gaps.",
            ),
            ]
    },
    "Birth Cohort Analysis": {
        "options": [
            (
                "Age-Appropriate Enrollment Assessment",
                "Assess whether candidates are enrolling at suitable ages relative "
                "to their birth year, flagging over-age and under-age patterns.",
            ),
            (
                "Cohort Tracking Across Years",
                "Follow specific birth cohorts through examination years to detect "
                "re-sitting patterns and delayed progression.",
            ),
        ]
    },
    "Disability & Special Needs Profile": {
        "options": [
            (
                "Disability Inclusion Rate",
                "Calculate the percentage of candidates registered with a disability "
                "or special need across the full dataset.",
            ),
            (
                "Disability Trends by Exam Year",
                "Track how disability inclusion rates change over time to measure "
                "progress toward inclusive education.",
            ),
            (
                "Disability by Gender & Age Group",
                "Analyse disability representation across gender and age group "
                "dimensions to understand intersectional patterns.",
            ),
            (
                "Regional Disability Patterns",
                "Compare disability registration rates across different states and "
                "regions to identify areas of low inclusion.",
            ),
        ]
    },

    # ── GROUP 2: GEOGRAPHIC & REGIONAL ANALYSIS ───────────────────────────────
    "Centre Geographic Distribution & Accessibility": {
        "options": [
            (
                "Centre Count by State & Region",
                "Map how many active examination centres exist in each state and "
                "region to identify infrastructure gaps.",
            ),
            (
                "Candidate Load per Centre",
                "Estimate average candidate volume per centre to identify overloaded "
                "and underutilised examination infrastructure.",
            ),
            (
                "Underserved Area Identification",
                "Flag states or regions with disproportionately few centres relative "
                "to their candidate population.",
            ),
            (
                "Centre Accessibility Index",
                "Score regions by how accessible examination infrastructure is, "
                "factoring in centre count relative to candidates.",
            ),
        ]
    },
    "State Candidate Volume Analysis": {
        "options": [
            (
                "Top & Bottom States by Candidate Volume",
                "Automatically displays the top 5 and bottom 5 states by total "
                "candidate registrations — no manual selection needed.",
            ),
            (
                "State Registration Trends",
                "Track how candidate volumes in each state change across exam "
                "years, identifying growing and declining states.",
            ),
            (
                "State Enrollment Comparison",
                "Compare total registrations side-by-side across all states for "
                "a single snapshot of geographic distribution.",
            ),
            (
                "State Growth Rate Analysis",
                "Calculate year-on-year growth rates for each state to identify "
                "which are expanding or contracting fastest.",
            ),
        ]
    },

    # ── GROUP 3: REGISTRATION & ENROLLMENT PATTERNS ───────────────────────────
    "Overall Registration Metrics & Trends": {
        "options": [
            (
                "Registration Trends & Growth Rate",
                "Track total candidate registration volumes across all exam years "
                "and calculate year-on-year growth rates to reveal whether "
                "participation is expanding, declining, or plateauing over time.",
            ),
            (
                "Registration by Exam Type",
                "Break down total registrations by examination type per year to "
                "see which exam types are growing in popularity.",
            ),
            (
                "Registration Forecast",
                "Project future registration volumes based on historical enrollment "
                "trends using time-series analysis.",
            ),
        ]
    },
    "Subject Enrollment & Combination Patterns": {
        "options": [
            (
                "Most & Least Registered Subjects",
                "Rank all subjects by total registration volume to identify the "
                "most and least popular subjects system-wide.",
            ),
            (
                "Popular Subject Combinations",
                "Identify the most common subject pairings and groupings chosen "
                "by candidates across exam years.",
            ),
            (
                "Compulsory Subject Compliance",
                "Measure how consistently candidates register for required subjects "
                "such as English and Mathematics.",
            ),
            (
                "Subject Enrollment Trends by Year",
                "Track how subject registration volumes shift across exam years, "
                "revealing growing and declining subjects.",
            ),
        ]
    },
    "Sponsor & Institutional Registration Breakdown": {
        "options": [
            (
                "Sponsor Type Distribution",
                "Break down registrations by sponsor category — school, private, "
                "government — to understand who funds candidate entry.",
            ),
            (
                "Sponsor Volume by State",
                "Compare sponsorship patterns across states to identify regions "
                "with high private or institutional sponsorship.",
            ),
            (
                "Sponsor Trends Over Time",
                "Track how the mix of sponsor types changes across exam years "
                "to spot shifts in institutional participation.",
            ),
            (
                "Sponsor vs Exam Type Relationship",
                "Analyse whether sponsor type correlates with exam type selection "
                "to understand how sponsorship shapes exam pathways.",
            ),
        ]
    },
    "Registration by Demographic": {
        "options": [
            (
                "Registration by Gender",
                "Break down total registrations by male and female candidates "
                "to measure overall gender participation.",
            ),
            (
                "Registration by Age Group",
                "Analyse how registrations are distributed across age brackets "
                "to identify dominant and underrepresented age groups.",
            ),
            (
                "Registration by Disability Status",
                "Assess the share of registrations from candidates with special "
                "needs to monitor inclusion in the examination system.",
            ),
            (
                "Demographic Registration Trends",
                "Track how the demographic composition of registrations — by "
                "gender, age, and disability — changes over time.",
            ),
        ]
    },

    # ── GROUP 4: EXAMINATION ADMINISTRATION ──────────────────────────────────
    "Exam Type Distribution": {
        "options": [
            (
                "Exam Type Volume Comparison",
                "Compare total candidate counts across all examination types to "
                "see which exam pathways are most used.",
            ),
            (
                "Exam Type Share by Year",
                "Track how the proportion of each exam type changes over time "
                "to reveal shifts in candidate pathway preferences.",
            ),
            (
                "Exam Type by State",
                "Identify which states favour particular examination types and "
                "where private candidacy is most prevalent.",
            ),
            (
                "Exam Type by Gender",
                "Analyse gender differences in examination type selection to "
                "understand if pathways have gender skews.",
            ),
        ]
    },
    "Centre Statistics, Capacity & Load Analysis": {
        "options": [
            (
                "Active Centres by State",
                "Count the number of active examination centres in each state "
                "to map infrastructure distribution.",
            ),
            (
                "Candidate Load per Centre",
                "Calculate average candidate volumes per centre and flag centres "
                "operating above or below sustainable thresholds.",
            ),
            (
                "Over-Capacity Centre Detection",
                "Identify centres handling more candidates than is sustainable, "
                "flagging infrastructure stress points.",
            ),
            (
                "Underutilized Centre Analysis",
                "Find centres operating well below their candidate capacity to "
                "inform resource reallocation decisions.",
            ),
        ]
    },
    "Centre Performance Rankings": {
        "options": [
            (
                "Top Performing Centres",
                "Rank centres by candidate academic outcomes and pass rates to "
                "identify centres delivering the best results.",
            ),
            (
                "Bottom Performing Centres",
                "Identify consistently low-performing centres that may require "
                "targeted intervention or additional support.",
            ),
            (
                "Centre Performance Scorecard",
                "Generate a comprehensive performance profile for each centre "
                "combining pass rates, volume, and trend data.",
            ),
            (
                "Centre Performance Trends",
                "Track whether individual centres are improving, declining, or "
                "stable in their candidate outcomes over time.",
            ),
        ]
    },
    "Examination Attendance & Absenteeism": {
        "options": [
            (
                "Registered vs Sat Candidates",
                "Measure the gap between total registrations and candidates who "
                "actually sat the exam to quantify absenteeism.",
            ),
            (
                "Absenteeism Rate by State",
                "Identify states with the highest rates of registered candidates "
                "failing to sit their exams.",
            ),
            (
                "Absenteeism by Exam Type & Gender",
                "Break down absenteeism rates across exam types and gender groups "
                "to identify at-risk segments.",
            ),
            (
                "Absenteeism Trends Over Time",
                "Track whether overall attendance rates are improving or worsening "
                "year on year across the system.",
            ),
        ]
    },

    # ── GROUP 5: ACADEMIC PERFORMANCE ANALYSIS ───────────────────────────────
    "Overall Grade Distribution": {
        "options": [
            (
                "Full Grade Breakdown",
                "View the complete distribution of all grades from distinction to "
                "failure for a system-wide picture of achievement.",
            ),
            (
                "Pass vs Fail Rate",
                "Calculate system-wide success and failure rates and track how "
                "they evolve across exam years.",
            ),
            (
                "Grade Distribution by Exam Year",
                "Track how the overall grade spread changes across years to reveal "
                "whether the system is improving or declining.",
            ),
            (
                "Grade Distribution by State",
                "Compare grade outcome distributions across different states to "
                "identify geographic performance disparities.",
            ),
        ]
    },
    "Credit & Pass Requirement Analysis": {
        "options": [
            (
                "5-Credit Attainment Rate",
                "Measure how many candidates achieve the minimum 5 credits required "
                "for tertiary admission and track this over time.",
            ),
            (
                "English & Maths Credit Rate",
                "Specifically track credit attainment in English and Mathematics — "
                "the two subjects most critical for university entry.",
            ),
            (
                "Credit Attainment Trend",
                "Monitor how the 5-credit pass rate evolves across exam years to "
                "assess system-wide progress toward university-readiness.",
            ),
            (
                "Credit Attainment by State & Gender",
                "Break down credit achievement by state and gender to identify "
                "which groups and regions are falling behind.",
            ),
        ]
    },
    "Subject Performance Comparison": {
        "options": [
            (
                "Best & Worst Performing Subjects",
                "Rank all subjects by average pass and credit rates to identify "
                "where candidates consistently succeed or struggle.",
            ),
            (
                "Subject Pass Rate Comparison",
                "Compare pass rates across all subjects side by side to benchmark "
                "relative subject difficulty.",
            ),
            (
                "Subject Performance by State",
                "Identify states where specific subjects perform above or below "
                "the national average.",
            ),
            (
                "Subject Performance Trends",
                "Track how individual subject performance metrics shift across "
                "exam years.",
            ),
        ]
    },
    "Performance by Gender, Age Group & Disability": {
        "options": [
            (
                "Gender Performance Gap",
                "Compare average grades and pass rates between male and female "
                "candidates to quantify the gender achievement gap.",
            ),
            (
                "Age Group Performance Comparison",
                "Assess whether younger or older candidates perform better and "
                "identify optimal examination age ranges.",
            ),
            (
                "Disability Achievement Gap",
                "Measure the performance difference between candidates with and "
                "without disabilities to assess inclusion outcomes.",
            ),
            (
                "Combined Demographic Performance",
                "Analyse performance across combinations of gender, age, and "
                "disability simultaneously.",
            ),
        ]
    },
    "State & Regional Performance Comparison": {
        "options": [
            (
                "State Performance Rankings",
                "Rank all states by average candidate academic outcomes to identify "
                "the highest and lowest performing states.",
            ),
            (
                "Regional Performance Gaps",
                "Identify disparities between high and low-performing regions to "
                "highlight geographic inequality in outcomes.",
            ),
            (
                "State Performance Trends",
                "Track which states are improving or declining in academic outcomes "
                "over time.",
            ),
        ]
    },
    "Exam Type Performance Comparison": {
        "options": [
            (
                "School vs Private Candidate Performance",
                "Compare grade distributions between school and private exam "
                "candidates to assess pathway equity.",
            ),
            (
                "Exam Type Pass Rate Comparison",
                "Calculate and compare pass rates across all exam types to see "
                "whether different pathways produce different outcomes.",
            ),
            (
                "Exam Type Performance by State",
                "Identify states where particular exam types yield stronger or "
                "weaker outcomes than the national average.",
            ),
            (
                "Exam Type Performance Trends",
                "Track how performance differences between exam types evolve "
                "across years.",
            ),
        ]
    },

    # ── GROUP 6: SUBJECT INTELLIGENCE ────────────────────────────────────────
    "Subject Popularity & Enrollment Statistics": {
        "options": [
            (
                "Subject Enrollment Rankings",
                "Rank all subjects by total number of registrations to identify "
                "the most and least chosen subjects.",
            ),
            (
                "Subject Popularity Trends",
                "Track which subjects are growing or declining in registration "
                "volume over exam years.",
            ),
            (
                "Subject Popularity by State",
                "Compare subject enrollment volumes across states to identify "
                "regional subject preferences.",
            ),
            (
                "Niche Subject Identification",
                "Highlight subjects with very low enrollment that may be at risk "
                "of discontinuation.",
            ),
        ]
    },
    "Subject-Gender & Subject-Age Demographic Breakdown": {
        "options": [
            (
                "Gender Composition by Subject",
                "Reveal which subjects are male-dominated, female-dominated, or "
                "balanced in their candidate demographics.",
            ),
            (
                "Age Group Composition by Subject",
                "Show which age brackets are most represented in each subject's "
                "candidate pool.",
            ),
            (
                "STEM Gender Gap by Subject",
                "Specifically analyse gender representation in science, technology, "
                "engineering, and mathematics subjects.",
            ),
            (
                "Demographic Shifts in Subject Enrollment",
                "Track whether the gender or age profile of subjects is changing "
                "over time.",
            ),
        ]
    },
    "High vs. Low Performing Subjects": {
        "options": [
            (
                "Top Performing Subjects by Pass Rate",
                "Identify subjects with consistently high pass and credit rates "
                "across exam years.",
            ),
            (
                "Lowest Performing Subjects",
                "Flag subjects with persistently poor outcomes that may need "
                "curriculum or teaching intervention.",
            ),
            (
                "Subject Difficulty Ranking",
                "Rank subjects from easiest to hardest based on historical grade "
                "distributions.",
            ),
            (
                "Performance Consistency by Subject",
                "Assess which subjects show stable versus volatile performance "
                "year on year.",
            ),
        ]
    },
    "Rare & Declining Subject Trends": {
        "options": [
            (
                "Lowest Enrollment Subjects",
                "List subjects with the fewest registrations to identify those "
                "at risk of being discontinued.",
            ),
            (
                "Year-on-Year Enrollment Decline",
                "Identify subjects that are losing candidates consistently over "
                "multiple exam years.",
            ),
            (
                "Subjects at Risk of Discontinuation",
                "Flag subjects where enrollment has dropped below sustainable "
                "thresholds requiring policy intervention.",
            ),
            (
                "Regional Rarity Analysis",
                "Identify subjects that are rare in certain states but common in "
                "others, revealing geographic curriculum gaps.",
            ),
        ]
    },

    # ── GROUP 7: TEMPORAL TRENDS & FORECASTING ────────────────────────────────
    "Year-over-Year Enrollment & Registration Trends": {
        "options": [
            (
                "Total Enrollment by Year",
                "Track overall candidate volumes across all available exam years "
                "to understand the system's growth trajectory.",
            ),
            (
                "Enrollment Growth Rate",
                "Calculate year-on-year percentage change in total registrations "
                "to quantify expansion or contraction.",
            ),
            (
                "Enrollment Trends by State & Gender",
                "Break down enrollment growth by state and gender over time to "
                "reveal who is driving system growth.",
            ),
            (
                "Cyclical Enrollment Patterns",
                "Identify recurring peaks or dips in registration across exam "
                "cycles that may relate to policy or economic events.",
            ),
        ]
    },
    "Performance Trends Over Time": {
        "options": [
            (
                "Pass Rate Trends",
                "Monitor how the system-wide pass rate evolves across exam years "
                "to assess whether quality is improving.",
            ),
            (
                "Credit Attainment Trends",
                "Track changes in the proportion of candidates achieving credit "
                "grades over time.",
            ),
            (
                "Grade Distribution Shift",
                "Visualise how the full grade distribution changes year on year "
                "to detect grade inflation or deflation.",
            ),
            (
                "Subject Performance Over Time",
                "Track performance trends for individual subjects across years "
                "to identify sustained improvement or decline.",
            ),
        ]
    },
    "Growth Rate Analysis by State, Subject & Gender": {
        "options": [
            (
                "Fastest Growing States",
                "Identify states with the highest enrollment growth rates to "
                "understand where demand is expanding fastest.",
            ),
            (
                "Fastest Growing Subjects",
                "Rank subjects by their year-on-year registration growth rate "
                "to spot emerging subject preferences.",
            ),
            (
                "Gender Growth Rate Comparison",
                "Compare enrollment growth rates between male and female candidates "
                "to track equity progress.",
            ),
            (
                "Compound Growth Rate Summary",
                "Calculate multi-year compound growth rates for states, subjects, "
                "and demographic groups.",
            ),
        ]
    },
    "Forecasting & Projection Models": {
        "options": [
            (
                "Enrollment Volume Forecast",
                "Project total candidate registrations for future exam years based "
                "on historical growth patterns.",
            ),
            (
                "State-Level Enrollment Projections",
                "Forecast registration trends for individual states to support "
                "infrastructure and resource planning.",
            ),
            (
                "Pass Rate Projections",
                "Estimate future pass rates based on historical performance trends "
                "to anticipate systemic outcomes.",
            ),
            (
                "Demographic Composition Forecast",
                "Project how the gender and age profile of candidates will shift "
                "over coming exam cycles.",
            ),
        ]
    },

    # ── GROUP 8: STATISTICAL SUMMARIES & ADVANCED ANALYTICS ──────────────────
    "Descriptive Statistics Summary": {
        "options": [
            (
                "Central Tendency Measures",
                "Calculate mean, median, and mode for age, grades, and enrollment "
                "figures to establish statistical baselines.",
            ),
            (
                "Dispersion & Spread Analysis",
                "Assess variance, standard deviation, and range across key variables "
                "to understand data spread.",
            ),
            (
                "Quartile & Percentile Breakdown",
                "Identify data distribution segments and boundary values to "
                "understand the shape of the candidate population.",
            ),
            (
                "Outlier Detection",
                "Find anomalies and extreme values in enrollment, age, or performance "
                "data that may indicate data quality issues.",
            ),
        ]
    },
    "Correlation Analysis": {
        "options": [
            (
                "Age vs Performance Correlation",
                "Determine whether candidate age has a statistically meaningful "
                "relationship with academic grades.",
            ),
            (
                "Disability vs Subject Choice Correlation",
                "Analyse whether disability status relates to subject selection "
                "patterns in a statistically significant way.",
            ),
            (
                "Gender vs Performance Correlation",
                "Measure the statistical relationship between gender and academic "
                "outcomes across the full dataset.",
            ),
        ]
    },
    "Distribution & Normality Analysis": {
        "options": [
            (
                "Age Distribution Shape",
                "Test whether candidate age follows a normal, skewed, or bimodal "
                "distribution across the dataset.",
            ),
            (
                "Grade Distribution Normality",
                "Assess whether grade distributions are statistically normal or "
                "skewed and what that implies.",
            ),
            (
                "Enrollment Distribution by State",
                "Analyse the shape and spread of state-level enrollment distributions "
                "to understand geographic concentration.",
            ),
            (
                "Distribution Comparison Across Years",
                "Compare how key variable distributions shift between exam years "
                "to detect structural changes.",
            ),
        ]
    },
    "Multivariate & Segmentation Analysis": {
        "options": [
            (
                "Candidate Cluster Segmentation",
                "Group candidates into meaningful segments based on multiple "
                "variables simultaneously to uncover hidden patterns.",
            ),
            (
                "High-Performance Candidate Profile",
                "Identify the combination of attributes most associated with "
                "strong academic results.",
            ),
            (
                "At-Risk Candidate Profiling",
                "Detect candidate profiles most likely to underperform or fail "
                "based on demographic and enrollment patterns.",
            ),
            (
                "Multi-Dimensional Equity Analysis",
                "Assess fairness in outcomes across combinations of gender, age, "
                "state, and disability status simultaneously.",
            ),
        ]
    },
}

# -------------------- BREADCRUMB --------------------
st.markdown("""
<div class="breadcrumb">
    <a href="#">Select Report Group</a> &gt; <strong>Select Filter Group</strong>
</div>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
st.markdown(f"""
<div class="filter-group-header">
    <div class="filter-group-title">Select Filter Group</div>
    <div class="filter-group-subtitle">
        Choose an analysis from the <strong>{selected_subgroup}</strong> category
        to begin configuring your report filters.
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------- CARDS --------------------
if selected_subgroup in analysis_options:
    options  = analysis_options[selected_subgroup]["options"]
    num_cols = 3
    rows     = [options[i : i + num_cols] for i in range(0, len(options), num_cols)]

    for row in rows:
        cols = st.columns(num_cols)
        for idx, (title, description) in enumerate(row):
            with cols[idx]:
                st.markdown(f"""
                <div class="analysis-card">
                    <div class="analysis-card-title">{title}</div>
                    <div class="analysis-card-description">{description}</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Explore Filters →", key=f"filter_{title}", type="primary"):
                    st.session_state.selected_analysis   = title
                    st.session_state.selected_subgroup   = selected_subgroup
                    st.session_state.selected_main_group = selected_main_group
                    st.switch_page("pages/configure_filters.py")

        for empty_idx in range(len(row), num_cols):
            cols[empty_idx].empty()

else:
    st.error(
        f"❌ No analysis options found for '{selected_subgroup}'. "
        "Please go back and try again."
    )
    if st.button("← Go Back"):
        st.switch_page("pages/create_report.py")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("← Back to Report Selection"):
    st.switch_page("pages/create_report.py")
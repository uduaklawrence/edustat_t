import streamlit as st
from datetime import datetime
from Analytics_layer import (
    get_filter_options,
    get_record_count,
    get_top_bottom_states,
)
from geo_config import ZONES                
from db_queries import create_invoice_record
from report_pricing import calculate_report_price
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

st.set_page_config(page_title="Select Filters", layout="wide")

if "report_cart" not in st.session_state:
    st.session_state.report_cart = []

with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap');

.breadcrumb { font-size: 14px; color: var(--text-secondary); margin-bottom: 24px; }
.filter-header { margin-bottom: 32px; }
.filter-title { font-size: 32px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; }
.filter-subtitle { font-size: 16px; color: var(--text-secondary); line-height: 1.6; }
.filter-section-title { font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 36px 0 20px 0; }
.record-count-box {
    background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px;
    padding: 0.8rem 1.2rem; font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem; color: #166534; margin-top: 1.5rem;
}
.record-count-box strong { font-size: 1.1rem; }
.pricing-panel {
    background: #fff; border: 1.5px solid #e2e8f0;
    border-radius: 14px; padding: 1.4rem 1.6rem; position: sticky; top: 1rem;
}
.pricing-panel-title {
    font-family: 'DM Sans', sans-serif; font-size: 0.78rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; color: #2563eb; margin-bottom: 0.8rem;
}
.price-display {
    font-family: 'Playfair Display', serif; font-size: 2rem;
    font-weight: 700; color: #0f172a; line-height: 1.1;
}
.price-label {
    font-family: 'DM Sans', sans-serif; font-size: 0.82rem;
    color: #6b7280; margin-top: 0.25rem; margin-bottom: 1rem;
}
.weight-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.4rem 0; border-bottom: 1px solid #f1f5f9;
    font-family: 'DM Sans', sans-serif; font-size: 0.85rem;
}
.weight-row:last-of-type { border-bottom: none; }
.weight-key { color: #6b7280; }
.weight-val { font-weight: 600; color: #1e293b; }
.weight-total {
    display: flex; justify-content: space-between; padding: 0.6rem 0 0;
    margin-top: 0.4rem; border-top: 2px solid #e2e8f0;
    font-family: 'DM Sans', sans-serif; font-size: 0.9rem;
    font-weight: 700; color: #0f172a;
}
.cart-banner {
    background: linear-gradient(135deg, #0f172a, #1e3a8a); border-radius: 10px;
    padding: 1rem 1.4rem; display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 1.5rem;
}
.cart-text { font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #e2e8f0; }
.cart-text strong { color: #fff; }
.top-bottom-box {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem;
}
.top-bottom-title { font-weight: 700; color: #0f172a; margin-bottom: 0.5rem; font-size: 0.95rem; }
.top-tag {
    display: inline-block; background: #dcfce7; color: #166534;
    border-radius: 6px; padding: 2px 10px; margin: 3px; font-size: 0.82rem; font-weight: 600;
}
.bottom-tag {
    display: inline-block; background: #fee2e2; color: #991b1b;
    border-radius: 6px; padding: 2px 10px; margin: 3px; font-size: 0.82rem; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

user_id = st.session_state.get("user_id", 0)

def _post_add_nav(cart: list) -> None:
    """Render the two post-add navigation buttons inline."""
    count = len(cart)
    total = sum(i.get("price", 0) for i in cart)
    st.markdown(f"**📋 Invoice: {count} report(s) · Total: ₦{total:,}**")
    n1, n2 = st.columns(2)
    with n1:
        if st.button("➕ Add Another Report", key=f"nav_more_{count}",
                     use_container_width=True):
            st.switch_page("pages/create_report.py")
    with n2:
        if st.button("📋 View Invoice & Checkout", key=f"nav_checkout_{count}",
                     type="primary", use_container_width=True):
            _go_to_invoice(cart)

def _go_to_invoice(cart: list) -> None:
    if not st.session_state.get("invoice_ref"):
        total     = sum(item.get("price", 0) for item in cart)
        data_dict = {
            "reports": [
                {
                    "report_group": item.get("report_group"),
                    "subgroup":     item.get("subgroup"),
                    "analysis":     item.get("analysis"),
                    "filters":      item.get("filters", {}),
                    "record_count": item.get("record_count", 0),
                    "price":        item.get("price"),
                    "total_weight": item.get("total_weight"),
                }
                for item in cart
            ]
        }
        invoice_ref = create_invoice_record(
            user_id=st.session_state.get("user_id", 0),
            total=total,
            data_dict=data_dict,
        )
        if invoice_ref:
            st.session_state.invoice_ref = invoice_ref
        else:
            st.error("❌ Failed to create invoice. Please try again.")
            st.stop()
    st.switch_page("pages/view_invoice.py")

# ── Guard ──────────────────────────────────────────────────────────────────────
if "selected_analysis" not in st.session_state:
    st.error("❌ No analysis selected. Please go back and select an analysis type.")
    if st.button("← Go Back"):
        st.switch_page("pages/report_filters.py")
    st.stop()

selected_analysis   = st.session_state.get("selected_analysis",   "")
selected_subgroup   = st.session_state.get("selected_subgroup",   "")
selected_main_group = st.session_state.get("selected_main_group", "")

filter_options = get_filter_options()

# ── Reset filter state when entering a fresh report configuration ──────────
reset_key = f"filter_page_{selected_analysis}"
if st.session_state.get("_filter_page_key") != reset_key:
    keys_to_clear = [
        "all_years", "exam_year", "all_sex", "sex_select",
        "all_states", "state_select", "all_agegroup", "agegroup_select",
        "all_regions", "region_select",
        "all_centres", "centre_select", "top_n_centre",
        "all_disability", "disability_select",
        "all_sponsor", "sponsor_select",
        "all_examtype", "examtype_select",
        "all_subject", "subject_select",
        "all_grade", "grade_select",
        "all_status", "status_select",
        # ── special case keys ──
        "ar_all_years", "ar_years", "ar_all_states", "ar_states",
        "cohort_all_years", "cohort_years", "cohort_all_sex", "cohort_sex", "cohort_age_range",
        "cs_all_years", "cs_years", "cs_extra_subjects",
        "pf_pass_grades", "pf_fail_grades", "pf_all_years", "pf_years",
        "pf_all_states", "pf_states", "pf_all_sex", "pf_sex", "pf_all_et", "pf_et",
        "bw_all_years", "bw_years", "bw_all_states", "bw_states", "bw_top_n",
        "tb_exam_year", "tb_top_n",
    
    # ── also clear post-add navigation state ──
    "post_add_more", "post_add_checkout",
    "nav_more_1", "nav_more_2", "nav_more_3",
    "nav_checkout_1", "nav_checkout_2", "nav_checkout_3",
    ]

    for k in keys_to_clear:
        st.session_state.pop(k, None)
    st.session_state["_filter_page_key"] = reset_key

# ── Filter mapping ─────────────────────────────────────────────────────────────
filter_mapping = {
    "Age Range of Candidates":                           ["__AGE_RANGE__"],
    "Age Distribution by Exam Year":                     ["ExamYear", "AgeGroup"],
    "Birth Year Distribution":                           ["ExamYear", "AgeGroup"],
    "Generational Education Trends":                     ["ExamYear", "AgeGroup"],
    "Male-to-Female Ratio Overview":                     ["Sex"],
    "Gender Balance by Exam Year":                       ["ExamYear", "Sex"],
    "Gender Distribution by State & Centre":             ["Sex", "State", "centre"],
    "Gender Equity Trends Over Time":                    ["ExamYear", "Sex"],
    "Age-Appropriate Enrollment Assessment":             ["ExamYear", "AgeGroup"],
    "Cohort Tracking Across Years":                      ["__COHORT_AGE__"],
    "Disability Inclusion Rate":                         ["Disability"],
    "Disability Trends by Exam Year":                    ["ExamYear", "Disability"],
    "Disability by Gender & Age Group":                  ["Disability", "Sex", "AgeGroup"],
    "Regional Disability Patterns":                      ["Disability", "State"],
    "Top & Bottom States by Candidate Volume":           ["__TOP_BOTTOM_STATES__"],
    "State Registration Trends":                         ["ExamYear", "State"],
    "State Enrollment Comparison":                       ["ExamYear", "State"],
    "State Growth Rate Analysis":                        ["ExamYear", "State"],
    "Centre Count by State & Region":                    ["State", "ExamYear"],
    "Candidate Load per Centre":                          ["State", "ExamYear", "__TOP_N_CENTRE__"],
    "Centre Accessibility Index":                        ["State", "centre"],
    "Registration Trends & Growth Rate":                 ["ExamYear"],
    "Registration by Exam Type":                         ["ExamYear", "ExamType"],
    "Registration Forecast":                             ["ExamYear", "__FORECAST_HORIZON__"],
    "Most & Least Registered Subjects":                  ["Subject"],
    "Popular Subject Combinations":                      ["ExamYear", "Subject"],
    "Compulsory Subject Compliance":                     ["__COMPULSORY_SUBJECT__"],
    "Subject Enrollment Trends by Year":                 ["ExamYear", "Subject"],
    "Sponsor Type Distribution":                         ["Sponsor"],
    "Sponsor Volume by State":                           ["Sponsor", "State"],
    "Sponsor Trends Over Time":                          ["ExamYear", "Sponsor"],
    "Sponsor vs Exam Type Relationship":                 ["Sponsor", "ExamType"],
    "Registration by Gender":                            ["Sex"],
    "Registration by Age Group":                         ["AgeGroup"],
    "Registration by Disability Status":                 ["Disability"],
    "Demographic Registration Trends":                   ["ExamYear", "Sex", "AgeGroup"],
    "Exam Type Volume Comparison":                       ["ExamType"],
    "Exam Type Share by Year":                           ["ExamType", "ExamYear"],
    "Exam Type by State":                                ["ExamType", "State"],
    "Exam Type by Gender":                               ["ExamType", "Sex"],
    "Top Performing Centres":                            ["ExamYear", "centre", "State"],
    "Bottom Performing Centres":                         ["ExamYear", "centre", "State"],
    "Centre Performance Scorecard":                      ["ExamYear", "centre", "State"],
    "Centre Performance Trends":                         ["ExamYear", "centre"],
    "Registered vs Sat Candidates":                      ["ExamYear", "State", "Status"],
    "Absenteeism Rate by State":                         ["State", "Status"],
    "Absenteeism by Exam Type":                          ["ExamType", "Status"],
    "Absenteeism by Gender":                             ["Status", "Sex"],
    "Absenteeism Trends Over Time":                      ["ExamYear", "Status"],
    "Full Grade Breakdown":                              ["ExamYear", "Grade"],
    "Pass vs Fail Rate":                                 ["__PASS_FAIL__"],
    "Grade Distribution by Exam Year":                   ["ExamYear", "Grade"],
    "Grade Distribution by State":                       ["ExamYear", "Grade", "State"],
    "5-Credit Attainment Rate":                          ["ExamYear", "Subject", "Grade"],
    "English & Maths Credit Rate":                       ["ExamYear", "State", "Subject", "Grade"],
    "Credit Attainment Trend":                           ["ExamYear", "Grade"],
    "Credit Attainment by State & Gender":               ["ExamYear", "Grade", "State", "Sex"],
    "Best & Worst Performing Subjects":                  ["__BEST_WORST_SUBJECTS__"],
    "Subject Pass Rate Comparison":                      ["ExamYear", "Subject", "Grade"],
    "Subject Performance by State":                      ["Subject", "Grade", "State"],
    "Subject Performance Trends":                        ["ExamYear", "Subject", "Grade"],
    "Gender Performance Gap":                            ["ExamYear", "Sex", "Grade"],
    "Age Group Performance Comparison":                  ["ExamYear", "AgeGroup", "Grade"],
    "Disability Achievement Gap":                        ["ExamYear", "Disability", "Grade"],
    "Combined Demographic Performance":                  ["ExamYear", "Sex", "AgeGroup", "Disability", "Grade"],
    "State Performance Rankings":                        ["ExamYear", "State", "Grade"],
    "Regional Performance Gaps":                         ["ExamYear", "State", "Grade"],
    "State Performance Trends":                          ["ExamYear", "State", "Grade"],
    "School vs Private Candidate Performance":           ["ExamYear", "ExamType", "Grade"],
    "Exam Type Pass Rate Comparison":                    ["ExamYear", "ExamType", "Grade"],
    "Exam Type Performance by State":                    ["ExamType", "State", "Grade"],
    "Exam Type Performance Trends":                      ["ExamYear", "ExamType", "Grade"],
    "Subject Enrollment Rankings":                       ["ExamYear", "Subject"],
    "Subject Popularity Trends":                         ["ExamYear", "Subject"],
    "Subject Popularity by State":                       ["Subject", "State"],
    "Niche Subject Identification":                      ["ExamYear", "Subject"],
    "Gender Composition by Subject":                     ["Subject", "Sex"],
    "Age Group Composition by Subject":                  ["Subject", "AgeGroup"],
    "STEM Gender Gap by Subject":                        ["Subject", "Sex"],
    "Demographic Shifts in Subject Enrollment":          ["ExamYear", "Subject", "Sex", "AgeGroup"],
    "Top Performing Subjects by Pass Rate":              ["ExamYear", "Subject", "Grade"],
    "Lowest Performing Subjects":                        ["ExamYear", "Subject", "Grade"],
    "Subject Difficulty Ranking":                        ["ExamYear", "Subject", "Grade"],
    "Performance Consistency by Subject":                ["ExamYear", "Subject", "Grade"],
    "Lowest Enrollment Subjects":                        ["ExamYear", "Subject"],
    "Year-on-Year Enrollment Decline":                   ["ExamYear", "Subject"],
    "Subjects at Risk of Discontinuation":               ["ExamYear", "Subject"],
    "Regional Rarity Analysis":                          ["Subject", "State"],
    "Total Enrollment by Year":                          ["ExamYear"],
    "Enrollment Growth Rate":                            ["ExamYear"],
    "Enrollment Trends by State & Gender":               ["ExamYear", "State", "Sex"],
    "Cyclical Enrollment Patterns":                      ["ExamYear"],
    "Pass Rate Trends":                                  ["ExamYear", "Grade"],
    "Credit Attainment Trends":                          ["ExamYear", "Grade"],
    "Grade Distribution Shift":                          ["ExamYear", "Grade"],
    "Subject Performance Over Time":                     ["ExamYear", "Subject", "Grade"],
    "Fastest Growing States":                            ["ExamYear", "State"],
    "Fastest Growing Subjects":                          ["ExamYear", "Subject"],
    "Gender Growth Rate Comparison":                     ["ExamYear", "Sex"],
    "Compound Growth Rate Summary":                      ["ExamYear", "State", "Subject"],
    "Enrollment Volume Forecast":                        ["ExamYear"],
    "State-Level Enrollment Projections":                ["ExamYear", "State"],
    "Pass Rate Projections":                             ["ExamYear", "Grade"],
    "Demographic Composition Forecast":                  ["ExamYear", "Sex", "AgeGroup"],
    "Central Tendency Measures":                         ["ExamYear", "AgeGroup", "Grade"],
    "Dispersion & Spread Analysis":                      ["ExamYear", "Grade", "State"],
    "Quartile & Percentile Breakdown":                   ["ExamYear", "Grade"],
    "Outlier Detection":                                 ["ExamYear", "State", "Grade"],
    "Age vs Performance Correlation":                    ["ExamYear", "AgeGroup", "Grade"],
    "Disability vs Subject Choice Correlation":          ["ExamYear", "Disability", "Subject"],
    "Gender vs Performance Correlation":                 ["ExamYear", "Sex", "Grade"],
    "Age Distribution Shape":                            ["ExamYear", "AgeGroup"],
    "Grade Distribution Normality":                      ["ExamYear", "Grade"],
    "Enrollment Distribution by State":                  ["ExamYear", "State"],
    "Distribution Comparison Across Years":              ["ExamYear", "Grade", "State"],
    "Candidate Cluster Segmentation":                    ["ExamYear", "Sex", "AgeGroup", "State", "Disability"],
    "High-Performance Candidate Profile":                ["ExamYear", "Sex", "AgeGroup", "State", "Grade"],
    "At-Risk Candidate Profiling":                       ["ExamYear", "Sex", "AgeGroup", "State", "Grade"],
    "Multi-Dimensional Equity Analysis":                 ["ExamYear", "Sex", "AgeGroup", "State", "Disability", "Grade"],
}

required_filters = filter_mapping.get(selected_analysis, ["ExamYear", "State", "Sex"])

# ── Cart banner ────────────────────────────────────────────────────────────────
cart_count = len(st.session_state.report_cart)
if cart_count > 0:
    cart_total = sum(item.get("price", 0) for item in st.session_state.report_cart)
    plural     = "s" if cart_count != 1 else ""
    st.markdown(
        '<div class="cart-banner"><div class="cart-text">🛒 Invoice: <strong>'
        + str(cart_count) + " report" + plural
        + "</strong> &nbsp;·&nbsp; Total so far: <strong>₦"
        + f"{cart_total:,}" + "</strong></div></div>",
        unsafe_allow_html=True,
    )
    if st.button("📋 View Invoice", key="view_cart_top"):
        st.switch_page("pages/view_invoice.py")

# ── Breadcrumb & header ────────────────────────────────────────────────────────
st.markdown(
    '<div class="breadcrumb">Select Report Group &gt; Select Filter Group'
    " &gt; <strong>Select Filters</strong></div>"
    '<div class="filter-header"><div class="filter-title">Filter Your Data</div>'
    '<div class="filter-subtitle">Customise your <strong>'
    + selected_analysis
    + "</strong> report. Your price updates live as you make selections.</div></div>",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CASE: Top & Bottom States
# ─────────────────────────────────────────────────────────────────────────────
if required_filters == ["__TOP_BOTTOM_STATES__"]:
    st.markdown(
        '<div class="filter-section-title">Report Configuration</div>',
        unsafe_allow_html=True,
    )
    years_all = filter_options.get("ExamYear", [])
    sel_years = st.multiselect(
        "📅 Filter by Exam Year(s) — optional (leave blank for all years)",
        years_all, key="tb_exam_year",
    )
    top_n_val = st.slider("How many top / bottom states?", 3, 10, 5, key="tb_top_n")
    tb_data   = get_top_bottom_states(exam_years=tuple(sel_years), top_n=top_n_val)

    top_tags = "".join(
        '<span class="top-tag">🟢 ' + s + "</span>" for s in tb_data["top"]
    )
    bot_tags = "".join(
        '<span class="bottom-tag">🔴 ' + s + "</span>" for s in tb_data["bottom"]
    )
    st.markdown(
        '<div class="top-bottom-box"><div class="top-bottom-title">Top '
        + str(top_n_val) + " States</div>"
        + (top_tags or "No data — try selecting a year range.") + "</div>"
        '<div class="top-bottom-box"><div class="top-bottom-title">Bottom '
        + str(top_n_val) + " States</div>"
        + (bot_tags or "No data.") + "</div>",
        unsafe_allow_html=True,
    )

    ranked = tb_data.get("all_ranked")
    if ranked is not None and not ranked.empty:
        with st.expander("📊 Full state ranking"):
            ranked.index = range(1, len(ranked) + 1)
            st.dataframe(ranked, width="stretch")

    combined_states = list(dict.fromkeys(tb_data["top"] + tb_data["bottom"]))

    # Effective filters for pricing:
    # - combined_states = top N + bottom N states = 2 × top_n_val entries
    # - sel_years = user selected exam years
    # Both affect the weight and therefore the price
    tb_filters = {
        "State":    combined_states,
        "ExamYear": sel_years,
    }

    # Price reflects: state count (top N + bottom N) × year count
    pricing      = calculate_report_price(tb_filters)
    state_weight = len(combined_states)   # top_n + bottom_n
    year_weight  = len(sel_years) if sel_years else 1
    total_weight = state_weight * year_weight

    col_a, col_b = st.columns([2.6, 1], gap="large")
    with col_b:
        rec_count_preview = get_record_count(
            states=tuple(combined_states),
            exam_years=tuple(sel_years),
        )
        st.markdown(
            '<div class="pricing-panel">'
            '<div class="pricing-panel-title">💰 Live Pricing</div>'
            '<div class="price-display">' + pricing["price_formatted"] + '</div>'
            '<div class="price-label">Top & Bottom '
            + str(top_n_val)
            + ' states ('
            + str(len(combined_states))
            + ' states × '
            + str(year_weight)
            + ' year'
            + ('s' if year_weight != 1 else '')
            + ')</div>'
            '<div class="record-count-box" style="margin-top:0.8rem;">'
            '📊 Matching: <strong>'
            + f"{rec_count_preview:,}"
            + '</strong> unique candidates</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, _, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back_tb", width="stretch"):
            st.switch_page("pages/report_filters.py")
    with b3:
        if st.button("➕ Add to Invoice", key="add_tb", type="primary", width="stretch"):
            if not combined_states:
                st.error("❌ No state data available.")
            else:
                final_pricing = calculate_report_price(tb_filters)
                rec_count = get_record_count(states=tuple(combined_states),
                                             exam_years=tuple(sel_years))
                tb_filters["TopN"] = top_n_val   # pass N to view_report
                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          tb_filters,
                    "record_count":     rec_count,
                    "price":            final_pricing["price"],
                    "price_fmt":        final_pricing["price_formatted"],
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      selected_analysis,
                }
                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                # st.success("✅ Added Top & Bottom States report to invoice.")
                # st.balloons()
    st.stop()

# ── CANDIDATE LOAD PER CENTRE — TOP / BOTTOM N ───────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
if "__TOP_N_CENTRE__" in required_filters:

    # This special report is self-contained.
    # Do NOT rely on filter_values / col_price from STANDARD FILTER LAYOUT,
    # because that section is below this block and has not executed yet.
    filter_values = {}
    configured_filters = set()

    years_all  = filter_options.get("ExamYear", [])
    states_all = filter_options.get("State", [])

    col_filters, col_price = st.columns([2.6, 1], gap="large")

    # ── LEFT: REPORT CONFIGURATION ───────────────────────────────────────────
    with col_filters:

        st.markdown(
            "Identify examination centres handling the **highest** or **lowest** "
            "candidate volumes within the selected examination period and State scope."
        )

        # ── Exam Year ────────────────────────────────────────────────────────
        st.markdown("**📅 Select Exam Year(s)**")

        all_years = st.checkbox(
            "Include All Exam Years",
            value=False,
            key="centre_load_all_years",
        )

        if all_years:
            selected_years = list(years_all)
        else:
            selected_years = st.multiselect(
                "Select one or more exam years",
                years_all,
                key="centre_load_years",
            )

        if selected_years:
            filter_values["ExamYear"] = selected_years
            configured_filters.add("ExamYear")

        # ── State ────────────────────────────────────────────────────────────
        st.markdown("**🌍 Select State(s)**")

        all_states = st.checkbox(
            "Include All States",
            value=False,
            key="centre_load_all_states",
        )

        if all_states:
            selected_states = list(states_all)
        else:
            selected_states = st.multiselect(
                "Select one or more states",
                states_all,
                key="centre_load_states",
            )

        if selected_states:
            filter_values["State"] = selected_states
            configured_filters.add("State")

        st.markdown("---")

        # ── Direction ────────────────────────────────────────────────────────
        st.markdown("**🏫 Centre Load Direction**")

        load_direction = st.radio(
            "Which centres do you want to analyse?",
            options=[
                "🔴 Highest Load — Highest candidate volumes",
                "🟢 Lowest Load — Lowest candidate volumes",
                "🔵 Both — Highest and lowest",
            ],
            index=0,
            key="centre_load_direction",
        )

        # ── Top N ────────────────────────────────────────────────────────────
        top_n_centre = st.radio(
            "How many centres should be included in each ranking?",
            options=[3, 5, 10, 15],
            index=1,
            horizontal=True,
            key="top_n_centre_select",
        )

        filter_values["LoadDirection"] = load_direction
        filter_values["TopN"] = top_n_centre


        ## ── REGISTRATION FORECAST ─────────────────────────────────────────────────────
        if "__FORECAST_HORIZON__" in required_filters:
            st.markdown("#### 📈 Forecast Configuration")
            st.markdown(
                "This report uses historical registration data to project future "
                "candidate volumes. Select how many years ahead to forecast."
                )

            horizon = st.radio(
                "Forecast horizon — how many years ahead?",
                options=[1, 3, 5, 10],
                index=1,
                horizontal=True,
                key="forecast_horizon",
                )

            filter_values["ForecastHorizon"] = horizon
            configured_filters.add("ForecastHorizon")

            years_opts = filter_options.get("ExamYear", [])
            effective_years = (
                list(years_opts)
                if st.session_state.get("all_years")
                else filter_values.get("ExamYear", [])
                )

            base_rec_count = get_record_count(
                exam_years=tuple(effective_years),
            )

            # Price scales with forecast horizon
            base_pricing   = calculate_report_price(
                {k: v for k, v in filter_values.items()
                 if k != "ForecastHorizon"}
                 )
            adjusted_price = base_pricing["price"] * horizon
            adjusted_fmt   = f"₦{adjusted_price:,}"

            with col_price:
                if not effective_years and not filter_values.get("ExamYear"):
                    st.markdown(
                        '<div class="pricing-panel">'
                        '<div class="pricing-panel-title">💰 Live Pricing</div>'
                        '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.9rem;'
                        'color:#94a3b8;padding:1rem 0;">Select at least one filter to see '
                        'your price estimate.</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                        st.markdown(
                            '<div class="pricing-panel">'
                            '<div class="pricing-panel-title">💰 Live Pricing</div>'
                            '<div class="price-display">' + adjusted_fmt + '</div>'
                            '<div class="price-label">Forecast: '
                            + str(horizon) + ' year'
                            + ('s' if horizon > 1 else '')
                            + ' ahead</div>'
                            '<div class="record-count-box" style="margin-top:0.8rem;">'
                            '📊 Historical base: <strong>'
                            + f"{base_rec_count:,}"
                            + '</strong> unique candidates</div>'
                            '<div style="margin-top:0.5rem;font-family:\'DM Sans\',sans-serif;'
                            'font-size:0.78rem;color:#94a3b8;">'
                            'Price scales with forecast horizon length.'
                            '</div>'
                            '</div>',
                            unsafe_allow_html=True,
                        )

                col_back_f, col_add_f = st.columns([1, 2])
                with col_back_f:
                        if st.button("← Back", key="forecast_back",
                                     use_container_width=True):
                            st.switch_page("pages/report_filters.py")
                            with col_add_f:
                                if st.button("＋ Add to Invoice", key="forecast_add",
                                             type="primary", use_container_width=True):
                                    fin_price = base_pricing["price"] * horizon
                                    report_item = {
                                        "report_group":  st.session_state.get("selected_group",    ""),
                                        "subgroup":      st.session_state.get("selected_subgroup", ""),
                                        "analysis":      selected_analysis,
                                        "filters":       filter_values,
                                        "record_count":  base_rec_count,
                                        "price":         fin_price,
                                        "price_fmt":     f"₦{fin_price:,}",
                                        "total_weight":  base_pricing["total_weight"] * horizon,
                                        }
                                    st.session_state.report_cart.append(report_item)
                                    st.session_state.invoice_ref = None
                                    st.success(
                                        f"✅ Added: **{selected_analysis}** — "
                                        f"₦{fin_price:,} ({horizon}-year forecast)"
                                        )
                                    _post_add_nav(st.session_state.report_cart)
                                    st.stop()

    # ── EFFECTIVE FILTERS FOR COUNTING ──────────────────────────────────────
    effective_years = tuple(selected_years)
    effective_states = tuple(selected_states)

    centre_rec_count = 0

    if selected_years or selected_states:
        centre_rec_count = get_record_count(
            exam_years=effective_years,
            states=effective_states,
        )


    # ── PRICING ──────────────────────────────────────────────────────────────
    pricing_filters = {}

    if selected_years:
        pricing_filters["ExamYear"] = selected_years

    if selected_states:
        pricing_filters["State"] = selected_states

    base_pricing = calculate_report_price(pricing_filters)

    multiplier = top_n_centre * (
        2 if "Both" in load_direction else 1
    )

    adjusted_price = base_pricing["price"] * multiplier
    adjusted_fmt = f"₦{adjusted_price:,}"

    direction_label = (
        "Highest & Lowest"
        if "Both" in load_direction
        else "Highest"
        if "Highest" in load_direction
        else "Lowest"
    )


    # ── RIGHT: LIVE PRICING ──────────────────────────────────────────────────
    with col_price:

        if not selected_years and not selected_states:

            st.markdown(
                '<div class="pricing-panel">'
                '<div class="pricing-panel-title">💰 Live Pricing</div>'
                '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.9rem;'
                'color:#94a3b8;padding:1rem 0;">'
                'Select at least one Exam Year or State to see your estimate.'
                '</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        else:

            both_note = " × 2 for both rankings" if "Both" in load_direction else ""

            st.markdown(
                '<div class="pricing-panel">'
                '<div class="pricing-panel-title">💰 Live Pricing</div>'
                '<div class="price-display">'
                + adjusted_fmt
                + '</div>'
                '<div class="price-label">'
                + direction_label
                + " — "
                + str(top_n_centre)
                + " centres"
                + both_note
                + '</div>'
                '<div class="record-count-box" style="margin-top:0.8rem;">'
                '📊 Candidates in selected scope: <strong>'
                + f"{centre_rec_count:,}"
                + '</strong>'
                '</div>'
                '<div style="margin-top:0.6rem;font-family:\'DM Sans\',sans-serif;'
                'font-size:0.78rem;color:#94a3b8;line-height:1.5;">'
                'The report will rank examination centres by unique candidate load '
                'within the selected year and State scope.'
                '</div>'
                '</div>',
                unsafe_allow_html=True,
            )


    # ── ACTION BUTTONS ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    col_back, col_add = st.columns([1, 2])

    with col_back:
        if st.button(
            "← Back",
            key="centre_load_back",
            use_container_width=True,
        ):
            st.switch_page("pages/report_filters.py")

    with col_add:

        if st.button(
            "＋ Add to Invoice",
            key="centre_load_add",
            type="primary",
            use_container_width=True,
        ):

            if not selected_years and not selected_states:
                st.error(
                    "❌ Select at least one Exam Year or State "
                    "before adding this report."
                )

            elif centre_rec_count == 0:
                st.error(
                    "❌ No candidates matched the selected scope. "
                    "Adjust your filters and try again."
                )

            else:

                saved_filters = {
                    "ExamYear": selected_years,
                    "State": selected_states,
                    "LoadDirection": load_direction,
                    "TopN": top_n_centre,
                }

                report_item = {
                    "id": len(st.session_state.report_cart) + 1,
                    "report_group": selected_main_group,
                    "subgroup": selected_subgroup,
                    "analysis": selected_analysis,
                    "filters": saved_filters,
                    "record_count": centre_rec_count,
                    "price": adjusted_price,
                    "price_fmt": adjusted_fmt,
                    "total_weight": (
                        base_pricing["total_weight"] * multiplier
                    ),
                    "weight_breakdown": base_pricing["filter_weights"],
                    "added_at": datetime.now().isoformat(),
                    "description": st.session_state.get(
                        "selected_analysis_description",
                        selected_analysis,
                    ),
                }

                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None

                st.success(
                    f"✅ Added **{selected_analysis}** — "
                    f"{direction_label}, {top_n_centre} centre"
                    f"{'s' if top_n_centre != 1 else ''} — "
                    f"{adjusted_fmt}"
                )

                _post_add_nav(st.session_state.report_cart)

    st.stop()
# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CASE: Age Range of Candidates
# ─────────────────────────────────────────────────────────────────────────────
if required_filters == ["__AGE_RANGE__"]:
    st.markdown(
    '''
    <div class="filter-section-title">
        Select Population Scope
    </div>

    <div style="
        font-size:0.95rem;
        color:#64748b;
        margin-top:-10px;
        margin-bottom:24px;
        line-height:1.6;
    ">
        This report automatically calculates candidate age ranges.
        The filters below simply define <strong>which candidates</strong>
        should be included in the analysis.
    </div>
    ''',
    unsafe_allow_html=True,
)
    years_all  = filter_options.get("ExamYear", [])
    states_all = filter_options.get("State", [])
    exam_types = filter_options.get("ExamType", [])
    age_groups = filter_options.get("AgeGroup", [])
    disabilities = filter_options.get("Disability", [])
    sponsors = filter_options.get("Sponsor", [])
    subjects = filter_options.get("Subject", [])
    grades = filter_options.get("Grade", [])
    statuses = filter_options.get("Status", [])
    

    col_f, col_p = st.columns([2.6, 1], gap="large")
    with col_f:
        all_yrs = st.checkbox("Include All Exam Years", value=False, key="ar_all_years")
        if all_yrs:
            ar_years = list(years_all)  # all available years
        else:
            ar_years = st.multiselect("Limit analysis to specific Exam Year(s)", years_all, key="ar_years")

        all_sts = st.checkbox("Include All States", value=False, key="ar_all_states")
        if all_sts:
            ar_states = list(states_all)  # all available states
        else:
            ar_states = st.multiselect("Limit analysis to specific State(s)", states_all, key="ar_states")

    ar_filters = {}
    if ar_years:
        ar_filters["ExamYear"] = ar_years
    if ar_states:
        ar_filters["State"] = ar_states

    # If "Include All" is ticked, pass ALL available categories
    effective_years  = tuple(years_all) if st.session_state.get("ar_all_years") else tuple(ar_years)
    effective_states = tuple(states_all)     if st.session_state.get("ar_all_states") else tuple(ar_states)

    rec_count = get_record_count(
        exam_years=effective_years,
        states=effective_states,
    )

    with col_p:
        ar_configured = bool(ar_years) or bool(ar_states) or \
                        st.session_state.get("ar_all_years") or \
                        st.session_state.get("ar_all_states")

        if not ar_configured:
            st.markdown(
                '<div class="pricing-panel">'
                '<div class="pricing-panel-title">💰 Live Pricing</div>'
                '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.9rem;'
                'color:#94a3b8;padding:1rem 0;">Select at least one filter to see '
                'your price estimate.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            effective_ar_filters = {}
            if effective_years:
                effective_ar_filters["ExamYear"] = list(effective_years)
            if effective_states:
                effective_ar_filters["State"] = list(effective_states)
            pricing = calculate_report_price(effective_ar_filters if effective_ar_filters else {"ExamYear": list(effective_years)}
                                             )
            st.markdown(
                '<div class="pricing-panel">'
                '<div class="pricing-panel-title">💰 Live Pricing</div>'
                '<div class="price-display">' + pricing["price_formatted"] + "</div>"
                '<div class="price-label">Estimated report price</div>'
                '<div class="record-count-box" style="margin-top:0.8rem;">📊 Matching: <strong>'
                + f"{rec_count:,}" + "</strong> records</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, _, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back_ar", width="stretch"):
            st.switch_page("pages/report_filters.py")
    with b3:
        if st.button("➕ Add to Invoice", key="add_ar", type="primary", width="stretch"):
            if rec_count == 0:
                st.error("❌ No records found. Adjust filters and try again.")
            else:
                final_pricing = calculate_report_price(
                    ar_filters if ar_filters else {"ExamYear": []}
                )
                save_f = {}
                if ar_years:
                    save_f["ExamYear"] = ar_years
                if ar_states:
                    save_f["State"] = ar_states
                # Empty dict = all data
                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          save_f,
                    "record_count":     rec_count,
                    "price":            final_pricing["price"],
                    "price_fmt":        final_pricing["price_formatted"],
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      selected_analysis,
                }
                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                st.success("✅ Added Age Range of Candidates report to invoice.")
                # st.balloons()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CASE: Cohort Tracking Across Years
# Age is calculated as ExamYear − year(DateOfBirth). Filters: ExamYear,
# Sex (optional), and an age range slider capped at 12–25.
# ─────────────────────────────────────────────────────────────────────────────
if required_filters == ["__COHORT_AGE__"]:
    st.markdown(
        '<div class="filter-section-title">Cohort Configuration</div>',
        unsafe_allow_html=True,
    )
    st.info(
        "ℹ️ Candidate age is calculated as **ExamYear − birth year** from the "
        "DateOfBirth column. Only candidates aged 12–25 are included by default."
    )

    col_f, col_p = st.columns([2.6, 1], gap="large")
    with col_f:
        years_all = filter_options.get("ExamYear", [])
        all_yrs   = st.checkbox("Include All Exam Years", value=False, key="cohort_all_years")
        if all_yrs:
            cohort_years = list(years_all)  # all available years
            configured_cohort = True
        else:
            cohort_years = st.multiselect(
                "📅 Select Exam Year(s)", years_all, key="cohort_years"
            )
            configured_cohort = bool(cohort_years)

        age_min, age_max = st.slider(
            "🎂 Age range to include (ExamYear − birth year)",
            min_value=5, max_value=40, value=(12, 25), key="cohort_age_range",
        )

        genders_all = filter_options.get("Sex", ["Male", "Female"])
        all_sex     = st.checkbox("Include All Genders", value=True, key="cohort_all_sex")
        if all_sex:
            cohort_sex = ["Male", "Female"]
        else:
            cohort_sex = st.multiselect("👤 Gender(s)", genders_all, key="cohort_sex")

    cohort_filters = {
        "ExamYear":       cohort_years,
        "Sex":            cohort_sex,
        "_age_min":       age_min,
        "_age_max":       age_max,
        "_age_computed":  True,   # signal to view_report to compute age
    }

    # Record count uses ExamYear + Sex only (age filter applied post-query)
    cohort_rec = get_record_count(
        exam_years=tuple(cohort_years),
        sex=tuple(cohort_sex),
    )

    with col_p:
        pricing = calculate_report_price({"ExamYear": cohort_years, "Sex": cohort_sex})
        st.markdown(
            '<div class="pricing-panel">'
            '<div class="pricing-panel-title">💰 Live Pricing</div>'
            '<div class="price-display">' + pricing["price_formatted"] + "</div>"
            '<div class="price-label">Estimated report price</div>'
            '<div class="record-count-box" style="margin-top:0.8rem;">📊 Base records: <strong>'
            + f"{cohort_rec:,}" + "</strong><br>"
            '<span style="font-size:0.78rem;color:#6b7280;">'
            "Age filter applied at render time</span></div>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, _, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back_cohort", width="stretch"):
            st.switch_page("pages/report_filters.py")
    with b3:
        if st.button("➕ Add to Invoice", key="add_cohort", type="primary", width="stretch"):
            if not configured_cohort and not all_yrs:
                st.error("❌ Please select at least one Exam Year or tick Include All.")
            elif cohort_rec == 0:
                st.error("❌ No records found for the selected years.")
            else:
                final_pricing = calculate_report_price(
                    {"ExamYear": cohort_years, "Sex": cohort_sex}
                )
                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          cohort_filters,
                    "record_count":     cohort_rec,
                    "price":            final_pricing["price"],
                    "price_fmt":        final_pricing["price_formatted"],
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      selected_analysis,
                }
                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                st.success(
                    "✅ Added Cohort Tracking report — ages "
                    + str(age_min) + "–" + str(age_max) + "."
                )
                # st.balloons()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CASE: Compulsory Subject Compliance
# Mathematics and English Language are pre-ticked and locked.
# User can optionally add extra subjects and filter by ExamYear.
# ─────────────────────────────────────────────────────────────────────────────
if required_filters == ["__COMPULSORY_SUBJECT__"]:
    st.markdown(
        '<div class="filter-section-title">Compulsory Subject Configuration</div>',
        unsafe_allow_html=True,
    )
    st.success(
        "✅ **Mathematics** and **English Language** are compulsory and always included."
    )

    col_f, col_p = st.columns([2.6, 1], gap="large")
    with col_f:
        years_all = filter_options.get("ExamYear", [])
        all_yrs   = st.checkbox("Include All Exam Years", value=False, key="cs_all_years")
        if all_yrs:
            cs_years = list(years_all)  # all available years
            cs_year_configured = True
        else:
            cs_years = st.multiselect(
                "📅 Select Exam Year(s)", years_all, key="cs_years"
            )
            cs_year_configured = bool(cs_years)

        # Build subject list — compulsory ones pre-selected and disabled via default
        all_subjects = filter_options.get("Subject", [])
        compulsory   = ["Mathematics", "English Language"]
        extra        = [s for s in all_subjects if s not in compulsory]

        st.markdown("**📚 Compulsory subjects (always included)**")
        for s in compulsory:
            st.checkbox(s, value=True, disabled=True, key=f"cs_lock_{s}")

        st.markdown("**➕ Add extra subjects (optional)**")
        extra_sel = st.multiselect(
            "Select additional subjects", extra, key="cs_extra_subjects"
        )

    final_subjects = compulsory + extra_sel

    cs_filters = {
        "ExamYear": cs_years,
        "Subject":  final_subjects,
    }

    cs_rec = get_record_count(
        exam_years=tuple(cs_years),
        subjects=tuple(final_subjects),
    )

    with col_p:
        pricing = calculate_report_price(cs_filters)
        st.markdown(
            '<div class="pricing-panel">'
            '<div class="pricing-panel-title">💰 Live Pricing</div>'
            '<div class="price-display">' + pricing["price_formatted"] + "</div>"
            '<div class="price-label">Estimated report price</div>'
            '<div class="record-count-box" style="margin-top:0.8rem;">📊 Matching: <strong>'
            + f"{cs_rec:,}" + "</strong> records</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, _, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back_cs", width="stretch"):
            st.switch_page("pages/report_filters.py")
    with b3:
        if st.button("➕ Add to Invoice", key="add_cs", type="primary", width="stretch"):
            if not cs_year_configured and not all_yrs:
                st.error("❌ Please select at least one Exam Year or tick Include All.")
            elif cs_rec == 0:
                st.error("❌ No records found. Adjust filters and try again.")
            else:
                final_pricing = calculate_report_price(cs_filters)
                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          cs_filters,
                    "record_count":     cs_rec,
                    "price":            final_pricing["price"],
                    "price_fmt":        final_pricing["price_formatted"],
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      selected_analysis,
                }
                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                st.success(
                    "✅ Added Compulsory Subject Compliance report — "
                    + str(len(final_subjects)) + " subjects."
                )
                # st.balloons()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CASE: Pass vs Fail Rate
# ─────────────────────────────────────────────────────────────────────────────
if required_filters == ["__PASS_FAIL__"]:
    st.markdown(
        '<div class="filter-section-title">Pass / Fail Configuration</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "Define which grades count as **pass** and which count as **fail**, "
        "then apply optional demographic filters below."
    )

    col_f, col_p = st.columns([2.6, 1], gap="large")
    with col_f:
        # Grade bucket selectors
        st.markdown("**✅ Pass Grades** — select which grades are counted as a pass")
        default_pass = ["A1","B2","B3","C4","C5","C6","D7","E8"]
        pf_pass = st.multiselect(
            "Pass grades", ["A1","B2","B3","C4","C5","C6","D7","E8"],
            default=default_pass, key="pf_pass_grades",
        )

        st.markdown("**❌ Fail Grades** — select which grades are counted as a fail")
        default_fail = ["F9"]
        pf_fail = st.multiselect(
            "Fail grades", ["D7","E8","F9"],
            default=default_fail, key="pf_fail_grades",
        )

        st.markdown("---")
        st.markdown("**Optional demographic filters**")

        years_all  = filter_options.get("ExamYear", [])
        all_yrs    = st.checkbox("Include All Exam Years", value=True, key="pf_all_years")
        pf_years   = list(years_all) if all_yrs else st.multiselect("📅 Exam Year(s)", years_all, key="pf_years")

        states_all = filter_options.get("State", [])
        all_sts    = st.checkbox("Include All States", value=True, key="pf_all_states")
        pf_states  = list(states_all) if all_sts else st.multiselect("🌍 State(s)", states_all, key="pf_states")

        genders_all = filter_options.get("Sex", ["Male","Female"])
        all_sex     = st.checkbox("Include All Genders", value=True, key="pf_all_sex")
        pf_sex      = ["Male", "Female"] if all_sex else st.multiselect("👤 Gender(s)", genders_all, key="pf_sex")

        exam_types_all = filter_options.get("ExamType", [])
        all_et         = st.checkbox("Include All Exam Types", value=True, key="pf_all_et")
        pf_et          = list(exam_types_all) if all_et else st.multiselect("📝 Exam Type(s)", exam_types_all, key="pf_et")

    # Build all selected grades to pass to query (pass + fail combined)
    all_selected_grades = list(dict.fromkeys(pf_pass + pf_fail))

    pf_filters = {
        "ExamYear":     pf_years,
        "State":        pf_states,
        "Sex":          pf_sex,
        "ExamType":     pf_et,
        "Grade":        all_selected_grades,
        # Private keys: tell view_report.py which grades are pass vs fail
        "_pass_grades": pf_pass,
        "_fail_grades": pf_fail,
    }

    effective_pf_years = tuple(years_all) if st.session_state.get("pf_all_years") else tuple(pf_years)
    effective_pf_states = tuple(states_all) if st.session_state.get("pf_all_states") else tuple(pf_states)
    effective_pf_sex = tuple(["Male", "Female"]) if st.session_state.get("pf_all_sex") else tuple(pf_sex)
    effective_pf_et = tuple(exam_types_all) if st.session_state.get("pf_all_et") else tuple(pf_et)
    effective_ar_gr = tuple(ALL_GRADES_OPTIONS) if st.session_state.get("pf_all_grades") else tuple(all_selected_grades)

    pf_rec = get_record_count(
        exam_years  = effective_pf_years,
        states      = effective_pf_states,
        sex         = effective_pf_sex,
        exam_types  = effective_pf_et,
        grades      = effective_ar_gr,
    )

    with col_p:
        # Only show price once user has interacted —
        # pf_pass and pf_fail always have defaults so check
        # if any optional demographic filter was also touched
        pf_configured = bool(pf_pass or pf_fail)
        if not pf_configured:
            st.markdown(
                '<div class="pricing-panel">'
                '<div class="pricing-panel-title">💰 Live Pricing</div>'
                '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.9rem;'
                'color:#94a3b8;padding:1rem 0;">Configure grade buckets to see '
                'your price estimate.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            pricing = calculate_report_price({"ExamYear": pf_years, "Grade": all_selected_grades})
            st.markdown(
                '<div class="pricing-panel">'
                '<div class="pricing-panel-title">💰 Live Pricing</div>'
                '<div class="price-display">' + pricing["price_formatted"] + "</div>"
                '<div class="price-label">Estimated report price</div>'
                '<div class="record-count-box" style="margin-top:0.8rem;">📊 Matching: <strong>'
                + f"{pf_rec:,}" + "</strong> records</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, _, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back_pf", width="stretch"):
            st.switch_page("pages/report_filters.py")
    with b3:
        if st.button("➕ Add to Invoice", key="add_pf", type="primary", width="stretch"):
            if not pf_pass and not pf_fail:
                st.error("❌ Please select at least one pass or fail grade.")
            elif pf_rec == 0:
                st.error("❌ No records found. Adjust filters and try again.")
            else:
                final_pricing = calculate_report_price(
                    {"ExamYear": pf_years, "Grade": all_selected_grades}
                )
                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          pf_filters,
                    "record_count":     pf_rec,
                    "price":            final_pricing["price"],
                    "price_fmt":        final_pricing["price_formatted"],
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      selected_analysis,
                }
                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                st.success(
                    "✅ Added Pass vs Fail report — "
                    + str(len(pf_pass)) + " pass grades, "
                    + str(len(pf_fail)) + " fail grades."
                )
                # st.balloons()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CASE: Best & Worst Performing Subjects
# User selects Top N (3, 5, or 10) and optional ExamYear filter.
# The _top_n private key is passed to view_report.py for chart rendering.
# ─────────────────────────────────────────────────────────────────────────────
if required_filters == ["__BEST_WORST_SUBJECTS__"]:
    st.markdown(
        '<div class="filter-section-title">Best & Worst Subjects Configuration</div>',
        unsafe_allow_html=True,
    )

    col_f, col_p = st.columns([2.6, 1], gap="large")
    with col_f:
        # Top N selector — the key requirement from the spec
        st.markdown("**🔢 How many subjects to show in each ranking?**")
        top_n = st.radio(
            "Select N",
            options=[3, 5, 10],
            index=1,        # default: 5
            horizontal=True,
            key="bw_top_n",
        )
        st.caption(
            f"Will show the **top {top_n}** (highest credit rate) "
            f"and **bottom {top_n}** (lowest credit rate) subjects."
        )

        st.markdown("---")
        years_all = filter_options.get("ExamYear", [])
        all_yrs   = st.checkbox("Include All Exam Years", value=False, key="bw_all_years")
        if all_yrs:
            bw_years = list(years_all)  # all available years
            bw_configured = True
        else:
            bw_years = st.multiselect("📅 Filter by Exam Year(s)", years_all, key="bw_years")
            bw_configured = bool(bw_years)

        states_all = filter_options.get("State", [])
        all_sts    = st.checkbox("Include All States", value=True, key="bw_all_states")
        bw_states  = list(states_all) if all_sts else st.multiselect("🌍 State(s)", states_all, key="bw_states")

    bw_filters = {
        "ExamYear": bw_years,
        "State":    bw_states,
        "_top_n":   top_n,   # private key read by view_report build_chart
    }

    effective_bw_years = tuple(years_all) if st.session_state.get("bw_all_years") else tuple(bw_years)
    effective_bw_states = tuple(states_all) if st.session_state.get("bw_all_states") else tuple(bw_states)

    bw_rec = get_record_count(
        exam_years = effective_bw_years,
        states     = effective_bw_states,
    )

    with col_p:
        # top_n doubles the effective report scope (top N + bottom N)
        # so multiply price weight by 2 when top_n >= 5
        bw_price_filters = {"ExamYear": bw_years, "State": bw_states}
        pricing = calculate_report_price(bw_price_filters)
        # Adjust price for double report (top + bottom)
        adjusted_price   = pricing["price"] * 2
        adjusted_fmt     = f"₦{adjusted_price:,}"
        st.markdown(
            '<div class="pricing-panel">'
            '<div class="pricing-panel-title">💰 Live Pricing</div>'
            '<div class="price-display">' + adjusted_fmt + "</div>"
            '<div class="price-label">Estimated report price (Top + Bottom ' + str(top_n) + ' subjects)</div>'
            '<div class="record-count-box" style="margin-top:0.8rem;">📊 Base records: <strong>'
            + f"{bw_rec:,}" + "</strong></div>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    b1, _, b3 = st.columns(3)
    with b1:
        if st.button("← Back", key="back_bw", width="stretch"):
            st.switch_page("pages/report_filters.py")
    with b3:
        if st.button("➕ Add to Invoice", key="add_bw", type="primary", width="stretch"):
            if not bw_configured and not all_yrs:
                st.error("❌ Please select at least one Exam Year or tick Include All.")
            elif bw_rec == 0:
                st.error("❌ No records found. Adjust filters and try again.")
            else:
                final_pricing = calculate_report_price(
                    {"ExamYear": bw_years, "State": bw_states}
                )
                adjusted_price   = final_pricing["price"] * 2
                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          bw_filters,
                    "record_count":     bw_rec,
                    "price":            adjusted_price,
                    "price_fmt":        f"₦{adjusted_price:,}",
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      selected_analysis,
                }
                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                st.success(
                    "✅ Added Best & Worst Subjects — top/bottom "
                    + str(top_n) + " subjects."
                )
                #st.balloons()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# STANDARD FILTER LAYOUT
#
# HOW "SELECT ALL" WORKS (fixes both bugs):
#
#   1. When "Include All X" checkbox is ticked:
#        filter_values[key] = []        ← empty list = no SQL WHERE clause
#        configured_filters.add(key)    ← marks this filter as actively set
#
#   2. When specific items are chosen:
#        filter_values[key] = [a, b]    ← SQL IN (a, b) clause
#        configured_filters.add(key)
#
#   3. Validation checks `configured_filters`, NOT whether values are non-empty.
#      So ticking "Include All" correctly passes validation.
#
#   4. get_record_count() receives empty tuples for "All" filters,
#      which means no WHERE clause → counts all records. No row limit. No OOM.
#
#   5. The cart stores filter_values as-is. view_report.py calls
#      load_report_data(filters) which also treats [] as "no clause".
# ─────────────────────────────────────────────────────────────────────────────
col_filters, col_price = st.columns([2.6, 1], gap="large")
filter_values: dict    = {}
configured_filters: set = set()

with col_filters:
    st.markdown(
        '<div class="filter-section-title">Select Filters</div>',
        unsafe_allow_html=True,
    )

    for filter_name in required_filters:

        if filter_name == "ExamYear":
            st.markdown("**📅 Select Exam Year(s)**")
            years   = filter_options.get("ExamYear", [])
            all_yrs = st.checkbox("Include All Years", value=False, key="all_years")
            if all_yrs:
                filter_values["ExamYear"] = list(years_all)  # all available years
                configured_filters.add("ExamYear")
            else:
                sel = st.multiselect(
                    "Select one or more years", years, key="exam_year",
                    help="Select multiple years to compare across time periods",
                )
                filter_values["ExamYear"] = sel
                if sel:
                    configured_filters.add("ExamYear")

        elif filter_name == "Sex":
            st.markdown("**👤 Select Gender(s)**")
            genders = filter_options.get("Sex", ["Male", "Female"])
            all_sex = st.checkbox("Include All Genders", value=False, key="all_sex")
            if all_sex:
                filter_values["Sex"] = ["Male", "Female"]  # all available genders
                configured_filters.add("Sex")
            else:
                sel = st.multiselect("Select one or more genders", genders, key="sex_select")
                filter_values["Sex"] = sel
                if sel:
                    configured_filters.add("Sex")

        elif filter_name == "AgeGroup":
            st.markdown("**🎂 Select Age Group(s)**")
            age_groups = filter_options.get("AgeGroup", [])
            if age_groups:
                all_ag = st.checkbox("Include All Age Groups", value=False, key="all_agegroup")
                if all_ag:
                    filter_values["AgeGroup"] = list(AGE_GROUPS_OPTIONS)  # all available age groups
                    configured_filters.add("AgeGroup")
                else:
                    sel = st.multiselect(
                        "Select one or more age groups", age_groups, key="agegroup_select",
                    )
                    filter_values["AgeGroup"] = sel
                    if sel:
                        configured_filters.add("AgeGroup")
            else:
                st.info("ℹ️ Age group data not available in this dataset.")
                filter_values["AgeGroup"] = []

        elif filter_name == "State":
            st.markdown("**🌍 Select State(s)**")
            states     = filter_options.get("State", [])
            all_states = st.checkbox("Include All States", value=False, key="all_states")
            if all_states:
                filter_values["State"] = list(states_all)  # all available states
                configured_filters.add("State")
            else:
                sel = st.multiselect("Select one or more states", states, key="state_select")
                filter_values["State"] = sel
                if sel:
                    configured_filters.add("State")

        elif filter_name == "Region":
            st.markdown("**🗺️ Select Geopolitical Region(s)**")

        
        elif filter_name == "centre":
            st.markdown("**🏫 Select Examination Centre(s)**")
            selected_states = filter_values.get("State", [])
            if selected_states:
                from Analytics_layer import query_exam_data as _qed
                centres_df = _qed(states=tuple(selected_states))
                centres    = (
                    sorted(centres_df["centre"].dropna().unique().tolist())
                    if not centres_df.empty else []
                )
                st.caption("Showing centres in: " + ", ".join(selected_states))
            else:
                centres = filter_options.get("centre", [])
                st.caption("Select a state first to filter centres by state.")

            all_centres = st.checkbox("Include All Centres", value=False, key="all_centres")
            if all_centres:
                filter_values["centre"] = list(centres)  # all available centres
                configured_filters.add("centre")
            elif centres:
                top_n_opts = {
                    "Manual selection": None,
                    "Top 2": 2, "Top 3": 3, "Top 5": 5, "Top 10": 10, "Top 20": 20,
                }
                top_label = st.selectbox(
                    "Quick-select top N centres by volume",
                    list(top_n_opts.keys()), key="top_n_centre",
                )
                top_n = top_n_opts[top_label]
                if top_n:
                    from Analytics_layer import query_exam_data as _qed2
                    scope_df = _qed2(
                        states=tuple(selected_states) if selected_states else ()
                    )
                    if not scope_df.empty:
                        top_list = (
                            scope_df.groupby("centre").size()
                            .sort_values(ascending=False)
                            .head(top_n).index.tolist()
                        )
                        filter_values["centre"] = top_list
                        configured_filters.add("centre")
                        st.success("✅ Auto-selected top " + str(top_n) + " centres")
                    else:
                        filter_values["centre"] = []
                else:
                    sel = st.multiselect(
                        "Select one or more centres", centres, key="centre_select"
                    )
                    filter_values["centre"] = sel
                    if sel:
                        configured_filters.add("centre")
            else:
                filter_values["centre"] = []

        elif filter_name == "Disability":
            st.markdown("**♿ Special Needs Status**")
            disabilities = filter_options.get("Disability", [])
            if disabilities:
                all_dis = st.checkbox("Include All", value=False, key="all_disability")
                if all_dis:
                    filter_values["Disability"] = list(disabilities)  # all available statuses
                    configured_filters.add("Disability")
                else:
                    sel = st.multiselect(
                        "Select one or more statuses", disabilities, key="disability_select"
                    )
                    filter_values["Disability"] = sel
                    if sel:
                        configured_filters.add("Disability")
            else:
                filter_values["Disability"] = []

        elif filter_name == "Sponsor":
            st.markdown("**💼 Select Sponsor(s)**")
            sponsors = filter_options.get("Sponsor", [])
            if sponsors:
                all_sp = st.checkbox("Include All Sponsors", value=False, key="all_sponsor")
                if all_sp:
                    filter_values["Sponsor"] = list(sponsors)  # all available sponsors
                    configured_filters.add("Sponsor")
                else:
                    sel = st.multiselect(
                        "Select one or more sponsors", sponsors, key="sponsor_select"
                    )
                    filter_values["Sponsor"] = sel
                    if sel:
                        configured_filters.add("Sponsor")
            else:
                filter_values["Sponsor"] = []

        elif filter_name == "ExamType":
            st.markdown("**📝 Select Exam Type(s)**")
            exam_types = filter_options.get("ExamType", [])
            if exam_types:
                all_et = st.checkbox("Include All Exam Types", value=False, key="all_examtype")
                if all_et:
                    filter_values["ExamType"] = list(exam_types)  # all available exam types
                    configured_filters.add("ExamType")
                else:
                    sel = st.multiselect(
                        "Select one or more exam types", exam_types, key="examtype_select"
                    )
                    filter_values["ExamType"] = sel
                    if sel:
                        configured_filters.add("ExamType")
            else:
                filter_values["ExamType"] = []

        elif filter_name == "Subject":
            st.markdown("**📚 Select Subject(s)**")
            subjects = filter_options.get("Subject", [])
            if subjects:
                all_sub = st.checkbox("Include All Subjects", value=False, key="all_subject")
                if all_sub:
                    filter_values["Subject"] = list(subjects)  # all available subjects
                    configured_filters.add("Subject")
                else:
                    sel = st.multiselect(
                        "Select one or more subjects", subjects, key="subject_select"
                    )
                    filter_values["Subject"] = sel
                    if sel:
                        configured_filters.add("Subject")
            else:
                filter_values["Subject"] = []

        elif filter_name == "Grade":
            st.markdown("**🏆 Select Grade(s)**")
            grades = filter_options.get("Grade", [])
            if grades:
                all_gr = st.checkbox("Include All Grades", value=False, key="all_grade")
                if all_gr:
                    filter_values["Grade"] = list(grades)  # all available grades
                    configured_filters.add("Grade")
                else:
                    sel = st.multiselect(
                        "Select one or more grades", grades, key="grade_select"
                    )
                    filter_values["Grade"] = sel
                    if sel:
                        configured_filters.add("Grade")
            else:
                filter_values["Grade"] = []

        elif filter_name == "Status":
            st.markdown("**✅ Select Status**")
            statuses = filter_options.get("Status", [])
            if statuses:
                all_st = st.checkbox("Include All Statuses", value=False, key="all_status")
                if all_st:
                    filter_values["Status"] = list(statuses)  # all available statuses
                    configured_filters.add("Status")
                else:
                    sel = st.multiselect(
                        "Select one or more statuses", statuses, key="status_select"
                    )
                    filter_values["Status"] = sel
                    if sel:
                        configured_filters.add("Status")
            else:
                filter_values["Status"] = []

    # ── Live record count ──────────────────────────────────────────────────────
    if configured_filters:
        record_count = get_record_count(
            exam_years = tuple(filter_values.get("ExamYear",   []) or []),
            states     = tuple(filter_values.get("State",      []) or []),
            sex        = tuple(filter_values.get("Sex",        []) or []),
            disability = tuple(filter_values.get("Disability", []) or []),
            sponsor    = tuple(filter_values.get("Sponsor",    []) or []),
            age_groups = tuple(filter_values.get("AgeGroup",   []) or []),
            centres    = tuple(filter_values.get("centre",     []) or []),
            exam_types = tuple(filter_values.get("ExamType",   []) or []),
            subjects   = tuple(filter_values.get("Subject",    []) or []),
            grades     = tuple(filter_values.get("Grade",      []) or []),
            statuses   = tuple(filter_values.get("Status",     []) or []),
        )
        st.markdown(
            '<div class="record-count-box">📊 Matching records: <strong>'
            + f"{record_count:,}" + "</strong></div>",
            unsafe_allow_html=True,
        )

# ── Live Pricing Panel ─────────────────────────────────────────────────────────
with col_price:
    if not configured_filters:
        st.markdown(
            '<div class="pricing-panel">'
            '<div class="pricing-panel-title">💰 Live Pricing</div>'
            '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.9rem;'
            'color:#94a3b8;padding:1rem 0;">Select at least one filter to see '
            'your price estimate.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        pricing          = calculate_report_price(filter_values)
        weight_rows_html = ""
        for fname, w in pricing["filter_weights"].items():
            if fname not in configured_filters:
                continue
            val   = filter_values.get(fname)
            label = fname + " (all)" if val == [] else fname + " (" + str(len(val)) + " sel.)"
            weight_rows_html += (
                '<div class="weight-row">'
                '<span class="weight-key">' + label + "</span>"
                '<span class="weight-val">× ' + str(w) + "</span></div>"
            )

        if not weight_rows_html:
            weight_rows_html = (
                "<div style=\"font-family:'DM Sans',sans-serif;font-size:0.85rem;"
                "color:#94a3b8;padding:0.5rem 0;\">Configure filters to see breakdown</div>"
            )

        st.markdown(
            '<div class="pricing-panel">'
            '<div class="pricing-panel-title">💰 Live Pricing</div>'
            '<div class="price-display">' + pricing["price_formatted"] + "</div>"
            '<div class="price-label">Estimated report price</div>'
            '<div style="margin-top:0.8rem">' + weight_rows_html + "</div>"
            '<div class="weight-total"><span>Total weight</span><span>'
            + str(pricing["total_weight"]) + "</span></div>"
            "<div style=\"margin-top:1rem;font-family:'DM Sans',sans-serif;"
            "font-size:0.78rem;color:#94a3b8;line-height:1.5;\">Price is the "
            "<strong>product</strong> of all filter weights mapped to a pricing tier.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

# ── Action Buttons ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
btn1, btn2, btn3 = st.columns(3)

with btn1:
    if st.button("← Back", key="back_btn", width="stretch"):
        st.switch_page("pages/report_filters.py")

with btn2:
    if st.button("🔄 Reset Filters", key="reset_btn", width="stretch"):
        st.rerun()

with btn3:
    if st.button("➕ Add to Invoice", key="add_to_cart_btn",
                 type="primary", width="stretch"):

        # ── VALIDATION ──────────────────────────────────────────────────────
        # configured_filters tracks every filter the user actively set
        # (either ticked "Include All" OR chose specific values).
        # An empty configured_filters means the user clicked nothing at all.
        if not configured_filters:
            st.error(
                "❌ Please configure at least one filter. "
                "Tick 'Include All' to include all available values, "
                "or select specific items."
            )
        else:
            try:
                # Fast COUNT — no raw rows, no OOM, works on 178M+ records
                record_count = get_record_count(
                    exam_years = tuple(filter_values.get("ExamYear",   []) or []),
                    states     = tuple(filter_values.get("State",      []) or []),
                    sex        = tuple(filter_values.get("Sex",        []) or []),
                    disability = tuple(filter_values.get("Disability", []) or []),
                    sponsor    = tuple(filter_values.get("Sponsor",    []) or []),
                    age_groups = tuple(filter_values.get("AgeGroup",   []) or []),
                    centres    = tuple(filter_values.get("centre",     []) or []),
                    exam_types = tuple(filter_values.get("ExamType",   []) or []),
                    subjects   = tuple(filter_values.get("Subject",    []) or []),
                    grades     = tuple(filter_values.get("Grade",      []) or []),
                    statuses   = tuple(filter_values.get("Status",     []) or []),
                )

                if record_count == 0:
                    st.error(
                        "❌ No records matched your filters. "
                        "Please adjust your selections and try again."
                    )
                    st.stop()

                # Only store filters the user actually configured
                saved_filters = {
                    k: v for k, v in filter_values.items()
                    if k in configured_filters
                }

                final_pricing = calculate_report_price(saved_filters)

                report_item = {
                    "id":               len(st.session_state.report_cart) + 1,
                    "report_group":     selected_main_group,
                    "subgroup":         selected_subgroup,
                    "analysis":         selected_analysis,
                    "filters":          saved_filters,
                    "record_count":     record_count,
                    "price":            final_pricing["price"],
                    "price_fmt":        final_pricing["price_formatted"],
                    "total_weight":     final_pricing["total_weight"],
                    "weight_breakdown": final_pricing["filter_weights"],
                    "added_at":         datetime.now().isoformat(),
                    "description":      st.session_state.get(
                        "selected_analysis_description", selected_analysis
                    ),
                }

                st.session_state.report_cart.append(report_item)
                st.session_state.invoice_ref = None   # force re-creation with updated cart
                st.success(
                    "✅ Added: **" + selected_analysis + "** — "
                    + final_pricing["price_formatted"]
                    + " (" + f"{record_count:,}" + " records)"
                )
                # st.balloons()

                # ── Post-add navigation ──────────────────────────────────
                cart_count_now = len(st.session_state.report_cart)
                cart_total_now = sum(
                    i.get("price", 0) for i in st.session_state.report_cart
                )
                st.markdown(
                    f"**📋 Invoice: {cart_count_now} report(s) · "
                    f"Total: ₦{cart_total_now:,}**"
                )
                nav1, nav2 = st.columns(2)
                with nav1:
                    if st.button(
                        "➕ Add Another Report",
                        key="post_add_more",
                        use_container_width=True,
                    ):
                        st.switch_page("pages/create_report.py")
                with nav2:
                    if st.button(
                        "📋 View Invoice & Checkout",
                        key="post_add_checkout",
                        type="primary",
                        use_container_width=True,
                    ):
                        if not st.session_state.get("invoice_ref"):
                            cart      = st.session_state.report_cart
                            total     = sum(item.get("price", 0) for item in cart)
                            data_dict = {
                                "reports": [
                                    {
                                        "report_group": item.get("report_group"),
                                        "subgroup":     item.get("subgroup"),
                                        "analysis":     item.get("analysis"),
                                        "filters":      item.get("filters", {}),
                                        "record_count": item.get("record_count", 0),
                                        "price":        item.get("price"),
                                        "total_weight": item.get("total_weight"),
                                    }
                                    for item in cart
                                ]
                            }
                            invoice_ref = create_invoice_record(
                                user_id=st.session_state.get("user_id", 0),
                                total=total,
                                data_dict=data_dict,
                            )
                            if invoice_ref:
                                st.session_state.invoice_ref = invoice_ref
                            else:
                                st.error("❌ Failed to create invoice. Please try again.")
                                st.stop()
                        st.switch_page("pages/view_invoice.py")

            except Exception as e:
                st.error("❌ Failed to process filters: " + str(e))

# ── Invoice Summary ────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

if st.session_state.report_cart:
    cart_total = sum(item.get("price", 0) for item in st.session_state.report_cart)
    st.markdown("---")
    st.markdown("### 📋 Current Invoice Summary")

    for item in st.session_state.report_cart:
        price_display = item.get("price_fmt") or ("₦" + str(item.get("price", 0)))
        rec_count     = item.get("record_count", 0)
        st.markdown(
            "- **" + item["analysis"] + "**"
            + " &nbsp;·&nbsp; " + f"{rec_count:,}" + " records"
            + " &nbsp;·&nbsp; **" + price_display + "**"
        )

    st.markdown("**Total: ₦" + f"{cart_total:,}" + "**")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Continue Adding Reports", key="continue_shopping", width="stretch"):
            st.switch_page("pages/create_report.py")
    with c2:
        if st.button("📋 View Invoice & Checkout", key="view_invoice_btn",
                     type="primary", width="stretch"):
            if not st.session_state.get("invoice_ref"):
                cart      = st.session_state.report_cart
                total     = sum(item.get("price", 0) for item in cart)
                data_dict = {
                    "reports": [
                        {
                            "report_group": item.get("report_group"),
                            "subgroup":     item.get("subgroup"),
                            "analysis":     item.get("analysis"),
                            "filters":      item.get("filters", {}),
                            "record_count": item.get("record_count", 0),
                            "price":        item.get("price"),
                            "total_weight": item.get("total_weight"),
                        }
                        for item in cart
                    ]
                }
                invoice_ref = create_invoice_record(
                    user_id=st.session_state.get("user_id", 0),
                    total=total,
                    data_dict=data_dict,
                )
                if invoice_ref:
                    st.session_state.invoice_ref = invoice_ref
                else:
                    st.error("❌ Failed to create invoice. Please try again.")
                    st.stop()
            st.switch_page("pages/view_invoice.py")
else:
    st.info("💡 Add reports to your invoice to proceed with checkout.")
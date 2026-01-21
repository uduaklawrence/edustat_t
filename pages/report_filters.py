import streamlit as st
from datetime import datetime

# ------------------ AUTH CHECK ------------------
if not st.session_state.get("logged_in", False):
    st.warning("Please sign in to view the report.")
    st.stop()

st.set_page_config(page_title="Select Filter Group", layout="wide")

# Load existing CSS
with open('styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Additional CSS
st.markdown("""
<style>
    /* Breadcrumb */
    .breadcrumb {
        font-size: 14px;
        color: var(--text-secondary);
        margin-bottom: 24px;
    }
    
    .breadcrumb a {
        color: var(--text-secondary);
        text-decoration: none;
    }
    
    .breadcrumb a:hover {
        color: var(--primary-blue);
    }
    
    /* Page Header */
    .filter-group-header {
        margin-bottom: 32px;
    }
    
    .filter-group-title {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }
    
    .filter-group-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
        line-height: 1.6;
        max-width: 900px;
    }
    
    /* Analysis Option Cards */
    .analysis-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 24px;
        margin-top: 40px;
    }
    
    .analysis-card {
        background: white;
        border-radius: 12px;
        padding: 28px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid var(--border-light);
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        min-height: 240px;
    }
    
    .analysis-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-4px);
        border-color: var(--accent-blue);
    }
    
    .analysis-card-title {
        font-size: 19px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 16px;
        min-height: 50px;
        display: flex;
        align-items: center;
    }
    
    .analysis-card-description {
        color: var(--text-secondary);
        font-size: 14px;
        line-height: 1.6;
        flex-grow: 1;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Check if a subgroup was selected
if 'selected_subgroup' not in st.session_state or st.session_state.selected_subgroup is None:
    st.error("❌ No subgroup selected. Please go back and select a report type.")
    if st.button("← Go Back"):
        st.switch_page("pages/create_report.py")
    st.stop()

selected_main_group = st.session_state.get("selected_main_group", "")
selected_subgroup = st.session_state.get("selected_subgroup", "")

# ------------------ ANALYSIS OPTIONS MAPPING ------------------
analysis_options = {
    # DEMOGRAPHIC ANALYSIS
    "Age Distribution Analysis": {
        "options": [
            ("Age Range of Candidates", "View youngest and oldest candidates, identifying age extremes in the dataset"),
            ("Age Distribution by Exam Year", "Analyze how candidate ages vary across different examination years"),
            ("Age Appropriateness Analysis", "Assess age suitability for different exam types and identify outliers"),
            ("Early/Late Enrollment Patterns", "Identify trends in early or delayed enrollment based on age data")
        ]
    },
    "Gender Equity Analysis": {
        "options": [
            ("Male-to-Female Ratio", "Calculate overall gender balance and identify disparities"),
            ("Gender Balance by Exam Year", "Track how gender distribution changes over examination years"),
            ("Gender Distribution by Exam Type", "Compare gender representation across school and private exams"),
            ("Gender Trends Over Time", "Visualize historical gender equity patterns and improvements")
        ]
    },
    "Special Needs & Disability Analysis": {
        "options": [
            ("Disability Inclusion Rate", "Calculate percentage of candidates with special needs"),
            ("Disability Trends by Year", "Track inclusion rates and changes over time"),
            ("Disability by Gender Distribution", "Analyze disability representation across male and female candidates"),
            ("Regional Disability Patterns", "Compare disability rates across different states and regions")
        ]
    },
    
    # GEOGRAPHIC & INSTITUTIONAL INSIGHTS
    "State-Level Distribution": {
        "options": [
            ("State Enrollment Rankings", "Identify top and bottom states by candidate volume"),
            ("Regional Access Patterns", "Map geographic disparities in education access"),
            ("State Trends Over Years", "Track enrollment growth or decline by state"),
            ("State Capacity Analysis", "Assess state-level educational infrastructure utilization")
        ]
    },
    "Centre/School Comparison": {
        "options": [
            ("Top Performing Centres", "Rank examination centres by candidate enrollment"),
            ("Centre Capacity Utilization", "Analyze how effectively centres are being used"),
            ("Centre Distribution by State", "Map centres across geographic regions"),
            ("School-to-School Comparison", "Compare individual institutions on key metrics")
        ]
    },
    "Origin Analysis": {
        "options": [
            ("Top Origin Locations", "Identify where most candidates originate from"),
            ("Local vs External Candidates", "Compare candidates from local vs external origins"),
            ("Migration Patterns", "Visualize candidate movement for education"),
            ("Origin Diversity Index", "Measure geographic diversity of candidate origins")
        ]
    },
    
    # EXAMINATION & ACADEMIC PERFORMANCE
    "Exam Type Analysis": {
        "options": [
            ("School vs Private Exam Distribution", "Compare volumes of school and private examinations"),
            ("Exam Type Preferences by Year", "Track how exam type choices change over time"),
            ("Exam Type by Gender", "Analyze gender differences in exam type selection"),
            ("Exam Type Regional Patterns", "Identify regional preferences for exam types")
        ]
    },
    "Subject Performance Analysis": {
        "options": [
            ("Most Popular Subjects", "Rank subjects by enrollment and identify trends"),
            ("Subject Difficulty Analysis", "Assess subject difficulty based on grade distributions"),
            ("Subject Preferences by Gender", "Identify gender-based subject selection patterns"),
            ("Subject Enrollment Trends", "Track how subject popularity changes over years")
        ]
    },
    "Grade Distribution Analysis": {
        "options": [
            ("Overall Grade Patterns", "View complete grade distribution across all candidates"),
            ("Pass/Fail Rate Analysis", "Calculate success rates and identify improvement areas"),
            ("Grade Trends by Subject", "Compare performance across different subjects"),
            ("Grade Performance by Year", "Track academic outcomes over examination years")
        ]
    },
    
    # TEMPORAL & PROGRESSION TRENDS
    "Year-over-Year Enrollment Trends": {
        "options": [
            ("Total Enrollment by Year", "Track overall candidate volumes across years"),
            ("Growth Rate Analysis", "Calculate year-on-year percentage changes"),
            ("Enrollment Forecasting", "Project future enrollment trends based on historical data"),
            ("Seasonal Enrollment Patterns", "Identify cyclical patterns in registration")
        ]
    },
    "Birth Cohort Analysis": {
        "options": [
            ("Birth Year Distribution", "Analyze candidate distribution by year of birth"),
            ("Age-Appropriate Enrollment", "Assess if candidates are enrolling at suitable ages"),
            ("Cohort Tracking", "Follow specific age groups through examination years"),
            ("Generational Education Trends", "Compare educational patterns across generations")
        ]
    },
    
    # CROSS-DIMENSIONAL ANALYSIS
    "Gender-Subject Preference": {
        "options": [
            ("Gender Bias in Subjects", "Identify male or female-dominated subject areas"),
            ("STEM Gender Gap Analysis", "Analyze gender representation in science subjects"),
            ("Subject Gender Balance Index", "Measure gender equity across all subjects"),
            ("Gender Preference Trends", "Track how gender-subject patterns change over time")
        ]
    },
    "Gender-Performance Analysis": {
        "options": [
            ("Gender Performance Gap", "Compare average grades between male and female candidates"),
            ("Subject-Specific Gender Performance", "Identify subjects where gender affects outcomes"),
            ("Gender Equity in Outcomes", "Assess fairness in academic achievement"),
            ("Performance Trends by Gender", "Track how gender performance gaps evolve")
        ]
    },
    "Age-Performance Correlation": {
        "options": [
            ("Optimal Age for Success", "Determine age ranges with best performance"),
            ("Over-Age Performance Analysis", "Assess outcomes for candidates above typical age"),
            ("Under-Age Performance Analysis", "Evaluate results for younger candidates"),
            ("Age-Grade Relationship", "Visualize correlation between age and grades")
        ]
    },
    "State-Performance Comparison": {
        "options": [
            ("State Performance Rankings", "Rank states by average academic outcomes"),
            ("Regional Performance Gaps", "Identify disparities between high and low-performing regions"),
            ("State Quality Indicators", "Assess state-level education quality metrics"),
            ("Performance Improvement Trends", "Track which states are improving over time")
        ]
    },
    "Disability-Performance Analysis": {
        "options": [
            ("Achievement Gap Analysis", "Measure performance differences for students with disabilities"),
            ("Disability Support Effectiveness", "Assess if support systems improve outcomes"),
            ("Inclusion Success Metrics", "Evaluate academic success of special needs students"),
            ("Disability Performance by Subject", "Identify subjects where disability impacts vary")
        ]
    },
    "Exam Type-Performance Analysis": {
        "options": [
            ("School vs Private Performance", "Compare grades between exam types"),
            ("Exam Type Standards Comparison", "Assess if grading standards differ"),
            ("Performance Trends by Exam Type", "Track outcome patterns over years"),
            ("Exam Type Success Rates", "Calculate pass rates for each exam type")
        ]
    },
    "Centre-Performance Rankings": {
        "options": [
            ("Best Performing Centres", "Identify top centres by academic outcomes"),
            ("Centre Quality Scorecard", "Create comprehensive centre performance metrics"),
            ("Centre Size vs Performance", "Analyze if centre size affects results"),
            ("Centre Improvement Tracking", "Monitor centres showing progress over time")
        ]
    },
    
    # STATISTICAL INSIGHTS
    "Descriptive Statistics": {
        "options": [
            ("Central Tendency Measures", "Calculate mean, median, and mode for key metrics"),
            ("Dispersion Analysis", "Assess variance and standard deviation patterns"),
            ("Quartile and Percentile Analysis", "Identify data distribution segments"),
            ("Outlier Detection", "Find anomalies and extreme values in the dataset")
        ]
    },
    "Correlation Analysis": {
        "options": [
            ("Grade Prediction Factors", "Identify which variables best predict academic success"),
            ("Variable Relationships", "Analyze correlations between different data points"),
            ("Performance Indicators", "Determine key factors associated with better outcomes"),
            ("Multi-Variable Analysis", "Examine complex relationships between multiple factors")
        ]
    }
}

# ------------------ BREADCRUMB ------------------
st.markdown(f"""
<div class="breadcrumb">
    <a href="#">Select Report Group</a> &gt; <strong>Select Filter Group</strong>
</div>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown(f"""
<div class="filter-group-header">
    <div class="filter-group-title">Select Filter Group</div>
    <div class="filter-group-subtitle">
        Choose a filter group from the {selected_subgroup.lower()} group to begin analyzing your data. 
        Each group provides specific filtering options tailored to that data type.
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------ DISPLAY ANALYSIS OPTIONS ------------------
if selected_subgroup in analysis_options:
    options = analysis_options[selected_subgroup]["options"]
    
    # Create grid of analysis cards
    num_cols = 3
    rows = [options[i:i+num_cols] for i in range(0, len(options), num_cols)]
    
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
                    # Save selected analysis
                    st.session_state.selected_analysis = title
                    st.session_state.selected_subgroup = selected_subgroup
                    st.session_state.selected_main_group = selected_main_group
                    
                    # Redirect to actual filter configuration page
                    st.switch_page("pages/configure_filters.py")
        
        # Fill empty columns in last row
        if len(row) < num_cols:
            for _ in range(num_cols - len(row)):
                cols[len(row)].empty()

else:
    st.error(f"❌ No analysis options found for '{selected_subgroup}'. Please go back and try again.")
    if st.button("← Go Back"):
        st.switch_page("pages/create_report.py")

# Back button
st.markdown("<br>", unsafe_allow_html=True)
if st.button("← Back to Report Selection"):
    st.switch_page("pages/create_report.py")
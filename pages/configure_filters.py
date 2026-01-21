import streamlit as st
import json
from datetime import datetime
from db_queries import (
    fetch_data,
    create_invoice_record,
)
from redis_cache import get_or_set_distinct_values

# ------------------ SETTINGS ------------------
SUBSCRIPTION_AMOUNT = 20000.00  # ₦

# ------------------ AUTH CHECK ------------------
if not st.session_state.get("logged_in", False):
    st.warning("Please sign in to view the report.")
    st.stop()

st.set_page_config(page_title="Select Filters", layout="wide")

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
    
    /* Page Header */
    .filter-header {
        margin-bottom: 32px;
    }
    
    .filter-title {
        font-size: 32px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }
    
    .filter-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    
    /* Info Box */
    .info-box {
        background: #fffbeb;
        border: 2px solid #fbbf24;
        border-radius: 8px;
        padding: 20px;
        margin: 30px 0;
        display: flex;
        gap: 16px;
    }
    
    .info-icon {
        font-size: 24px;
        color: #f59e0b;
    }
    
    .info-content h4 {
        margin: 0 0 8px 0;
        font-size: 16px;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .info-content p {
        margin: 4px 0;
        font-size: 14px;
        color: var(--text-secondary);
    }
    
    /* Filter Section */
    .filter-section-title {
        font-size: 24px;
        font-weight: 700;
        color: var(--text-primary);
        margin: 40px 0 24px 0;
    }
    
    /* Selected Filter Chips */
    .filter-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 16px;
    }
    
    .chip {
        background: #dc2626;
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    
    .chip-add {
        background: white;
        color: var(--text-secondary);
        border: 1px solid var(--border-light);
    }
    
    /* Action Buttons */
    .action-buttons {
        display: flex;
        justify-content: space-between;
        margin-top: 40px;
        padding-top: 30px;
        border-top: 2px solid var(--border-light);
    }
</style>
""", unsafe_allow_html=True)

user_email = st.session_state.get("user_email")
user_id = st.session_state.get("user_id", 0)

# Check if analysis was selected
if 'selected_analysis' not in st.session_state:
    st.error("❌ No analysis selected. Please go back and select an analysis type.")
    if st.button("← Go Back"):
        st.switch_page("pages/report_filters.py")
    st.stop()

selected_analysis = st.session_state.get("selected_analysis", "")
selected_subgroup = st.session_state.get("selected_subgroup", "")
selected_main_group = st.session_state.get("selected_main_group", "")

# ------------------ FILTER MAPPING ------------------
# Maps each analysis to its required filters
filter_mapping = {
    # Age Distribution Analysis
    "Age Range of Candidates": ["ExamYear", "Sex", "State"],
    "Age Distribution by Exam Year": ["ExamYear", "Sex", "Age"],
    "Age Appropriateness Analysis": ["ExamYear", "Age", "ExamType"],
    "Early/Late Enrollment Patterns": ["ExamYear", "Age", "Sex"],
    
    # Gender Equity Analysis
    "Male-to-Female Ratio": ["ExamYear", "Sex", "State"],
    "Gender Balance by Exam Year": ["ExamYear", "Sex"],
    "Gender Distribution by Exam Type": ["ExamYear", "Sex", "ExamType"],
    "Gender Trends Over Time": ["ExamYear", "Sex"],
    
    # Disability Analysis
    "Disability Inclusion Rate": ["ExamYear", "Disability", "Sex"],
    "Disability Trends by Year": ["ExamYear", "Disability"],
    "Disability by Gender Distribution": ["ExamYear", "Disability", "Sex"],
    "Regional Disability Patterns": ["ExamYear", "Disability", "State"],
    
    # State-Level Distribution
    "State Enrollment Rankings": ["ExamYear", "State", "Sex"],
    "Regional Access Patterns": ["ExamYear", "State"],
    "State Trends Over Years": ["ExamYear", "State"],
    "State Capacity Analysis": ["ExamYear", "State", "Centre"],
    
    # Centre/School Comparison
    "Top Performing Centres": ["ExamYear", "Centre", "State"],
    "Centre Capacity Utilization": ["ExamYear", "Centre"],
    "Centre Distribution by State": ["ExamYear", "Centre", "State"],
    "School-to-School Comparison": ["ExamYear", "Centre", "State"],
    
    # Origin Analysis
    "Top Origin Locations": ["ExamYear", "Origin", "State"],
    "Local vs External Candidates": ["ExamYear", "Origin"],
    "Migration Patterns": ["ExamYear", "Origin", "State"],
    "Origin Diversity Index": ["ExamYear", "Origin"],
    
    # Exam Type Analysis
    "School vs Private Exam Distribution": ["ExamYear", "ExamType", "Sex"],
    "Exam Type Preferences by Year": ["ExamYear", "ExamType"],
    "Exam Type by Gender": ["ExamYear", "ExamType", "Sex"],
    "Exam Type Regional Patterns": ["ExamYear", "ExamType", "State"],
    
    # Subject Performance
    "Most Popular Subjects": ["ExamYear", "Subject", "Sex"],
    "Subject Difficulty Analysis": ["ExamYear", "Subject", "Grade"],
    "Subject Preferences by Gender": ["ExamYear", "Subject", "Sex"],
    "Subject Enrollment Trends": ["ExamYear", "Subject"],
    
    # Grade Distribution
    "Overall Grade Patterns": ["ExamYear", "Grade", "Subject"],
    "Pass/Fail Rate Analysis": ["ExamYear", "Grade"],
    "Grade Trends by Subject": ["ExamYear", "Grade", "Subject"],
    "Grade Performance by Year": ["ExamYear", "Grade"],
    
    # Add more mappings as needed...
}

# Get required filters for selected analysis
required_filters = filter_mapping.get(selected_analysis, ["ExamYear"])

# Helper function to fetch distinct values
def fetch_distinct_from_db(column):
    try:
        if column == "Age":
            df = fetch_data("SELECT DISTINCT TIMESTAMPDIFF(YEAR, DateOfBirth, CURDATE()) AS Age FROM exam_candidates ORDER BY Age")
            return df["Age"].dropna().tolist()
        else:
            df = fetch_data(f"SELECT DISTINCT {column} FROM exam_candidates ORDER BY {column}")
            return df[column].dropna().tolist()
    except:
        return []

# ------------------ BREADCRUMB ------------------
st.markdown("""
<div class="breadcrumb">
    Select Report Group &gt; Select Filter Group &gt; <strong>Select Filters</strong>
</div>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown(f"""
<div class="filter-header">
    <div class="filter-title">Filter Your Data</div>
    <div class="filter-subtitle">
        Customize your {selected_analysis} report by selecting the filters below. Choose 
        multiple options to refine your insights.
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------ INFO BOX ------------------
st.markdown("""
<div class="info-box">
    <div class="info-icon">💡</div>
    <div class="info-content">
        <h4>Editable & Static Filters</h4>
        <p><strong>Editable filters</strong> are criteria that you can modify or select based on your preferences. You can choose different options within these filters to refine your report and extract specific data.</p>
        <p><strong>Static filters</strong> are predefined criteria that remain constant and cannot be modified.</p>
        <p>They ensure that certain aspects of the report are consistently included, providing a comprehensive view of the data.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------ FILTER SECTION ------------------
st.markdown('<div class="filter-section-title">Select Filters</div>', unsafe_allow_html=True)

# Initialize filter values
filter_values = {}

# Display filters based on required_filters
for filter_name in required_filters:
    if filter_name == "ExamYear":
        st.markdown("**Select Exam Year**")
        cache_key = "distinct:ExamYear"
        years = get_or_set_distinct_values(cache_key, lambda: fetch_distinct_from_db("ExamYear"))
        filter_values["ExamYear"] = st.selectbox(
            "Select Year",
            ["Please select a filter..."] + years,
            key="exam_year",
            label_visibility="collapsed"
        )
    
    elif filter_name == "Sex":
        st.markdown("**Select Gender**")
        selected_genders = []
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Male ✕" if "Male" in st.session_state.get("selected_genders", []) else "Male +", 
                        key="male_btn", use_container_width=True):
                if "selected_genders" not in st.session_state:
                    st.session_state.selected_genders = []
                if "Male" in st.session_state.selected_genders:
                    st.session_state.selected_genders.remove("Male")
                else:
                    st.session_state.selected_genders.append("Male")
                st.rerun()
        
        with col2:
            if st.button("Female +" if "Female" not in st.session_state.get("selected_genders", []) else "Female ✕",
                        key="female_btn", use_container_width=True):
                if "selected_genders" not in st.session_state:
                    st.session_state.selected_genders = []
                if "Female" in st.session_state.selected_genders:
                    st.session_state.selected_genders.remove("Female")
                else:
                    st.session_state.selected_genders.append("Female")
                st.rerun()
        
        with col3:
            if st.button("Prefer not to say +", key="prefer_btn", use_container_width=True):
                pass
        
        filter_values["Sex"] = st.session_state.get("selected_genders", [])
    
    elif filter_name == "Age":
        st.markdown("**Select Age Category**")
        selected_ages = []
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Under 18 ✕" if "Under 18" in st.session_state.get("selected_ages", []) else "Under 18 +",
                        key="under18_btn", use_container_width=True):
                if "selected_ages" not in st.session_state:
                    st.session_state.selected_ages = []
                if "Under 18" in st.session_state.selected_ages:
                    st.session_state.selected_ages.remove("Under 18")
                else:
                    st.session_state.selected_ages.append("Under 18")
                st.rerun()
        
        with col2:
            if st.button("Above 18 +" if "Above 18" not in st.session_state.get("selected_ages", []) else "Above 18 ✕",
                        key="above18_btn", use_container_width=True):
                if "selected_ages" not in st.session_state:
                    st.session_state.selected_ages = []
                if "Above 18" in st.session_state.selected_ages:
                    st.session_state.selected_ages.remove("Above 18")
                else:
                    st.session_state.selected_ages.append("Above 18")
                st.rerun()
        
        with col3:
            if st.button("All age groups +", key="all_ages_btn", use_container_width=True):
                st.session_state.selected_ages = ["Under 18", "Above 18"]
                st.rerun()
        
        filter_values["Age"] = st.session_state.get("selected_ages", [])
    
    elif filter_name == "Centre":
        st.markdown("**Select School**")
        all_schools_selected = st.session_state.get("all_schools", False)
        
        if st.button("All Schools are inclusive for this report ✕" if all_schools_selected else "All Schools are inclusive for this report +",
                    key="all_schools_btn"):
            st.session_state.all_schools = not all_schools_selected
            st.rerun()
        
        filter_values["Centre"] = "All" if all_schools_selected else []
    
    elif filter_name == "Subject":
        st.markdown("**Select Subject**")
        cache_key = "distinct:Subject"
        subjects = get_or_set_distinct_values(cache_key, lambda: fetch_distinct_from_db("Subject"))
        
        # Display selected subjects as chips
        selected_subjects = st.session_state.get("selected_subjects", [])
        if selected_subjects:
            cols = st.columns(len(selected_subjects) + 1)
            for idx, subj in enumerate(selected_subjects):
                with cols[idx]:
                    st.markdown(f'<div class="chip">{subj} ✕</div>', unsafe_allow_html=True)
        
        # Dropdown to add more subjects
        new_subject = st.selectbox(
            "Add Subject",
            ["Please select a filter..."] + [s for s in subjects if s not in selected_subjects],
            key="subject_select",
            label_visibility="collapsed"
        )
        
        if new_subject != "Please select a filter..." and new_subject not in selected_subjects:
            if "selected_subjects" not in st.session_state:
                st.session_state.selected_subjects = []
            st.session_state.selected_subjects.append(new_subject)
            st.rerun()
        
        filter_values["Subject"] = selected_subjects
    
    elif filter_name == "State":
        st.markdown("**Select State**")
        cache_key = "distinct:State"
        states = get_or_set_distinct_values(cache_key, lambda: fetch_distinct_from_db("State"))
        filter_values["State"] = st.selectbox(
            "Select State",
            ["Please select a filter..."] + states,
            key="state_select",
            label_visibility="collapsed"
        )
    
    elif filter_name == "Disability":
        st.markdown("**Special Needs Type**")
        disability_options = ["None", "Physical Disability", "Learning Disability", "Other"]
        filter_values["Disability"] = st.selectbox(
            "Select Special Needs",
            ["Please select a filter..."] + disability_options,
            key="disability_select",
            label_visibility="collapsed"
        )
    
    elif filter_name == "ExamType":
        st.markdown("**Select Exam Type**")
        exam_types = ["School Exams", "Private Examination"]
        filter_values["ExamType"] = st.selectbox(
            "Select Exam Type",
            ["Please select a filter..."] + exam_types,
            key="exam_type_select",
            label_visibility="collapsed"
        )
    
    elif filter_name == "Grade":
        st.markdown("**Select Grade**")
        grades = ["A1", "B2", "B3", "C4", "C5", "C6", "D7", "E8", "F9"]
        filter_values["Grade"] = st.multiselect(
            "Select Grades",
            grades,
            key="grade_select"
        )
    
    elif filter_name == "Origin":
        st.markdown("**Select Origin**")
        cache_key = "distinct:Origin"
        origins = get_or_set_distinct_values(cache_key, lambda: fetch_distinct_from_db("Origin"))
        filter_values["Origin"] = st.selectbox(
            "Select Origin",
            ["Please select a filter..."] + origins,
            key="origin_select",
            label_visibility="collapsed"
        )

# ------------------ ACTION BUTTONS ------------------
st.markdown('<div class="action-buttons">', unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("🔄 Reset Filters", key="reset_btn", use_container_width=True):
        # Clear all session state filters
        for key in list(st.session_state.keys()):
            if key.startswith("selected_") or key in ["all_schools"]:
                del st.session_state[key]
        st.rerun()

with col2:
    if st.button("📊 Apply Filters & View Invoice", key="apply_btn", type="primary", use_container_width=True):
        # Validate that at least some filters are selected
        valid_filters = {k: v for k, v in filter_values.items() 
                        if v and v != "Please select a filter..." and v != []}
        
        if not valid_filters:
            st.error("❌ Please select at least one filter before proceeding.")
        else:
            # Prepare report payload
            report_payload = {
                "report_group": selected_main_group,
                "subgroup": selected_subgroup,
                "analysis": selected_analysis,
                "filters": filter_values,
                "charts": ["Table/Matrix", "Bar Chart"],  # Default charts
                "created_at": datetime.now().isoformat(),
            }
            
            try:
                # Ensure user_id exists
                if not user_id or user_id == 0:
                    user_df = fetch_data(f"SELECT user_id FROM users WHERE email_address='{user_email}' LIMIT 1")
                    if not user_df.empty:
                        user_id = int(user_df["user_id"].iloc[0])
                        st.session_state.user_id = user_id
                
                # Create invoice
                invoice_ref = create_invoice_record(
                    user_id=user_id,
                    total=int(SUBSCRIPTION_AMOUNT),
                    data_dict=report_payload,
                )
                
                if invoice_ref:
                    # Save to session state
                    st.session_state.invoice_ref = invoice_ref
                    st.session_state.saved_group = selected_main_group
                    st.session_state.saved_subgroup = selected_subgroup
                    st.session_state.saved_analysis = selected_analysis
                    st.session_state.saved_filters = filter_values
                    st.session_state.saved_charts = ["Table/Matrix", "Bar Chart"]
                    st.session_state.pending_invoice_saved = True
                    st.session_state.payment_verified = False
                    
                    # Redirect to invoice page
                    st.success("✅ Invoice created successfully!")
                    st.switch_page("pages/view_invoice.py")
                else:
                    st.error("❌ Failed to create invoice. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

st.markdown('</div>', unsafe_allow_html=True)

# Back button
st.markdown("<br>", unsafe_allow_html=True)
if st.button("← Back to Analysis Selection"):
    st.switch_page("pages/report_filters.py")
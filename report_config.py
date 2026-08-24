# ------------------ COMPLETE REPORT STRUCTURE ------------------
report_structure = {
    "Demographic Analysis": {
        "icon": "👥",
        "subgroups": {
            "Age Distribution & Group Segmentation": "Analyzes the spread of candidates across age groups, identifying the youngest, oldest, and most dominant age brackets. Highlights whether candidates fall within expected school-age ranges or show signs of over-age or under-age registration.",
            "Gender Equity Analysis": "Measures the male-to-female ratio across the entire dataset and tracks whether gender balance is improving or declining over exam years. Flags states, subjects, or centres where gender disparity is most pronounced.",
            "Birth Cohort Analysis": "Groups candidates by birth year to understand which generations are sitting for exams and whether older cohorts are re-sitting. Reveals patterns in delayed education or repeated examination attempts across birth years.",
            "Disability & Special Needs Profile": "Quantifies the number and proportion of candidates registered with a disability. Breaks down disability representation by gender, age group, state, and exam year to understand inclusion trends across the dataset."
        }
    },
    "Geographic & Regional Analysis": {
        "icon": "🗺️",
        "subgroups": {
            "Centre Statistics, Capacity and Load Analysis":
            "Analyses examination centre distribution, candidate load per centre, "
            "and areas where candidate demand may be high relative to available "
            "examination centres.",

        "State Candidate Volume Analysis":
            "Examines candidate registration volumes across states, identifying "
            "the highest and lowest contributing states, registration trends, "
            "state comparisons, and year-on-year growth patterns.",
        }
    },
    "Registration & Enrollment Patterns": {
        "icon": "📋",  # ← trailing space removed from key
        "subgroups": {
            "Overall Registration Metrics & Trends": "Provides a high-level count of total registrations per exam year, tracking growth, decline, or stagnation in participation over time. Serves as the baseline headcount report for the entire dataset.",
            "Subject Enrollment & Combination Patterns": "Examines which subjects candidates register for most frequently and which subject combinations are most common. Identifies compulsory subject compliance and popular elective pairings.",
            "Sponsor & Institutional Registration Breakdown": "Analyzes who is sponsoring candidates — private individuals, schools, or government institutions — and how sponsorship type relates to volume of registration, state, and exam type.",
            "Registration by Demographic": "Breaks down total registrations by age group, gender, and disability status to show whether certain demographic groups are over- or under-represented in the registration pool."
        }
    },
    "Examination Administration": {
        "icon": "📝",
        "subgroups": {
            "Exam Type Distribution": "Compares the volume of candidates registered across different examination types (e.g., WASSCE, GCE, Private), showing which exam type dominates and how the mix shifts across years and states.",
            "Centre Statistics, Capacity & Load Analysis": "Reports on the number of active centres per state and region, estimates candidate load per centre, and flags centres that may be over-capacity or underutilized relative to the candidate population they serve.",
            "Centre Performance Rankings": "Ranks centres based on candidate outcomes, identifying consistently high-performing and low-performing centres. Provides a basis for resource allocation and quality assurance decisions.",
            "Examination Attendance & Absenteeism": "Measures the gap between registered candidates and those who actually sat for the exam. Identifies states, centres, exam types, and demographic groups with the highest rates of absenteeism or non-completion."
        }
    },
    "Academic Performance Analysis": {
        "icon": "📊",
        "subgroups": {
            "Overall Grade Distribution": "Presents the full breakdown of grades awarded across all candidates — from distinctions to failures — giving a system-wide picture of academic achievement and failure rates.",
            "Credit & Pass Requirement Analysis": "Measures how many candidates meet the minimum credit thresholds typically required for tertiary admission (e.g., 5 credits including English and Mathematics). Tracks this pass rate over exam years.",
            "Subject Performance Comparison": "Compares average grades and pass rates across all subjects to identify which subjects candidates perform best and worst in system-wide, forming the basis for curriculum and teaching quality discussions.",
            "Performance by Gender, Age Group & Disability": "Disaggregates performance results by key demographic variables to determine whether gender, age, or disability status has a statistically meaningful relationship with academic outcomes.",
            "State & Regional Performance Comparison": "Ranks states and regions by candidate performance metrics, revealing geographic inequalities in educational outcomes and identifying states that consistently outperform or underperform the national average.",
            "Exam Type Performance Comparison": "Compares grade distributions and pass rates across exam types to determine whether candidates sitting different exam variants achieve comparable outcomes or show systematic differences."
        }
    },
    "Subject Intelligence": {
        "icon": "📚",
        "subgroups": {
            "Subject Popularity & Enrollment Statistics": "Ranks all subjects by total number of registrations, tracking which subjects are growing or declining in popularity over exam years. Highlights niche subjects at risk of discontinuation.",
            "Subject-Gender & Subject-Age Demographic Breakdown": "Examines the demographic composition of each subject's candidate pool, revealing gender-dominated subjects, age skews within subjects, and whether demographic participation in subjects is shifting over time.",
            "High vs. Low Performing Subjects": "Identifies subjects with consistently high pass and credit rates versus those with persistently poor outcomes. Provides a ranked view of subject difficulty or teaching effectiveness across the system.",
            "Rare & Declining Subject Trends": "Tracks subjects with very low enrollment or a year-on-year decline in registration, flagging subjects that may be at risk of being phased out or that require targeted intervention to sustain participation."
        }
    },
    "Temporal Trends & Forecasting": {
        "icon": "📈",
        "subgroups": {
            "Year-over-Year Enrollment & Registration Trends": "Tracks total and segmented registration figures across all available exam years, identifying periods of rapid growth, decline, or stagnation and linking them to observable contextual factors where possible.",
            "Performance Trends Over Time": "Monitors how key performance metrics — pass rates, credit attainment, grade distributions — have evolved across exam years, revealing whether the system is improving, declining, or plateauing.",
            "Growth Rate Analysis by State, Subject & Gender": "Calculates compound or annual growth rates for registration and performance at a granular level, identifying which states, subjects, and gender groups are growing fastest or falling behind over time.",
            "Forecasting & Projection Models": "Uses historical trend data to project future registration volumes, pass rates, and demographic compositions. Provides data-driven estimates to support planning for infrastructure, staffing, and resource allocation."
        }
    },
    "Statistical Summaries & Advanced Analytics": {
        "icon": "🧠",
        "subgroups": {
            "Descriptive Statistics Summary": "Produces key statistical measures — mean, median, mode, standard deviation, and range — for numerical variables such as age and grade scores, providing a mathematical baseline profile of the dataset.",
            "Correlation Analysis": "Investigates statistical relationships between variables, such as whether age correlates with performance, whether state of origin influences grade outcomes, or whether disability status relates to subject choice patterns.",
            "Distribution & Normality Analysis": "Examines how key variables such as age, grades, and enrollment figures are distributed across the dataset, testing whether distributions are normal, skewed, or bimodal and what that implies for the population.",
            "Multivariate & Segmentation Analysis": "Applies multi-dimensional analysis to segment candidates into meaningful clusters based on combinations of variables — such as age, gender, state, subject, and performance — to uncover hidden patterns not visible in single-variable reports."
        }
    }
}
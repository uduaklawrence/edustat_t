import streamlit as st

# ------------ SESSION DEFAULTS ------------
st.set_page_config(page_title="Edustat – Educational Intelligence", layout="wide", initial_sidebar_state="collapsed")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ------------ CUSTOM CSS ------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

.main { background: #f5f7fa; padding: 0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Nav ── */
.nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.2rem 4rem;
    background: #fff;
    border-bottom: 1px solid #e8ecf0;
    position: sticky;
    top: 0;
    z-index: 100;
}
.nav-brand {
    font-family: 'Playfair Display', serif;
    font-size: 1.6rem;
    font-weight: 900;
    color: #1a2744;
    letter-spacing: -0.5px;
}
.nav-brand span { color: #2563eb; }
.nav-links { display: flex; gap: 2rem; align-items: center; }
.nav-links a {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    font-weight: 500;
    color: #4b5563;
    text-decoration: none;
}
.nav-badge {
    background: #dbeafe;
    color: #1d4ed8;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    letter-spacing: 0.03em;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #1a2744 100%);
    padding: 5rem 4rem 4rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -100px; right: -100px;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%);
    border-radius: 50%;
}
.hero::after {
    content: '';
    position: absolute;
    bottom: -80px; left: -80px;
    width: 350px; height: 350px;
    background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-inner {
    max-width: 900px;
    margin: 0 auto;
    position: relative;
    z-index: 2;
    text-align: center;
}
.hero-tag {
    display: inline-block;
    background: rgba(59,130,246,0.2);
    border: 1px solid rgba(59,130,246,0.4);
    color: #93c5fd;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.4rem 1.2rem;
    border-radius: 30px;
    margin-bottom: 1.5rem;
}
.hero h1 {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2.4rem, 5vw, 3.8rem);
    font-weight: 900;
    color: #fff;
    line-height: 1.15;
    margin-bottom: 1.2rem;
    letter-spacing: -1px;
}
.hero h1 em { color: #60a5fa; font-style: normal; }
.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    color: #94a3b8;
    line-height: 1.7;
    margin-bottom: 2.5rem;
    max-width: 620px;
    margin-left: auto;
    margin-right: auto;
}
.hero-cta {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
}
.btn-primary {
    background: #2563eb;
    color: #fff;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 0.85rem 2rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: inline-block;
}
.btn-primary:hover { background: #1d4ed8; transform: translateY(-1px); }
.btn-outline {
    background: transparent;
    color: #e2e8f0;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    padding: 0.85rem 2rem;
    border-radius: 8px;
    border: 1.5px solid rgba(255,255,255,0.25);
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: inline-block;
}
.btn-outline:hover { border-color: rgba(255,255,255,0.6); transform: translateY(-1px); }

/* ── Stats bar ── */
.stats-bar {
    background: #fff;
    border-bottom: 1px solid #e8ecf0;
    padding: 1.8rem 4rem;
}
.stats-inner {
    display: flex;
    justify-content: center;
    gap: 4rem;
    max-width: 900px;
    margin: 0 auto;
}
.stat-item { text-align: center; }
.stat-num {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #1a2744;
    line-height: 1;
}
.stat-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    color: #6b7280;
    margin-top: 0.3rem;
    font-weight: 500;
}
.stat-divider {
    width: 1px;
    background: #e5e7eb;
    align-self: stretch;
}

/* ── Section ── */
.section { padding: 4rem; }
.section-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #2563eb;
    margin-bottom: 0.6rem;
}
.section-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.8rem;
    line-height: 1.2;
}
.section-body {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    color: #4b5563;
    line-height: 1.7;
    max-width: 520px;
}

/* ── Feature Grid ── */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    max-width: 1100px;
    margin: 3rem auto 0;
}
.feat-card {
    background: #fff;
    border-radius: 16px;
    padding: 2rem;
    border: 1px solid #e8ecf0;
    transition: box-shadow 0.2s, transform 0.2s;
}
.feat-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.09);
    transform: translateY(-3px);
}
.feat-icon {
    font-size: 2rem;
    margin-bottom: 1rem;
    display: block;
}
.feat-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.6rem;
}
.feat-desc {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    color: #6b7280;
    line-height: 1.6;
}

/* ── Audience strip ── */
.audience {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    padding: 4rem;
}
.audience-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: #fff;
    text-align: center;
    margin-bottom: 0.6rem;
}
.audience-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    color: #94a3b8;
    text-align: center;
    margin-bottom: 2.5rem;
}
.audience-cards {
    display: flex;
    gap: 1.5rem;
    justify-content: center;
    flex-wrap: wrap;
}
.aud-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    padding: 1.8rem 2rem;
    width: 220px;
    text-align: center;
    transition: background 0.2s;
}
.aud-card:hover { background: rgba(255,255,255,0.12); }
.aud-icon { font-size: 2rem; margin-bottom: 0.8rem; display: block; }
.aud-name {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.4rem;
}
.aud-desc {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.5;
}

/* ── CTA bottom ── */
.cta-section {
    background: #f0f4ff;
    padding: 4rem;
    text-align: center;
    border-top: 1px solid #dbeafe;
}
.cta-section h2 {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.8rem;
}
.cta-section p {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    color: #4b5563;
    margin-bottom: 2rem;
}

/* ── Streamlit button overrides ── */
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 0.75rem 2rem !important;
    font-size: 0.95rem !important;
    transition: all 0.2s !important;
    border: none !important;
}
div[data-testid="column"]:nth-child(1) .stButton > button {
    background: #2563eb !important;
    color: white !important;
}
div[data-testid="column"]:nth-child(2) .stButton > button {
    background: transparent !important;
    color: #2563eb !important;
    border: 2px solid #2563eb !important;
}
.stButton > button:hover { transform: translateY(-2px) !important; }

.waec-notice {
    background: #fefce8;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 1rem 1.5rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    color: #92400e;
    text-align: center;
    max-width: 700px;
    margin: 0 auto 2rem;
}
</style>
""", unsafe_allow_html=True)

# ── NAV ──
st.markdown("""
<div class="nav">
    <div class="nav-brand">Edu<span>stat</span></div>
    <div class="nav-links">
        <a href="#">Features</a>
        <a href="#">About WAEC</a>
        <a href="#">Pricing</a>
        <span class="nav-badge">By WAEC Nigeria</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── HERO ──
st.markdown("""
<div class="hero">
    <div class="hero-inner">
        <div class="hero-tag">🎓 Nigeria's Premier Educational Intelligence Platform</div>
        <h1>Make <em>data-driven</em> decisions for Nigerian education</h1>
        <p class="hero-sub">
            Edustat gives researchers, institutions, government agencies, and educators 
            deep access to WAEC examination records — from candidate demographics to 
            performance trends across all 36 states.
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── HERO BUTTONS (Streamlit) ──
st.markdown('<div style="background:linear-gradient(135deg,#0f172a,#1e3a8a);padding:0 4rem 4rem;display:flex;justify-content:center;">', unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    bc1, bc2, bc3 = st.columns([2, 1.2, 1.2, 2][1:3] + [2], gap="small")
    # center hack
    _, c1, c2, _ = st.columns([3, 2, 2, 3])
    with c1:
        if st.button("🚀 Get Started — Sign Up", use_container_width=True, key="hero_signup"):
            st.switch_page("pages/sign_up.py")
    with c2:
        if st.button("🔑 Login to Dashboard", use_container_width=True, key="hero_login"):
            st.switch_page("pages/Login.py")
else:
    _, c1, c2, _ = st.columns([3, 2, 2, 3])
    with c1:
        if st.button("📊 Go to Dashboard", use_container_width=True, key="hero_dash"):
            st.switch_page("pages/dashboard.py")
    with c2:
        if st.button("📄 Create New Report", use_container_width=True, key="hero_report"):
            st.switch_page("pages/create_report.py")

st.markdown('</div>', unsafe_allow_html=True)

# ── STATS BAR ──
st.markdown("""
<div class="stats-bar">
    <div class="stats-inner">
        <div class="stat-item">
            <div class="stat-num">36+</div>
            <div class="stat-label">States Covered</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
            <div class="stat-num">10M+</div>
            <div class="stat-label">Candidate Records</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
            <div class="stat-num">15+</div>
            <div class="stat-label">Years of Data</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
            <div class="stat-num">5</div>
            <div class="stat-label">Report Categories</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── FEATURES ──
st.markdown("""
<div class="section" style="background:#f5f7fa;">
    <div style="text-align:center; margin-bottom: 0.5rem;">
        <div class="section-label">What You Can Explore</div>
        <div class="section-title" style="margin:0 auto;">Powerful analytics across every dimension</div>
        <p style="font-family:'DM Sans',sans-serif;color:#6b7280;max-width:560px;margin:0.8rem auto 0;font-size:1rem;line-height:1.7;">
            Edustat transforms raw WAEC examination records into actionable intelligence 
            for every stakeholder in Nigerian education.
        </p>
    </div>
    <div class="feature-grid">
        <div class="feat-card">
            <span class="feat-icon">👥</span>
            <div class="feat-title">Student Population</div>
            <div class="feat-desc">Analyse candidate demographics including gender, disability status, and registration trends by state and LGA.</div>
        </div>
        <div class="feat-card">
            <span class="feat-icon">📈</span>
            <div class="feat-title">Performance Analysis</div>
            <div class="feat-desc">Track subject-level pass rates, grade distributions, and year-on-year performance shifts across institutions.</div>
        </div>
        <div class="feat-card">
            <span class="feat-icon">🗺️</span>
            <div class="feat-title">State & LGA Insights</div>
            <div class="feat-desc">Drill down from national averages to local government area performance for targeted intervention planning.</div>
        </div>
        <div class="feat-card">
            <span class="feat-icon">✅</span>
            <div class="feat-title">Success Rate Tracking</div>
            <div class="feat-desc">Monitor credit pass rates, distinction counts, and failure patterns to benchmark school and state progress.</div>
        </div>
        <div class="feat-card">
            <span class="feat-icon">⚠️</span>
            <div class="feat-title">Malpractice Reports</div>
            <div class="feat-desc">Access verified malpractice incident data by centre, state, and year to ensure examination integrity.</div>
        </div>
        <div class="feat-card">
            <span class="feat-icon">📋</span>
            <div class="feat-title">Custom Report Builder</div>
            <div class="feat-desc">Generate, save, and download tailored reports filtered by year, state, gender, subject, and more — as PDF or CSV.</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── AUDIENCE ──
st.markdown("""
<div class="audience">
    <div class="audience-title">Who uses Edustat?</div>
    <p class="audience-sub">Trusted by decision-makers across Nigeria's educational ecosystem</p>
    <div class="audience-cards">
        <div class="aud-card">
            <span class="aud-icon">🏛️</span>
            <div class="aud-name">Government Agencies</div>
            <div class="aud-desc">Ministry of Education & policy planners making evidence-based decisions</div>
        </div>
        <div class="aud-card">
            <span class="aud-icon">🔬</span>
            <div class="aud-name">Researchers</div>
            <div class="aud-desc">Academics studying education outcomes, equity, and regional disparities</div>
        </div>
        <div class="aud-card">
            <span class="aud-icon">🏫</span>
            <div class="aud-name">School Leaders</div>
            <div class="aud-desc">Principals & administrators benchmarking their institution's performance</div>
        </div>
        <div class="aud-card">
            <span class="aud-icon">💰</span>
            <div class="aud-name">Funding Bodies</div>
            <div class="aud-desc">NGOs and donors identifying where educational investment is needed most</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── BOTTOM CTA ──
st.markdown("""
<div class="cta-section">
    <h2>Ready to explore Nigeria's exam data?</h2>
    <p>Create a free account and start generating insights in minutes.</p>
    <div class="waec-notice">
        🔒 All data is sourced directly from <strong>WAEC Nigeria</strong> official examination records 
        and is updated annually. Access requires a verified Edustat account.
    </div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.get("logged_in", False):
    _, cc1, cc2, _ = st.columns([3, 2, 2, 3])
    with cc1:
        if st.button("✏️ Create Free Account", use_container_width=True, key="cta_signup"):
            st.switch_page("pages/sign_up.py")
    with cc2:
        if st.button("🔑 Sign In", use_container_width=True, key="cta_login"):
            st.switch_page("pages/Login.py")
else:
    _, cc1, _ = st.columns([4, 3, 4])
    with cc1:
        if st.button("📊 Open My Dashboard", use_container_width=True, key="cta_dash"):
            st.switch_page("pages/dashboard.py")

st.markdown("""
<div style="text-align:center;padding:2rem;font-family:'DM Sans',sans-serif;font-size:0.82rem;color:#9ca3af;border-top:1px solid #e5e7eb;background:#fff;">
    © 2024 Edustat by WAEC Nigeria &nbsp;·&nbsp; Educational Intelligence Platform &nbsp;·&nbsp; 
    <a href="#" style="color:#2563eb;text-decoration:none;">Privacy Policy</a> &nbsp;·&nbsp; 
    <a href="#" style="color:#2563eb;text-decoration:none;">Terms of Use</a>
</div>
""", unsafe_allow_html=True)
# pages/sign_up.py
import streamlit as st
import re
import bcrypt
import base64
import pandas as pd
from db_connection import create_connection
from sqlalchemy import text
from session_manager import create_session
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import check_authentication, login_user

st.set_page_config(page_title="Sign Up - Edustat", layout="wide")

if check_authentication():
    st.info("You're already logged in!")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/dashboard.py")
    st.stop()

# -------------------- CSS --------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap');

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container { padding: 0 !important; max-width: 100% !important; }
.main { padding: 0 !important; background: #f5f7fa; min-height: 100vh; }

.top-nav {
    background: white;
    padding: 0.6rem 4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
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
    padding-left: 40px;
    line-height: 1.2;
}
.nav-brand span { color: #2563eb; }

.form-wrapper {
    background: white;
    border-radius: 16px;
    padding: 2.5rem 2rem;
    box-shadow: 0 8px 40px rgba(0,0,0,0.10);
    max-width: 480px;
    margin: 2.5rem auto 3rem auto;
}
.form-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.9rem;
    font-weight: 700;
    color: #1a1a1a;
    text-align: center;
    margin-bottom: 0.3rem;
}
.form-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.92rem;
    color: #6c757d;
    text-align: center;
    margin-bottom: 1.5rem;
}

/* password strength bar */
.strength-bar-wrap {
    height: 6px;
    background: #e5e7eb;
    border-radius: 4px;
    margin: 6px 0 2px;
    overflow: hidden;
}
.strength-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s, background 0.3s;
}
.strength-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 6px;
}

/* inline validation hints */
.hint-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 6px 0 10px;
}
.hint {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.74rem;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 500;
}
.hint.ok  { background: #dcfce7; color: #166534; }
.hint.bad { background: #fee2e2; color: #991b1b; }

.stTextInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.95rem !important;
    background: #f8f9fa !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
    background: white !important;
}
.stTextInput > label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    font-weight: 600;
    color: #374151;
}
.stCheckbox > label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.88rem;
    color: #4b5563;
}
.stButton > button {
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.75rem 2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    width: 100% !important;
    margin-top: 0.5rem !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #1d4ed8 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 16px rgba(37,99,235,0.3) !important;
}
.footer-text {
    text-align: center;
    margin-top: 1.2rem;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.9rem;
    color: #6c757d;
}
.footer-text a { color: #2563eb; font-weight: 600; text-decoration: none; }
.footer-text a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)


# -------------------- HELPERS --------------------
def get_base64_image(img_path: str) -> str:
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def is_valid_email(email: str) -> bool:
    """Strict email check — must contain @, a domain, and a TLD."""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def check_password_strength(pwd: str) -> dict:
    """Returns per-rule pass/fail and an overall strength score 0-5."""
    rules = {
        "min8":    len(pwd) >= 8,
        "upper":   bool(re.search(r'[A-Z]', pwd)),
        "lower":   bool(re.search(r'[a-z]', pwd)),
        "digit":   bool(re.search(r'[0-9]', pwd)),
        "special": bool(re.search(r'[^a-zA-Z0-9\s]', pwd)),
        "nospace": " " not in pwd,
    }
    rules["score"] = sum(1 for k, v in rules.items() if k != "score" and v)
    return rules

def hash_password(pwd: str) -> str:
    return bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# -------------------- NAV --------------------
logo_base64 = get_base64_image("assets/Edustat.png")

nav_col1, _, nav_col3 = st.columns([2, 4, 1.5])
with nav_col1:
    st.markdown(f"""
    <div style="display:flex;align-items:center;padding-top:5px;padding-left:40px;">
        <img src="data:image/png;base64,{logo_base64}"
             alt="Edustat Logo" style="height:40px;margin-right:10px;">
            """, unsafe_allow_html=True)

with nav_col3:
    if st.button("Sign In →", key="nav_login"):
        st.switch_page("pages/Login.py")

st.markdown(
    '<hr style="margin:0;border:none;border-bottom:1px solid #e8ecf0;">',
    unsafe_allow_html=True,
)


# -------------------- FORM --------------------
_, col2, _ = st.columns([1, 2, 1])

with col2:
    st.markdown('<div class="form-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="form-title">Create account</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="form-subtitle">Already have an account? '
        '<a href="/Login">Sign in here</a></div>',
        unsafe_allow_html=True,
    )

    # ── Fields ──────────────────────────────────────────────────────────────
    name          = st.text_input("Full Name",        placeholder="e.g. Amaka Obi",          key="su_name")
    username      = st.text_input("Username",         placeholder="e.g. amaka_obi",           key="su_user")
    phone_number  = st.text_input("Phone Number",     placeholder="e.g. 08012345678",         key="su_phone")
    email_address = st.text_input("Email Address",    placeholder="e.g. amaka@gmail.com",     key="su_email")
    password      = st.text_input("Password",         placeholder="Create a strong password", key="su_pass",  type="password")
    confirm_password = st.text_input("Confirm Password", placeholder="Re-enter password",     key="su_conf",  type="password")

    # ── Live password strength indicator ────────────────────────────────────
    if password:
        rules = check_password_strength(password)
        score = rules["score"]

        bar_color = (
            "#dc2626" if score <= 2 else
            "#f59e0b" if score <= 4 else
            "#16a34a"
        )
        bar_width = f"{int(score / 6 * 100)}%"
        strength_label = (
            "Weak"   if score <= 2 else
            "Fair"   if score <= 4 else
            "Strong"
        )
        label_color = bar_color

        st.markdown(f"""
        <div class="strength-bar-wrap">
            <div class="strength-bar"
                 style="width:{bar_width};background:{bar_color};"></div>
        </div>
        <div class="strength-label" style="color:{label_color};">
            Password strength: {strength_label}
        </div>
        <div class="hint-row">
            <span class="hint {'ok' if rules['min8']    else 'bad'}">{'✓' if rules['min8']    else '✗'} 8+ chars</span>
            <span class="hint {'ok' if rules['upper']   else 'bad'}">{'✓' if rules['upper']   else '✗'} Uppercase</span>
            <span class="hint {'ok' if rules['lower']   else 'bad'}">{'✓' if rules['lower']   else '✗'} Lowercase</span>
            <span class="hint {'ok' if rules['digit']   else 'bad'}">{'✓' if rules['digit']   else '✗'} Number</span>
            <span class="hint {'ok' if rules['special'] else 'bad'}">{'✓' if rules['special'] else '✗'} Special char</span>
            <span class="hint {'ok' if rules['nospace'] else 'bad'}">{'✓' if rules['nospace'] else '✗'} No spaces</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Terms checkbox with link ─────────────────────────────────────────────
    terms_agreed = st.checkbox(
        "I agree to the Terms & Conditions",
        key="su_terms",
    )
    st.markdown(
        '<div style="font-family:\'DM Sans\',sans-serif;font-size:0.8rem;'
        'color:#6b7280;margin-top:-10px;margin-bottom:8px;">'
        'Read our <a href="/terms_and_conditions" target="_self" '
        'style="color:#2563eb;font-weight:600;">Terms & Conditions</a> '
        'before signing up.</div>',
        unsafe_allow_html=True,
    )

    # ── Sign up button & validation ──────────────────────────────────────────
    if st.button("CREATE ACCOUNT", key="su_submit"):
        name_val     = name.strip()
        user_val     = username.strip()
        phone_val    = phone_number.strip()
        email_val    = email_address.strip()
        pass_val     = password.strip()
        confirm_val  = confirm_password.strip()

        errors = []

        # 1. Empty fields
        if not all([name_val, user_val, phone_val, email_val, pass_val, confirm_val]):
            errors.append("Please fill in all fields.")

        # 2. Email format
        if email_val and not is_valid_email(email_val):
            errors.append(
                "Invalid email address — make sure it contains **@** and a valid domain "
                "(e.g. yourname@gmail.com)."
            )

        # 3. Password complexity
        if pass_val:
            rules = check_password_strength(pass_val)
            if rules["score"] < 6:
                failing = []
                if not rules["min8"]:    failing.append("at least 8 characters")
                if not rules["upper"]:   failing.append("an uppercase letter")
                if not rules["lower"]:   failing.append("a lowercase letter")
                if not rules["digit"]:   failing.append("a number")
                if not rules["special"]: failing.append("a special character")
                if not rules["nospace"]: failing.append("no spaces")
                errors.append(
                    "Password must contain: " + ", ".join(failing) + "."
                )

        # 4. Confirm password match
        if pass_val and confirm_val and pass_val != confirm_val:
            errors.append("Passwords do not match.")

        # 5. Terms
        if not terms_agreed:
            errors.append(
                "You must agree to the Terms & Conditions before signing up."
            )

        # ── Show all errors at once ──────────────────────────────────────────
        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                engine = create_connection()

                # Check duplicate email
                existing = pd.read_sql(
                    text("SELECT user_id FROM users WHERE email_address = :email"),
                    engine,
                    params={"email": email_val},
                )
                if not existing.empty:
                    st.error(
                        "This email is already registered. "
                        "Please [sign in](/Login) instead."
                    )
                else:
                    hashed = hash_password(pass_val)
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO users
                                    (username, name, phone_number, email_address, password)
                                VALUES
                                    (:username, :name, :phone, :email, :password)
                            """),
                            {
                                "username": user_val,
                                "name":     name_val,
                                "phone":    phone_val,
                                "email":    email_val,
                                "password": hashed,
                            },
                        )
                    st.success(
                        "✅ Account created successfully! "
                        "Redirecting to sign in…"
                    )
                    st.switch_page("pages/Login.py")

            except Exception as e:
                st.error(f"Something went wrong: {e}")

    st.markdown(
        '<div class="footer-text">Already have an account? '
        '<a href="/Login">Sign in</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
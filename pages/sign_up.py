# pages/sign_up.py
import streamlit as st
import re
import bcrypt
import pandas as pd
from db_connection import create_connection
from sqlalchemy import text
from session_manager import create_session
import sys
from pathlib import Path

# Add parent directory to path to import auth_utils
sys.path.append(str(Path(__file__).parent.parent))
from auth_utils import check_authentication, login_user

st.set_page_config(page_title="Sign Up - Edustat", layout="wide")

# Check if already logged in
if check_authentication():
    st.info("You're already logged in!")
    if st.button("Go to Dashboard"):
        st.switch_page("pages/dashboard.py")
    st.stop()

# -------------------- CUSTOM CSS --------------------
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }        

    /* Main container */
    .main {
        padding: 0 !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    /* Logo and header section */
    .top-nav {
        background: white;
        padding: 1rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .logo-section {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .logo-text {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
    }
    
    .nav-links {
        display: flex;
        gap: 2rem;
        align-items: center;
    }
    
    /* Form container */
    .form-container {
        background: white;
        border-radius: 16px;
        padding: 0;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        max-width: 480px;
        margin: 2rem auto 0 auto;
    }
    
    .form-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .form-subtitle {
        font-size: 0.95rem;
        color: #6c757d;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .form-subtitle a {
        color: #1e293b;
        text-decoration: underline;
        font-weight: 500;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        background: #f8f9fa;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1e293b;
        box-shadow: 0 0 0 3px rgba(30, 41, 59, 0.1);
        background: white;
    }
    
    .stTextInput > label {
        font-size: 0.9rem;
        font-weight: 500;
        color: #374151;
        margin-bottom: 0.5rem;
    }
    
    /* Checkbox styling */
    .stCheckbox {
        margin: 1.5rem 0;
    }
    
    .stCheckbox > label {
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    .stCheckbox a {
        color: #1e293b;
        text-decoration: underline;
        font-weight: 500;
    }
    
    /* Button styling */
    .stButton > button {
        background: #1e293b;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        margin-top: 1rem;
        transition: all 0.3s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        background: #0f172a;
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(30, 41, 59, 0.3);
    }
    
    /* Footer text */
    .footer-text {
        text-align: center;
        margin-top: 1.5rem;
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    .footer-text a {
        color: #1e293b;
        font-weight: 600;
        text-decoration: none;
    }
    
    .footer-text a:hover {
        text-decoration: underline;
    }
    
    /* Error/Success messages */
    .stAlert {
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- HEADER / NAVIGATION --------------------
st.markdown("""
<div class="top-nav">
    <div class="logo-section">
        <span style="font-size: 2rem;">☀️</span>
        <span class="logo-text">EDUSTAT</span>
    </div>
    <div class="nav-links">
        <span style="color: #6c757d; cursor: pointer;">Pricing</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------- FORM CONTAINER --------------------
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="form-title">Create account</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subtitle">Please login if you already have an account</div>', unsafe_allow_html=True)
    
    # --- Input Fields ---
    name = st.text_input("Full Name", placeholder="Enter your full name", key="name_input")
    username = st.text_input("Username", placeholder="Enter your username", key="username_input")
    phone_number = st.text_input("Phone Number", placeholder="Enter your phone number", key="phone_input")
    email_address = st.text_input("Email Address", placeholder="Enter your email address", key="email_input")
    password = st.text_input("Password", type="password", placeholder="Enter your password", key="password_input")
    confirm_password = st.text_input("Confirm password", type="password", placeholder="Confirm your password", key="confirm_input")
    
    # Terms and conditions checkbox
    terms_agreed = st.checkbox("By signing up you agree to the Terms & Conditions", key="terms_checkbox")
    
    # --- Validation Functions ---
    def is_valid_email(email):
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(email_regex, email) is not None

    def hash_password(pwd):
        return bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # --- Sign-Up Logic ---
    if st.button("SIGN UP", key="signup_button"):
        # Trim whitespace from inputs
        username_val = username.strip()
        name_val = name.strip()
        phone_val = phone_number.strip()
        email_val = email_address.strip()
        password_val = password.strip()
        confirm_val = confirm_password.strip()

        # Validation checks
        if not all([username_val, name_val, phone_val, email_val, password_val, confirm_val]):
            st.error("Please fill in all fields.")
        elif not terms_agreed:
            st.error("Please agree to the Terms & Conditions.")
        elif not is_valid_email(email_val):
            st.error("Please enter a valid email address.")
        elif password_val != confirm_val:
            st.error("Passwords do not match.")
        else:
            try:
                engine = create_connection()  # SQLAlchemy engine

                # Check if email already exists
                check_query = text("SELECT * FROM users WHERE email_address = :email")
                existing_user_df = pd.read_sql(check_query, engine, params={"email": email_val})

                if not existing_user_df.empty:
                    st.error("Email already registered. Please login instead.")
                else:
                    # Hash the password
                    hashed_pass = hash_password(password_val)

                    # Insert user into database
                    insert_query = text("""
                        INSERT INTO users (username, name, phone_number, email_address, password)
                        VALUES (:username, :name, :phone, :email, :password)
                    """)
                    with engine.begin() as conn:
                        result =conn.execute(
                            insert_query,
                            {
                                "username": username_val,
                                "name": name_val,
                                "phone": phone_val,
                                "email": email_val,
                                "password": hashed_pass
                            }
                        )

                    st.success("✅ Account created successfully! Redirecting to login...")
                    st.switch_page("pages/Login.py")

            except Exception as e:
                st.error(f"Database error: {e}")
    
    # Footer link
    st.markdown('<div class="footer-text">Already have an account? <a href="/Login">Login</a></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
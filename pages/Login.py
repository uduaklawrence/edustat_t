import streamlit as st
import re
import bcrypt
import pandas as pd
from db_connection import create_connection
from streamlit_local_storage import LocalStorage
from session_manager import create_session, validate_session

st.set_page_config(page_title="Login - Edustat", layout="wide")

# Initialize localStorage
storage = LocalStorage()

# --- Check for Existing Session Token ---
token = storage.getItem("session_token")

# Uncomment when session validation is ready
# if token and token not in ["", "null", "undefined"]:
#     user_id = validate_session(token)
#     if user_id:
#         st.session_state.logged_in = True
#         st.session_state.user_id = user_id
#         st.session_state.session_token = token
#         st.switch_page("pages/dashboard.py")
#         st.stop()
#     else:
#         storage.removeItem("session_token")

# -------------------- CUSTOM CSS --------------------
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Remove default padding */
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    /* Main container */
    .main {
        padding: 0 !important;
        background: #f8f9fa;
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
        margin-bottom: 0;
    }
    
    .logo-section {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .logo-img {
    height: 42px;
    width: auto;
    object-fit: contain;
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
    
    .nav-button {
        background: #1e293b;
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 6px;
        font-weight: 500;
        cursor: pointer;
        border: none;
    }
    
    /* Form container */
    .form-container {
        background: white;
        border-radius: 16px;
        padding: 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        max-width: 480px;
        width: 100%;
        margin-top: 2rem;
    }
    
    .form-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .welcome-text {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 0.5rem;
    }
    
    .form-subtitle {
        font-size: 0.95rem;
        color: #6c757d;
        margin-bottom: 2rem;
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
    
    /* Remember me and forgot password row */
    .login-options {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 1rem 0 1.5rem 0;
    }
    
    .stCheckbox {
        margin: 0;
    }
    
    .stCheckbox > label {
        font-size: 0.9rem;
        color: #6c757d;
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
        transition: all 0.3s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        background: #0f172a;
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(30, 41, 59, 0.3);
    }
    
    /* Secondary button for forgot password */
    .stButton > button[kind="secondary"] {
        background: transparent;
        color: #1e293b;
        border: 1px solid #1e293b;
        text-transform: none;
        letter-spacing: normal;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: #f8f9fa;
        transform: none;
    }
    
    /* Footer text */
    .footer-text {
        text-align: center;
        margin-top: 1.5rem;
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    .footer-link {
        color: #1e293b;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
    }
    
    .footer-link:hover {
        text-decoration: underline;
    }
    
    /* Forgot password link */
    .forgot-link {
        font-size: 0.9rem;
        color: #1e293b;
        text-decoration: none;
        font-weight: 500;
        cursor: pointer;
    }
    
    .forgot-link:hover {
        text-decoration: underline;
    }
    
    /* Error/Success messages */
    .stAlert {
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 1px solid #e2e8f0;
    }
    
    /* Forgot password section */
    .forgot-section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for forgot password
if 'forgot_clicked' not in st.session_state:
    st.session_state.forgot_clicked = False
if 'show_signup_link' not in st.session_state:
    st.session_state.show_signup_link = False

# -------------------- HEADER / NAVIGATION --------------------
st.markdown("""
<div class="top-nav">
    <div class="logo-section">
        <img src="assets/image2.jpg" class="logo-img" />
    </div>
    <div class="nav-links">
        <span style="color: #6c757d; cursor: pointer;">Pricing</span>
        <button class="nav-button" onclick="window.location.href='/sign_up'">Sign up</button>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------- CENTER CONTAINER --------------------
st.markdown('<div style="display: flex; justify-content: center; padding: 0 1rem;">', unsafe_allow_html=True)

# Create centered column
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    if not st.session_state.forgot_clicked:
        # ==================== LOGIN FORM ====================
        st.markdown('<div class="form-title">Sign in to your account</div>', unsafe_allow_html=True)
        st.markdown('<div class="welcome-text">Welcome</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-subtitle">Please sign-in if you already have an account</div>', unsafe_allow_html=True)
        
        # Email and Password inputs
        email = st.text_input("Email", placeholder="Email", key="email_input", label_visibility="visible")
        password = st.text_input("Password", type="password", placeholder="Password", key="password_input", label_visibility="visible")
        
        # Remember me and Forgot password row
        col_remember, col_forgot = st.columns([1, 1])
        with col_remember:
            remember_me = st.checkbox("Remember Me", key="remember_checkbox")
        with col_forgot:
            if st.button("Forgot Password?", key="forgot_btn", type="secondary", use_container_width=False):
                st.session_state.forgot_clicked = True
                st.rerun()
        
        # Email validation function
        def is_valid_email(email):
            email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            return re.match(email_regex, email) is not None
        
        # Login button
        if st.button("SIGN IN", key="login_button"):
            email_val = email.strip()
            password_val = password.strip()

            if not email_val or not password_val:
                st.error("Please enter both email and password.")
            elif not is_valid_email(email_val):
                st.error("Please enter a valid email address.")
            else:
                try:
                    engine = create_connection()
                    user_df = pd.read_sql(
                        "SELECT * FROM users WHERE email_address = %s",
                        engine,
                        params=(email_val,)
                    )

                    if not user_df.empty:
                        hashed_pass = user_df['password'].values[0].encode('utf-8')

                        if bcrypt.checkpw(password_val.encode('utf-8'), hashed_pass):
                            # Get user_id from DB
                            user_id = int(user_df['user_id'].values[0])

                            # Create session in DB
                            session_token = create_session(user_id)

                            # Save session info
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id
                            st.session_state.user_email = email_val
                            st.session_state.session_token = session_token

                            # Save token to browser localStorage
                            storage.setItem("session_token", session_token)

                            st.success("✅ Login successful! Redirecting to dashboard...")
                            st.switch_page("pages/dashboard.py")
                        else:
                            st.error("Invalid email or password.")
                    else:
                        st.error("Invalid email or password.")

                except Exception as e:
                    st.error(f"Login error: {e}")
        
        # Footer link
        st.markdown('<div class="footer-text">New on our platform? <a href="/sign_up" class="footer-link">Create an account</a></div>', unsafe_allow_html=True)
    
    else:
        # ==================== FORGOT PASSWORD FORM ====================
        st.markdown('<div class="forgot-section-title">🔑 Reset Your Password</div>', unsafe_allow_html=True)
        st.markdown('<div class="form-subtitle">Enter your email and new password to reset your account</div>', unsafe_allow_html=True)
        
        forgot_email = st.text_input("Registered Email", placeholder="Enter your registered email", key="forgot_email")
        new_password = st.text_input("New Password", type="password", placeholder="Enter new password", key="new_password")
        confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Confirm new password", key="confirm_password")
        
        col_reset, col_back = st.columns(2)
        
        with col_reset:
            if st.button("RESET PASSWORD", key="reset_button", use_container_width=True):
                if not forgot_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    try:
                        engine = create_connection()
                        user_exists_df = pd.read_sql(
                            "SELECT * FROM users WHERE email_address = %s",
                            engine,
                            params=(forgot_email,)
                        )

                        if user_exists_df.empty:
                            st.error("Email not found in our records.")
                        else:
                            hashed_pass = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            update_query = "UPDATE users SET password=%s WHERE email_address=%s"

                            with engine.begin() as conn:
                                conn.execute(update_query, (hashed_pass, forgot_email))

                            st.success("✅ Password updated successfully! You can now login with the new password.")
                            st.session_state.forgot_clicked = False
                            st.rerun()
                    
                    except Exception as e:
                        st.error(f"Reset error: {e}")
        
        with col_back:
            if st.button("Back to Login", key="back_button", type="secondary", use_container_width=True):
                st.session_state.forgot_clicked = False
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
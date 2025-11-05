import streamlit as st
import re
import bcrypt
import pandas as pd
from db_connection import create_connection

st.set_page_config(page_title="Login")
st.title("🔑 Login")

# --- Login Inputs ---
email = st.text_input("Email Address")
password = st.text_input("Password", type="password")

def is_valid_email(email):
    """Simple regex validation for email."""
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

# --- Login Logic ---
if st.button("Login"):
    if not is_valid_email(email):
        st.error("Please enter a valid email address.")
    else:
        engine = create_connection()
        query = "SELECT * FROM users WHERE email_address = %s"
        user_df = pd.read_sql(query, engine, params=(email,))

        if not user_df.empty:
            hashed_pass = user_df['password'].values[0].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), hashed_pass):
                # ✅ Save important session variables
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.user_id = int(user_df['user_id'].values[0])  # <-- NEW LINE

                st.success("Sign-in successful! Redirecting to Dashboard...")
                st.switch_page("pages/dashboard.py")
            else:
                st.error("Invalid email or password.")
        else:
            st.error("Invalid email or password.")

# --- Forgot Password Section ---
st.write("---")
st.subheader("Forgot Password?")

# Control whether reset form is visible
if 'forgot_clicked' not in st.session_state:
    st.session_state.forgot_clicked = False

if st.button("Forgot Password"):
    st.session_state.forgot_clicked = True

if st.session_state.forgot_clicked:
    forgot_email = st.text_input("Enter your registered email for reset", key="forgot_email")
    new_password = st.text_input("New Password", type="password", key="new_password")
    confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password")

    if st.button("Reset Password"):
        if not forgot_email or not new_password or not confirm_password:
            st.error("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
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

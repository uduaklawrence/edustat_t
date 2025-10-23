# pages/sign_up.py
import streamlit as st
import re
import bcrypt
import pandas as pd
from db_connection import create_connection
from sqlalchemy import text

st.set_page_config(page_title="Sign Up")
st.title("📝 Create a New Account")

# --- Input Fields ---
username = st.text_input("Username")
name = st.text_input("Full Name")
phone_number = st.text_input("Phone Number")
email_address = st.text_input("Email Address")
password = st.text_input("Password", type="password")
confirm_password = st.text_input("Confirm Password", type="password")

# --- Validation Functions ---
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- Sign-Up Logic ---
if st.button("Create Account"):
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
                    conn.execute(
                        insert_query,
                        {
                            "username": username_val,
                            "name": name_val,
                            "phone": phone_val,
                            "email": email_val,
                            "password": hashed_pass
                        }
                    )

                st.success("✅ Account created successfully! Please Sign-In.")
                st.switch_page("pages/Login.py")

        except Exception as e:
            st.error(f"Database error: {e}")

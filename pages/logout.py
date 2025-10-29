import streamlit as st
import time

st.set_page_config(page_title="Logout")

st.title("👋 Logging out...")

# --- Logout logic ---
if "logged_in" in st.session_state and st.session_state.logged_in:
    # Clear all login-related session keys
    for key in list(st.session_state.keys()):
        if key in ["logged_in", "user_email"]:
            del st.session_state[key]

    st.success("You have been logged out successfully.")
    time.sleep(1)  # Short delay before redirect
    st.switch_page("pages/Login.py")

else:
    st.info("You are not logged in.")
    st.page_link("pages/Login.py", label="Go to Login")

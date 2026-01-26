# auth_utils.py
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import os

def get_cookie_manager():
    """Initialize and return the cookie manager"""
    # Use environment variable for production, or a default for development
    secret_key = os.getenv("COOKIE_SECRET_KEY", "edustat-default-secret-key-change-in-production")
    
    cookies = EncryptedCookieManager(
        prefix="edustat_",
        password=secret_key
    )
    
    if not cookies.ready():
        st.stop()
    
    return cookies

def check_authentication():
    """
    Check if user is authenticated via cookies.
    Returns True if authenticated, False otherwise.
    Also sets st.session_state variables.
    """
    cookies = get_cookie_manager()
    
    # Check cookie first
    if cookies.get("logged_in") == "true":
        # Restore session state from cookies
        st.session_state.logged_in = True
        st.session_state.username = cookies.get("username", "")
        st.session_state.user_email = cookies.get("user_email", "")
        st.session_state.user_id = cookies.get("user_id", "")
        return True
    
    # Check session state (for same-session navigation)
    if st.session_state.get("logged_in", False):
        return True
    
    return False

def login_user(username, user_email="", user_id=""):
    """
    Log in a user by setting session state and cookies
    """
    cookies = get_cookie_manager()
    
    # Set session state
    st.session_state.logged_in = True
    st.session_state.username = username
    st.session_state.user_email = user_email
    st.session_state.user_id = user_id
    
    # Set cookies (persist across refreshes)
    cookies["logged_in"] = "true"
    cookies["username"] = username
    cookies["user_email"] = user_email
    cookies["user_id"] = str(user_id)
    cookies.save()

def logout_user():
    """
    Log out a user by clearing session state and cookies
    """
    cookies = get_cookie_manager()
    
    # Clear session state
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_email = ""
    st.session_state.user_id = ""
    
    # Clear cookies
    cookies["logged_in"] = "false"
    cookies["username"] = ""
    cookies["user_email"] = ""
    cookies["user_id"] = ""
    cookies.save()

def require_authentication():
    """
    Decorator/function to protect pages that require authentication.
    Call this at the top of protected pages.
    """
    if not check_authentication():
        st.warning("⚠️ Please login to access this page")
        st.switch_page("pages/Login.py")
        st.stop()
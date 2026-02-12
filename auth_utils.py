# auth_utils.py
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import os
import time
from datetime import datetime, timedelta

def get_cookie_manager():
    """Initialize and return the cookie manager (singleton pattern)"""
    # Check if cookie manager already exists in session state
    if "cookie_manager" not in st.session_state:
        # Use environment variable for production, or a default for development
        secret_key = os.getenv("COOKIE_SECRET_KEY", "edustat-default-secret-key-change-in-production")
        
        cookies = EncryptedCookieManager(
            prefix="edustat_",
            password=secret_key
        )
        
        # Wait for cookies to be ready
        if not cookies.ready():
            st.stop()
        
        # Store in session state to avoid recreating
        st.session_state.cookie_manager = cookies
    
    return st.session_state.cookie_manager

def check_authentication():
    """
    Check if user is authenticated via cookies.
    Returns True if authenticated, False otherwise.
    Also sets st.session_state variables.
    """
    cookies = get_cookie_manager()
    
    # Check cookie first
    logged_in_cookie = cookies.get("logged_in")
    
    if logged_in_cookie == "true":
        # Check if session has expired (4 hours)
        login_time_str = cookies.get("login_time", "")
        
        if login_time_str:
            try:
                login_time = datetime.fromisoformat(login_time_str)
                current_time = datetime.now()
                
                # Check if 4 hours have passed
                if current_time - login_time > timedelta(hours=4):
                    # Session expired, logout
                    logout_user()
                    return False
            except Exception:
                # If timestamp is invalid, continue with login
                pass
        
        # Restore session state from cookies
        username = cookies.get("username", "")
        user_email = cookies.get("user_email", "")
        user_id = cookies.get("user_id", "")
        
        # Only restore if we have valid data
        if username or user_email:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_email = user_email
            st.session_state.user_id = user_id
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
    
    # Set session state first
    st.session_state.logged_in = True
    st.session_state.username = username
    st.session_state.user_email = user_email
    st.session_state.user_id = user_id
    
    # Set cookies (persist across refreshes)
    try:
        # Save login timestamp for expiration check
        login_time = datetime.now().isoformat()
        
        cookies["logged_in"] = "true"
        cookies["username"] = str(username)
        cookies["user_email"] = str(user_email)
        cookies["user_id"] = str(user_id)
        cookies["login_time"] = login_time
        cookies.save()
        
        # Give cookies time to save before redirect
        time.sleep(0.5)
    except Exception as e:
        st.error(f"Cookie save error: {e}")

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
    try:
        cookies["logged_in"] = "false"
        cookies["username"] = ""
        cookies["user_email"] = ""
        cookies["user_id"] = ""
        cookies["login_time"] = ""
        cookies.save()
        
        # Give cookies time to clear
        time.sleep(0.3)
    except Exception as e:
        st.error(f"Cookie clear error: {e}")

def require_authentication():
    """
    Decorator/function to protect pages that require authentication.
    Call this at the top of protected pages.
    """
    if not check_authentication():
        st.warning("⚠️ Please login to access this page")
        st.switch_page("pages/Login.py")
        st.stop()
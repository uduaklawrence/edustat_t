import streamlit as st

# ------------ SESSION DEFAULTS ------------
st.set_page_config(page_title="Edustat WAEC Dashboard", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "navigate_to" not in st.session_state:
    st.session_state.navigate_to = "Landing"
if "user_id" not in st.session_state:
    st.session_state.user_id = None


# ------------ IMPORT ALL PAGES SAFELY ------------
# Every page file MUST contain a `render()` function

import pages.landing as landing_page
import pages.Login as login_page
import pages.sign_up as signup_page
import pages.dashboard as dashboard_page
import pages.create_report as create_report_page
import pages.my_reports as my_reports_page


# ------------ ROUTER FUNCTION ------------
def route():
    page = st.session_state.get("navigate_to", "Landing").lower()

    if page == "landing":
        landing_page.render()

    elif page == "login":
        login_page.render()

    elif page == "sign_up":
        signup_page.render()

    elif page == "dashboard":
        if not st.session_state.get("logged_in", False):
            st.warning("Please sign in first.")
            return
        dashboard_page.render()

    elif page == "create report":
        if not st.session_state.get("logged_in", False):
            st.warning("Please sign in first.")
            return
        create_report_page.render()

    elif page == "my reports":
        if not st.session_state.get("logged_in", False):
            st.warning("Please sign in first.")
            return
        my_reports_page.render()

    else:
        st.error("Unknown page requested.")


# ------------ SIDEBAR NAVIGATION ------------
with st.sidebar:
    st.markdown("## 📘 Navigation")

    if st.button("🏠 Home"):
        st.session_state.navigate_to = "Landing"
        st.rerun()

    if not st.session_state.get("logged_in", False):
        if st.button("🔐 Login"):
            st.session_state.navigate_to = "login"
            st.rerun()

        if st.button("📝 Sign Up"):
            st.session_state.navigate_to = "sign_up"
            st.rerun()
    else:
        if st.button("📊 Dashboard"):
            st.session_state.navigate_to = "dashboard"
            st.rerun()

        if st.button("📄 Create Report"):
            st.session_state.navigate_to = "create report"
            st.rerun()

        if st.button("📁 My Reports"):
            st.session_state.navigate_to = "my reports"
            st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.navigate_to = "Landing"
            st.rerun()


# ------------ RUN THE ROUTER ------------
route()
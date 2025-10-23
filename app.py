import streamlit as st

# ------------------- SESSION STATE -------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'navigate_to' not in st.session_state:
    st.session_state.navigate_to = "Landing"

st.set_page_config(page_title="Edustat WAEC Dashboard", layout="wide")

# ------------------- PAGE ROUTING -------------------
page = st.session_state['navigate_to']

if page == "Landing":
    import pages.landing
elif page.lower() == "sign_up":  # ensure lowercase matches
    import pages.sign_up
elif page.lower() == "login":
    import pages.Login
elif page.lower() == "dashboard":
    if not st.session_state.get('logged_in', False):
        st.warning("Please sign in first.")
        st.stop()
    import pages.dashboard
elif page.lower() == "create report":  # Added Create Report page
    if not st.session_state.get('logged_in', False):
        st.warning("Please sign in first.")
        st.stop()
    import pages.create_report

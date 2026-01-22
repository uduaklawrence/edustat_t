import streamlit as st

# ------------ SESSION DEFAULTS ------------
st.set_page_config(page_title="Edustat WAEC Dashboard", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ------------ MAIN PAGE CONTENT ------------
st.title("🎓 Welcome to Edustat")
st.write("Analyze WAEC candidate data with insightful visualizations.")

st.subheader("Get Started")

if not st.session_state.get("logged_in", False):
 
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 Sign Up", use_container_width=True):
            st.switch_page("pages/sign_up.py")
    with col2:
        if st.button("📝 Login", use_container_width=True):
            st.switch_page("pages/Login.py")
else:
    st.success(f"✅ Logged in as: {st.session_state.get('user_email', 'User')}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Go to Dashboard", use_container_width=True):
            st.switch_page("pages/dashboard.py")
    with col2:
        if st.button("📄 Create New Report", use_container_width=True):
            st.switch_page("pages/create_report.py")
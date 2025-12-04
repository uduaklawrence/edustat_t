import streamlit as st
 
st.set_page_config(page_title="Edustat WAEC Dashboard Landing", layout="wide")
st.title("🎓 Welcome to Edustat WAEC Dashboard")
st.write("Analyze WAEC candidate data with insightful visualizations.")
 
st.subheader("Get Started")
 
col1, col2 = st.columns(2)
 
with col1:
    if st.button("🔑 Sign Up"):
        st.switch_page("pages/sign_up.py")  # directly switches to Sign-Up page
 
with col2:
    if st.button("📝 Login"):
        st.switch_page("pages/Login.py")  # directly switches to Login page
 
st.info("Use Sign-Up to create a new account or Login if you already have credentials.")
 
import streamlit as st
import user_performance
import sales_performance
import os

# Authentication function
def login(username, password):
    PASSWORD = os.getenv("PASSWORD")
    USERNAME = "HospVenue"
    return username == USERNAME and password == PASSWORD

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'login_clicked' not in st.session_state:
    st.session_state['login_clicked'] = False

# Login button logic
if not st.session_state['authenticated']:
    st.title("🏟️ AFC Venue - MBM Hospitality")
    
    # Description of the app
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    This app provides insights into MBM Sales Performance and User Metrics. 

    **MBM Sales Performance**:  
    Analyse sales from MBM hospitality. 

    **Premium Exec Metrics**:  
    View and evaluate performance metrics from the Premium Team.

    **Note:** You will need to hit the submit button again after successfully entering your login details.
    """)

    if not st.session_state['login_clicked']:
        if st.button("🔐 Login"):
            st.session_state['login_clicked'] = True

    if st.session_state['login_clicked']:
        username = st.text_input("👤 Username")
        password = st.text_input("🔑 Password", type="password")
        if st.button("Submit"):
            if login(username, password):
                st.session_state['authenticated'] = True
                st.success("🎉 Login successful!")
            else:
                st.error("❌ Username or password is incorrect")

else:
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

    if app_choice == "📊 Sales Performance":
        sales_performance.run_app()

    elif app_choice == "📈 User Performance":
        user_performance.run_app()
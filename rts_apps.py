import streamlit as st
import user_performance
import sales_performance
import os

# Authentication function
def login(username, password):
    PASSWORD = os.getenv("PASSWORD")
    USERNAME = "HospVenue"
    return username == USERNAME and password == PASSWORD

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(username, password):
            st.session_state['authenticated'] = True
            st.success("Login successful!")
        else:
            st.error("Username or password is incorrect")
else:
    st.sidebar.title("Navigation")
    app_choice = st.sidebar.radio("Go to", ["User Performance", "Sales Performance"])

    if app_choice == "User Performance":
        
        user_performance.run_app()

    elif app_choice == "Sales Performance":
        
        sales_performance.run_app()

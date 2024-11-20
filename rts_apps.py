# import streamlit as st
# import user_performance_api
# import sales_performance
# import os

# # Authentication function
# def login(username, password):
#     PASSWORD = "Hospitality2024!"
#     USERNAME = "HospVenue"
#     return username == USERNAME and password == PASSWORD
    

# # Initialize session state for authentication
# if 'authenticated' not in st.session_state:
#     st.session_state['authenticated'] = False
# if 'login_clicked' not in st.session_state:
#     st.session_state['login_clicked'] = False
    

# # Login button logic
# if not st.session_state['authenticated']:
#     st.title("🏟️ AFC Venue - MBM Hospitality")
    
#     # Description of the app
#     st.markdown("""
#     **Welcome to the Venue Hospitality Dashboard!**  
#     This app provides insights into MBM Sales Performance and User Metrics. 

#     **MBM Sales Performance**:  
#     Analyse sales from MBM hospitality. 

#     **Premium Exec Metrics**:  
#     View and evaluate performance metrics from the Premium Team.

#     **Note:** You will need to hit the submit button again after successfully entering your login details.
#     """)

#     if not st.session_state['login_clicked']:
#         if st.button("🔐 Login"):
#             st.session_state['login_clicked'] = True

#     if st.session_state['login_clicked']:
#         username = st.text_input("👤 Username")
#         password = st.text_input("🔑 Password", type="password")
#         if st.button("Submit"):
#             if login(username, password):
#                 st.session_state['authenticated'] = True
#                 st.success("🎉 Login successful!")
#             else:
#                 st.error("❌ Username or password is incorrect")

# else:
#     st.sidebar.title("🧭 Navigation")
#     app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

#     if app_choice == "📊 Sales Performance":
#         sales_performance.run_app()

#     elif app_choice == "📈 User Performance":
#         user_performance_api.run_app()
        
        


import streamlit as st
import user_performance_api
import sales_performance
from msal_streamlit_authentication import msal_authentication

# Define MSAL configuration
msal_config = {
    "auth": {
        "clientId": "9c350612-9d05-40f3-94e9-d348d92f446a",
        "authority": "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021",
        "redirectUri": "https://afc-apps-hospitality.streamlit.app",
        "postLogoutRedirectUri": "https://afc-apps-hospitality.streamlit.app"
    },
    "cache": {
        "cacheLocation": "sessionStorage",
        "storeAuthStateInCookie": False
    }
}

# Define login request parameters
login_request = {
    "scopes": ["User.Read"]
}

# Initialize authentication
login_token = msal_authentication(
    auth=msal_config['auth'],
    cache=msal_config['cache'],
    login_request=login_request,
    logout_request={},
    login_button_text="🔐 Login",
    logout_button_text="🔓 Logout",
    key="unique_msal_key"
)

# Check auth
if login_token:
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

    if app_choice == "📊 Sales Performance":
        sales_performance.run_app()

    elif app_choice == "📈 User Performance":
        user_performance_api.run_app()
else:
    st.title("🏟️ AFC Venue - MBM Hospitality")

    # Description of the app
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    This app provides insights into MBM Sales Performance and User Metrics. 

    **MBM Sales Performance**:  
    Analyse sales from MBM hospitality. 

    **Premium Exec Metrics**:  
    View and evaluate performance metrics from the Premium Team.

    **Note:** Please log in using AFC credentials to access the app.
    """)

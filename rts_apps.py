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
import logging
import user_performance_api
import sales_performance
from msal import PublicClientApplication

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler()
    ]
)

# Log startup
logging.debug("Starting the Streamlit app.")

# Initialize session state
if "login_status" not in st.session_state:
    st.session_state["login_status"] = None
    logging.debug("Initialized session state for login_status.")

if "logout_triggered" not in st.session_state:
    st.session_state["logout_triggered"] = False
    logging.debug("Initialized session state for logout_triggered.")

# MSAL Configuration
client_id = "9c350612-9d05-40f3-94e9-d348d92f446a"
authority = "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021"
redirect_uri = "https://afc-apps-hospitality.streamlit.app"

# Create MSAL application instance
msal_app = PublicClientApplication(client_id=client_id, authority=authority)

# Silent Authentication
try:
    accounts = msal_app.get_accounts()
    if accounts:
        result = msal_app.acquire_token_silent(scopes=["User.Read"], account=accounts[0])
        logging.debug("Silent authentication attempted.")
    else:
        result = None

    if result and "access_token" in result:
        st.session_state["login_status"] = result["access_token"]
        logging.debug(f"Silent authentication successful: {result['access_token']}")
    else:
        logging.debug("Silent authentication failed. Login required.")
except Exception as e:
    logging.error(f"Error during silent authentication: {e}")
    st.session_state["login_status"] = None

# Debugging the login status and session state
logging.debug(f"Login status after silent authentication: {st.session_state['login_status']}")

# Handle authenticated and unauthenticated states
if st.session_state["login_status"]:
    # User is authenticated
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

    if app_choice == "📊 Sales Performance":
        logging.info("Navigated to Sales Performance.")
        sales_performance.run_app()

    elif app_choice == "📈 User Performance":
        logging.info("Navigated to User Performance.")
        user_performance_api.run_app()

else:
    # Unauthenticated state: show login button
    st.title("🏟️ AFC Venue - MBM Hospitality")
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    This app provides insights into MBM Sales Performance and User Metrics. 

    **MBM Sales Performance**:  
    Analyse sales from MBM hospitality. 

    **Premium Exec Metrics**:  
    View and evaluate performance metrics from the Premium Team.

    **Note:** Please log in using AFC credentials to access the app.
    """)

    # Show login button for interactive authentication
    if st.button("🔐 Login"):
        try:
            # Trigger interactive login
            result = msal_app.acquire_token_interactive(scopes=["User.Read"])  # Removed `redirect_uri`
            if result and "access_token" in result:
                st.session_state["login_status"] = result["access_token"]
                logging.debug(f"Access token received: {result['access_token']}")
            else:
                st.error("Login failed. Please try again.")
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            st.error("Authentication failed. Please try again.")




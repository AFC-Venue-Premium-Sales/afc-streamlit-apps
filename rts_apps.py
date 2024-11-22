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
import os
import msal

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler()
    ]
)

# Azure App Configuration
CLIENT_ID = "9c350612-9d05-40f3-94e9-d348d92f446a"
TENANT_ID = "068cb91a-8be0-49d7-be3a-38190b0ba021"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["User.Read"]
REDIRECT_URI = "https://afc-apps-hospitality.streamlit.app"
CACHE_FILE = "token_cache.bin"

# Functions for token caching
def load_token_cache():
    """Load token cache from file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = msal.SerializableTokenCache()
            cache.deserialize(f.read())
            return cache
    return msal.SerializableTokenCache()

def save_token_cache(cache):
    """Save token cache to file."""
    if cache.has_state_changed:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())

# MSAL Application Initialization
token_cache = load_token_cache()
app = msal.PublicClientApplication(
    client_id=CLIENT_ID,
    authority=AUTHORITY,
    token_cache=token_cache,
)

# Function to acquire a token interactively
def get_token_interactive():
    """Trigger interactive login and acquire token."""
    auth_url = app.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI,
    )
    st.markdown(f'[**Click here to log in**]({auth_url})', unsafe_allow_html=True)
    st.stop()

# Function to acquire token silently or refresh token
def get_token_silent():
    """Try to acquire token silently using cache."""
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes=SCOPE, account=accounts[0])
        if result and "access_token" in result:
            logging.info("Token refreshed silently.")
            return result["access_token"]
    logging.warning("Silent token acquisition failed.")
    return None

# Handle redirect from Azure AD
def handle_redirect():
    """Process the authorization code from the redirect URI."""
    query_params = st.query_params  # Updated method
    logging.debug(f"Query params: {query_params}")
    if "code" in query_params:
        code = query_params["code"][0]
        try:
            result = app.acquire_token_by_authorization_code(
                code=code,
                scopes=SCOPE,
                redirect_uri=REDIRECT_URI,
            )
            if result and "access_token" in result:
                st.session_state["access_token"] = result["access_token"]
                st.session_state["is_authenticated"] = True
                save_token_cache(token_cache)
                st.experimental_set_query_params()  # Clear query params to avoid repeated processing
                return True
        except Exception as e:
            logging.error(f"Error during token acquisition: {e}")
            st.error("Authentication failed. Please try again.")
    return False

# Initialize session state
if "is_authenticated" not in st.session_state:
    st.session_state["is_authenticated"] = False

# Main app logic
if not st.session_state["is_authenticated"]:
    # Handle redirect and retrieve token
    if handle_redirect():
        st.experimental_rerun()

    # Try silent login
    access_token = get_token_silent()
    if access_token:
        st.session_state["access_token"] = access_token
        st.session_state["is_authenticated"] = True
        logging.info("Authenticated via silent login.")
    else:
        # If silent login fails, prompt for interactive login
        logging.info("No valid session found. Prompting for login.")
        get_token_interactive()

# If authenticated, show the main app
if st.session_state["is_authenticated"]:
    st.sidebar.title("🧭 Navigation")
    st.sidebar.success("You are logged in!")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

    if app_choice == "📊 Sales Performance":
        st.write("Sales Performance Dashboard")
        # Placeholder for sales_performance.run_app()

    elif app_choice == "📈 User Performance":
        st.write("User Performance Dashboard")
        # Placeholder for user_performance_api.run_app()
else:
    st.warning("You must log in to access the app.")


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
from authlib.integrations.requests_client import OAuth2Session
import secrets
import hashlib
import base64

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

# Azure AD Configuration
client_id = "9c350612-9d05-40f3-94e9-d348d92f446a"  # Replace with your Azure AD Client ID
authority = "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021"  # Replace with your Tenant ID
redirect_uri = "https://afc-apps-hospitality.streamlit.app"  # Replace with your Redirect URI
scope = "User.Read"  # Adjust scope based on your needs

# Generate PKCE pair
def generate_pkce_pair():
    code_verifier = secrets.token_urlsafe(64)  # Generates a secure random string
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode("utf-8")  # Create a SHA256 hash and encode it
    return code_verifier, code_challenge

# Initialize session state
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

if "code_verifier" not in st.session_state:
    # Generate only once and persist across steps
    st.session_state["code_verifier"], st.session_state["code_challenge"] = generate_pkce_pair()
    logging.debug(f"Generated Code Verifier: {st.session_state['code_verifier']}")
    logging.debug(f"Generated Code Challenge: {st.session_state['code_challenge']}")
    logging.debug(f"Code Challenge Length: {len(st.session_state['code_challenge'])}")

# OAuth2 session
session = OAuth2Session(
    client_id=client_id,
    redirect_uri=redirect_uri,
    scope=scope
)

# Handle login/logout flow
if st.session_state["access_token"]:
    # User is authenticated
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

    if app_choice == "📊 Sales Performance":
        st.write("Welcome to the Sales Performance dashboard!")  # Placeholder
    elif app_choice == "📈 User Performance":
        st.write("Welcome to the User Performance dashboard!")  # Placeholder

    if st.sidebar.button("Logout"):
        st.session_state["access_token"] = None
        st.experimental_rerun()

else:
    # User is not authenticated
    st.title("🏟️ AFC Venue - MBM Hospitality")
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    This app provides insights into MBM Sales Performance and User Metrics. 

    **Note:** Please log in using AFC credentials to access the app.
    """)

    if st.button("Log in"):
        # Generate authorization URL with PKCE
        authorization_url = f"{authority}/oauth2/v2.0/authorize"
        url, state = session.create_authorization_url(
            authorization_url,
            code_challenge=st.session_state["code_challenge"],
            code_challenge_method="S256"  # Use PKCE method
        )
        st.session_state["oauth_state"] = state
        logging.debug(f"Generated Authorization URL: {url}")
        st.write(f"[Click here to log in]({url})")
        st.stop()

    # Capture the authorization code automatically from the redirect
    query_params = st.query_params  # Use the updated `st.query_params`
    code = query_params.get("code", [None])[0]

    if code:
        logging.debug(f"Authorization Code Received: {code}")
        try:
            # Log all parameters before token exchange
            token_url = f"{authority}/oauth2/v2.0/token"
            logging.debug("Attempting to exchange authorization code for tokens...")
            logging.debug(f"Token URL: {token_url}")
            logging.debug(f"Code Verifier: {st.session_state['code_verifier']}")
            logging.debug(f"Redirect URI: {redirect_uri}")
            logging.debug(f"Client ID: {client_id}")

            token = session.fetch_token(
                token_url,
                code=code,
                code_verifier=st.session_state["code_verifier"],  # PKCE verifier
            )
            st.session_state["access_token"] = token["access_token"]
            st.success("Login successful!")
            logging.debug(f"Access Token: {st.session_state['access_token']}")
            st.experimental_rerun()
        except Exception as e:
            logging.error(f"Error during token exchange: {e}")
            st.error("Failed to log in. Check the logs for details.")
    else:
        logging.error("Authorization Code not found in the query parameters.")
        st.error("Failed to retrieve authorization code. Please try logging in again.")

            

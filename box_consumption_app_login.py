import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import logging
import importlib


# Configure logging
logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler()  # Ensures logs are visible in the Streamlit terminal
    ]
)

# Import modules dynamically to handle errors gracefully
try:
    import box_consump_app
    importlib.reload(box_consump_app)
except ImportError as e:
    logging.error(f"Failed to import 'sales_performance': {e}")
    box_consump_app = None

# Load environment variables
load_dotenv()
    
# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID_1")
TENANT_ID = os.getenv("TENANT_ID_1")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_1")
REDIRECT_URI = os.getenv("REDIRECT_URI_1")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]


# MSAL Confidential Client Application
app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    client_credential=CLIENT_SECRET,
    authority=AUTHORITY
)

# Initialize session states
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "redirected" not in st.session_state:
    st.session_state["redirected"] = False
if "dashboard_data" not in st.session_state:
    st.session_state["dashboard_data"] = None  # Store dashboard data
    
    

# App Header with a logo
st.image("assets/arsenal_crest_gold.png", width=150)  # Placeholder for the logo
st.title("🏟️ Box Log Processing Tool")
st.markdown("---")  # A horizontal line for better UI

# Handle login
if not st.session_state["authenticated"]:
    # Display Welcome Message
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!
    **Log in to access the dashboards.**
    """)

    # Generate the Login URL
    login_url = app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)

    # Display the Login Button
    st.markdown(f"""
            <a href="{login_url}" target="_blank" style="
                text-decoration:none;
                color:white;
                background-color:#FF4B4B;
                padding:15px 25px;
                border-radius:5px;
                font-size:18px;
                display:inline-block;">
                🔐 Log in with Microsoft Entra ID
            </a>
        </div>
    """, unsafe_allow_html=True)

    # Process login by checking query parameters for the authorization code
    query_params = st.experimental_get_query_params()
    if "code" in query_params and not st.session_state.get("redirected", False):
        auth_code = query_params["code"][0]
        logging.info("Authorization code received. Initiating login process...")
        with st.spinner("🔄 Logging you in..."):
            try:
                result = app.acquire_token_by_authorization_code(
                    code=auth_code,
                    scopes=SCOPES,
                    redirect_uri=REDIRECT_URI
                )
                if "access_token" in result:
                    st.session_state["access_token"] = result["access_token"]
                    st.session_state["authenticated"] = True
                    st.session_state["redirected"] = True
                    logging.info("Login successful. Redirecting user...")
                    st.success("🎉 Login successful! Redirecting...")
                    st.rerun()
                else:
                    logging.warning("Failed to acquire access token.")
                    st.error("❌ Failed to log in. Please try again.")
            except Exception as e:
                logging.error(f"An error occurred during login: {e}")
                if "invalid_grant" in str(e):
                    st.error("❌ The authorization code is invalid or expired. Please log in again.")
                else:
                    st.error(f"❌ An unexpected error occurred: {str(e)}")
    else:
        if "code" not in query_params:
            logging.info("No authorization code in query parameters.")
            # st.info("🔑 Please log in using the authentication portal.")

# Initialize logout state
    if "logout_triggered" not in st.session_state:
        st.session_state["logout_triggered"] = False

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = True  # Default state is logged in

    # Logout Button
    if st.sidebar.button("🔓 Logout"):
        if not st.session_state["logout_triggered"]:
            logging.info("User logged out.")
            st.session_state["logout_triggered"] = True
            st.session_state["logged_in"] = False  # Mark as logged out
            st.session_state.clear()
            st.success("✅ You have been logged out successfully!")
            st.rerun()  # Trigger a full rerun

    # Handle post-logout state
    if st.session_state.get("logout_triggered", False):
        st.session_state.clear()  # Clear session state
        st.session_state["logout_triggered"] = True  # Maintain logout state to avoid flicker
        st.stop()  # Stop further execution to avoid login checks

# Footer Section
st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? <a href="mailto:cmunthali@arsenal.co.uk" style="text-decoration:none; color:#FF4B4B;">Contact: cmunthali@arsenal.co.uk</a>
    </div>
""", unsafe_allow_html=True)

import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import logging
import importlib

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

# Load environment variables
load_dotenv()

# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID_1")
TENANT_ID = os.getenv("TENANT_ID_1")
CLIENT_SECRET = os.getenv("CLIENT_SECRET_1")
REDIRECT_URI = os.getenv("REDIRECT_URI_1")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]

# MSAL Client
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

# App Header
st.image("assets/arsenal_crest_gold.png", width=150)
st.title("🏟️ Box Log Processing Tool")
st.markdown("---")

# Process login
query_params = st.experimental_get_query_params()
logging.info(f"Query parameters received: {query_params}")

if "code" in query_params and not st.session_state["authenticated"]:
    auth_code = query_params["code"][0]
    logging.info("Authorization code received. Initiating login process...")

    with st.spinner("🔄 Logging you in..."):
        try:
            result = app.acquire_token_by_authorization_code(
                code=auth_code,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )
            logging.info(f"Token acquisition result: {result}")

            if "access_token" in result:
                st.session_state["access_token"] = result["access_token"]
                st.session_state["authenticated"] = True
                st.session_state["redirected"] = True
                logging.info("✅ Login successful! Session updated.")

                st.success("🎉 Login successful! Redirecting...")
                st.rerun()  # Force refresh
            else:
                logging.warning("⚠️ No access token received.")
                st.error("❌ Failed to log in. Please try again.")
        except Exception as e:
            logging.error(f"🚨 Login error: {e}")
            st.error(f"❌ An error occurred: {str(e)}")

# Login Button (If Not Logged In)
if not st.session_state["authenticated"]:
    st.markdown("**Log in to access the Box Consumption Tool.**")
    login_url = app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)
    st.markdown(f"""
        <a href="{login_url}" target="_blank" style="
            text-decoration:none;
            color:white;
            background-color:#FF4B4B;
            padding:15px 25px;
            border-radius:5px;
            font-size:18px;
            display:inline-block;">
            🔐 Log in
        </a>
    """, unsafe_allow_html=True)
    st.stop()  # Prevent further execution

# After Login: Let the user choose the processing version
if st.session_state.get("authenticated", False):  # Ensure authentication exists
    st.success("✅ Logged in successfully!")

    # Provide a radio button for version selection in the sidebar
    version_choice = st.sidebar.radio(
        "Select Processing Logic", 
        ["Formatting - First Version", "Formatting - Second Version", "Guest Portal Insights"]
    )
    try:
        # Import the selected module based on user choice
        if version_choice == "Formatting - Second Version":
            import box_consumption_app_login_v2 as app_module
        elif version_choice == "Formatting - First Version":
            import box_consumption_app_login as app_module
        elif version_choice == "Guest Portal Insights":
            import guest_portal_metrics as app_module
        else:
            raise ImportError("Invalid selection")

        # Reload the module to ensure the latest code is used
        importlib.reload(app_module)

        # Call the run() function from the selected module
        app_module.run()

    except ImportError as e:
        logging.error(f"❌ Failed to load main app: {e}")
        st.error("❌ Could not load the application. Please try again.")

# Logout Button
if st.sidebar.button("🔓 Logout"):
    st.session_state.clear()
    st.success("✅ You have been logged out successfully!")
    st.rerun()

# Footer Section
st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2025  
        Need help? <a href="mailto:cmunthali@arsenal.co.uk" style="text-decoration:none; color:#FF4B4B;">Contact: cmunthali@arsenal.co.uk</a>
    </div>
""", unsafe_allow_html=True)

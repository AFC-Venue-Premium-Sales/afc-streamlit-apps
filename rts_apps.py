import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import logging
import sales_performance
import user_performance_api

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Load environment variables
load_dotenv()

# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
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
if "filtered_data" not in st.session_state:
    st.session_state["filtered_data"] = None  # Holds the output DataFrame

# Azure AD Login URL
def azure_ad_login():
    return app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)

# Function to fetch and reload data
def fetch_and_store_data():
    """Execute tjt_hosp_api and reload its output."""
    with st.spinner("Fetching data from the API..."):
        try:
            # Log the start of the fetching process
            logging.info("Fetching data from tjt_hosp_api...")
            
            # Import and execute `tjt_hosp_api`
            import tjt_hosp_api
            from tjt_hosp_api import filtered_df_without_seats  # Output DataFrame

            # Update session state with new data
            st.session_state["filtered_data"] = filtered_df_without_seats
            logging.info("Data successfully fetched and stored.")
            st.success("✅ Hospitality data fetched successfully!")
        except Exception as e:
            error_message = f"Failed to fetch data: {str(e)}"
            logging.error(error_message)
            st.error(f"❌ {error_message}")

# App Header with a logo
st.image("assets/arsenal-logo.png", width=250)  # Placeholder for the logo
st.title("🏟️ AFC Venue - MBM Hospitality")
st.markdown("---")  # A horizontal line for better UI

if not st.session_state["authenticated"]:
    # Instructions for SSO Login
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!  
    **Please log in using AFC credentials to access the following modules:**

    - **📊 Sales Performance**: Analyze and track sales data.
    - **📈 User Performance**: Monitor and evaluate team performance metrics.
    
    """)

    # Login Section
    login_url = azure_ad_login()
    st.markdown(f"""
        <div style="text-align:center;">
            <a href="{azure_ad_login()}" target="_blank" style="
                text-decoration:none;
                color:white;
                background-color:#FF4B4B;
                padding:10px 20px;
                border-radius:5px;
                font-size:16px;">
                🔐 Log in Microsoft Entra ID
            </a>
        </div>
    """, unsafe_allow_html=True)

    # Process login
    query_params = st.experimental_get_query_params()
    if "code" in query_params and not st.session_state["redirected"]:
        auth_code = query_params["code"][0]
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
                    st.success("🎉 Login successful! Redirecting...")
                    st.experimental_rerun()  # Reload the app to show authenticated view
                else:
                    st.error("❌ Failed to log in. Please try again.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
else:
    # Fetch data on app load if not already fetched
    if st.session_state["filtered_data"] is None:
        logging.info("Fetching data on app load...")
        fetch_and_store_data()

    # User Profile Card
    st.sidebar.markdown("### 👤 Logged in User")
    st.sidebar.info("User: **Azure AD User**\nRole: **Premium Exec**")
    
    # Navigation Sidebar
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance"],
        format_func=lambda x: x.split(" ")[1],  # Display just the module names
    )
    
    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        logging.info("Refresh button clicked. Fetching new data...")
        fetch_and_store_data()  # Reload data
        st.experimental_rerun()  # Trigger rerun to reflect updated data
    
    # Add Loading Indicator
    with st.spinner("🔄 Loading..."):
        if app_choice == "📊 Sales Performance":
            sales_performance.run_app()
        elif app_choice == "📈 User Performance":
            user_performance_api.run_app()

    # Logout Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        with st.spinner("🔄 Logging out..."):
            logging.info("User logged out.")
            # Clear session state
            st.session_state.clear()  # Clears all session state values
            st.success("✅ You have been logged out successfully!")
            # Redirect to the login screen
            st.experimental_set_query_params()  # Clears query params to prevent re-login issues
            st.experimental_rerun()

# Footer Section
st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? Contact [cmunthali@arsenal.co.uk](mailto:cmunthali@arsenal.co.uk)
    </div>
""", unsafe_allow_html=True)

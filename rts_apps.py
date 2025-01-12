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
    import sales_performance
    importlib.reload(sales_performance)
except ImportError as e:
    logging.error(f"Failed to import 'sales_performance': {e}")
    sales_performance = None

try:
    import user_performance_api
    importlib.reload(user_performance_api)
except ImportError as e:
    logging.error(f"Failed to import 'user_performance_api': {e}")
    user_performance_api = None

try:
    import ticket_exchange_report
    importlib.reload(ticket_exchange_report)
except ImportError as e:
    logging.error(f"Failed to import 'ticket_exchange_report': {e}")
    ticket_exchange_report = None
    
try:
    import sales_dashboard 
    importlib.reload(sales_dashboard)
except ImportError as e:
    logging.error(f"Failed to import 'sales_dashboard': {e}")
    sales_dashboard = None

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
if "dashboard_data" not in st.session_state:
    st.session_state["dashboard_data"] = None  # Store dashboard data


# Function to reload data
def reload_data():
    import importlib
    logging.info("🔄 Reloading tjt_hosp_api...")
    try:
        # Reload the module dynamically
        tjt_hosp_api = importlib.import_module('tjt_hosp_api')
        importlib.reload(tjt_hosp_api)

        # Validate the reloaded data
        filtered_df_without_seats = getattr(tjt_hosp_api, 'filtered_df_without_seats', None)
        if filtered_df_without_seats is None or filtered_df_without_seats.empty:
            raise ValueError("filtered_df_without_seats is None or empty after reload.")

        # Log successful reload
        logging.info(f"✅ Data reloaded successfully. Rows: {len(filtered_df_without_seats)}")
        st.success("✅ Data refreshed successfully!")

        # Reload dependent modules dynamically
        importlib.reload(sales_performance)
        importlib.reload(user_performance_api)

        # Trigger a rerun to refresh the app state
        st.rerun()

    except Exception as e:
        # Handle and log errors gracefully
        logging.error(f"❌ Failed to reload tjt_hosp_api: {e}")
        st.error(f"❌ Failed to reload data: {e}")




# App Header with a logo
st.image("assets/arsenal_colour-banner.png", width=500)  # Placeholder for the logo
st.title("🏟️ AFC Venue - MBM Hospitality")
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


else:
    # Sidebar Navigation
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance", "📄 Ticket Exchange Report", "📊 Live Sales Dashboard"],
        format_func=lambda x: x.split(" ")[1],
    )

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        logging.info("🔄 Refreshing data...")
        reload_data()  # Call the reload function
        # st.rerun()  # Trigger a full app rerun after reload

    # Update app_registry with the new dashboard
    app_registry = {
        "📊 Sales Performance": sales_performance.run_app,
        "📈 User Performance": user_performance_api.run_app,
        "📄 Ticket Exchange Report": ticket_exchange_report.run_app,
        "📊 Live Sales Dashboard": sales_dashboard.run_dashboard,  # Add your new dashboard here
    }

    app_function = app_registry.get(app_choice)
    if app_function:
        try:
            with st.spinner("🔄 Loading..."):
                app_function()
            st.success(f"✅ {app_choice} app loaded successfully!")
        except Exception as e:
            st.error(f"❌ An error occurred while loading the app: {e}")
            logging.error(f"Error loading app '{app_choice}': {e}")
    else:
        st.error("❌ Invalid selection. Please choose a valid app option.")


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

import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import logging
import importlib
import sales_performance
import user_performance_api
import ticket_exchange_report  # Import the new module

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
if "dashboard_data" not in st.session_state:
    st.session_state["dashboard_data"] = None  # Store dashboard data


# Function to reload data
def reload_data():
    """Reloads data from `tjt_hosp_api`."""
    logging.info("🔄 Reloading data from `tjt_hosp_api`...")
    try:
        import tjt_hosp_api
        importlib.reload(tjt_hosp_api)

        # Verify data loading
        from tjt_hosp_api import filtered_df_without_seats
        required_columns = ['Fixture Name', 'Order Id', 'First Name']
        missing_columns = [
            col for col in required_columns if col not in filtered_df_without_seats.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Update the dashboard data
        st.session_state["dashboard_data"] = filtered_df_without_seats
        logging.info(f"✅ Data successfully reloaded. Total rows: {len(filtered_df_without_seats)}")
        st.success("✅ Data refreshed successfully!")

    except Exception as e:
        logging.error(f"❌ Failed to reload data: {e}")
        st.error(f"❌ Failed to reload data: {e}")


# App Header with a logo
st.image("assets/arsenal-logo.png", width=250)  # Placeholder for the logo
st.title("🏟️ AFC Venue - MBM Hospitality")
st.markdown("---")  # A horizontal line for better UI

# Handle login
if not st.session_state["authenticated"]:
    # Display Welcome Message
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!
    **Log in using AFC credentials to access the dashboards.**
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
                    st.stop()
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


else:
    # Sidebar Navigation
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance", "📄 Ticket Exchange Report"],
        format_func=lambda x: x.split(" ")[1],
    )

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        logging.info("🔄 Refresh button clicked. Attempting to reload data...")
        reload_data()  # Call the reload function
        logging.info("🔄 Data refresh process triggered successfully.")
        st.stop()

    # Check if data is loaded before rendering the dashboard
    if st.session_state["dashboard_data"] is None:
        st.warning("⚠️ Data not loaded. Please refresh to load the latest data.")
        st.stop()

    # Handle module choice dynamically
    app_registry = {
        "📊 Sales Performance": sales_performance.run_app,
        "📈 User Performance": user_performance_api.run_app,
        "📄 Ticket Exchange Report": ticket_exchange_report.run_app
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

    # Logout Button
    if st.sidebar.button("🔓 Logout"):
        logging.info("User logged out.")
        st.session_state.clear()
        st.warning("🔒 You have been logged out. Please log in again.")
        st.stop()

# Footer Section
st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? <a href="mailto:cmunthali@arsenal.co.uk" style="text-decoration:none; color:#FF4B4B;">Contact: cmunthali@arsenal.co.uk</a>
    </div>
""", unsafe_allow_html=True)

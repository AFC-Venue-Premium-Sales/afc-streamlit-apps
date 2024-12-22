import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import logging
import importlib
import sales_performance
import user_performance_api
import datetime

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
if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = None
if "next_refresh_time" not in st.session_state:
    st.session_state["next_refresh_time"] = None
if "filtered_data" not in st.session_state:
    st.session_state["filtered_data"] = None


# Cached data fetcher
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_data():
    """Fetches data from `tjt_hosp_api` and validates required columns."""
    logging.info("Fetching data from tjt_hosp_api...")
    
    # Dynamically reload `tjt_hosp_api`
    import tjt_hosp_api
    importlib.reload(tjt_hosp_api)

    # Extract the DataFrame
    from tjt_hosp_api import filtered_df_without_seats
    required_columns = ['Fixture Name', 'Order Id', 'First Name']

    # Validate required columns
    missing_columns = [
        col for col in required_columns if col not in filtered_df_without_seats.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    logging.info("Data successfully fetched and validated.")
    return filtered_df_without_seats


# App Header with a logo
st.image("assets/arsenal-logo.png", width=250)  # Placeholder for the logo
st.title("🏟️ AFC Venue - MBM Hospitality")
st.markdown("---")  # A horizontal line for better UI

if not st.session_state["authenticated"]:
    # Display Welcome Message
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!
    **Log in using AFC credentials to access your dashboard.**
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
                    st.rerun()  # Reload the app to show authenticated view
                else:
                    st.error("❌ Failed to log in. Please try again.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")


else:
    # Always fetch the latest data (cached or fresh)
    try:
        current_time = datetime.datetime.now()

        # Auto-fetch data on app load or when cache expires
        if st.session_state["filtered_data"] is None or st.session_state["next_refresh_time"] is None:
            logging.info("Fetching data for the first time or cache expired.")
            st.session_state["filtered_data"] = fetch_data()
            st.session_state["last_refresh_time"] = current_time
            st.session_state["next_refresh_time"] = current_time + datetime.timedelta(seconds=300)
        elif current_time >= st.session_state["next_refresh_time"]:
            logging.info("Cache expired. Fetching fresh data...")
            st.cache_data.clear()  # Clear the cache
            st.session_state["filtered_data"] = fetch_data()
            st.session_state["last_refresh_time"] = current_time
            st.session_state["next_refresh_time"] = current_time + datetime.timedelta(seconds=300)

        logging.info(f"Using data fetched at: {st.session_state['last_refresh_time']}.")
        logging.info(f"Next refresh scheduled at: {st.session_state['next_refresh_time']}.")

        # Add Force Refresh Button
        if st.sidebar.button("🔄 Refresh Data"):
            logging.info("Force refreshing data...")
            st.cache_data.clear()  # Clear cache
            st.session_state["filtered_data"] = fetch_data()  # Fetch fresh data
            st.session_state["last_refresh_time"] = current_time
            st.session_state["next_refresh_time"] = current_time + datetime.timedelta(seconds=300)
            st.success(f"Data refreshed at {st.session_state['last_refresh_time']}!")

    except Exception as e:
        logging.error(f"Failed to fetch data: {e}")
        st.error(f"❌ Failed to fetch data: {e}")

    # Sidebar Navigation
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance"],
        format_func=lambda x: x.split(" ")[1],
    )
    
    # Handle module choice
    with st.spinner("🔄 Loading..."):
        if app_choice == "📊 Sales Performance":
            sales_performance.run_app()
        elif app_choice == "📈 User Performance":
            user_performance_api.run_app()

    # Logout Button
    if st.sidebar.button("🔓 Logout"):
        logging.info("User logged out.")
        st.session_state.clear()
        st.success("✅ You have been logged out successfully!")

st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? <a href="mailto:cmunthali@arsenal.co.uk" style="text-decoration:none; color:#FF4B4B;">Contact: cmunthali@arsenal.co.uk</a>
    </div>
""", unsafe_allow_html=True)

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
    query_params = st.experimental_get_query_params()
    if "code" in query_params and not st.session_state["redirected"]:
        # Show a custom loading animation
        st.markdown("""
        <div style="text-align:center; margin-top:50px;">
            <p style="font-size:18px; color:#4B4B4B;">🔄 Authenticating your credentials...</p>
        </div>
        """, unsafe_allow_html=True)

        # Start authentication process
        with st.spinner("🔄 Logging you in and preparing your dashboard..."):
            try:
                # Retrieve the authorization code from query parameters
                auth_code = query_params["code"][0]

                # Exchange the authorization code for an access token
                result = app.acquire_token_by_authorization_code(
                    code=auth_code,
                    scopes=SCOPES,
                    redirect_uri=REDIRECT_URI
                )

                # Handle successful login
                if "access_token" in result:
                    st.session_state["access_token"] = result["access_token"]
                    st.session_state["authenticated"] = True
                    st.session_state["redirected"] = True
                    st.success("🎉 Login successful!")
                    st.rerun()  # Reload the app to display the authenticated view

                # Handle login failure
                else:
                    st.error("❌ Failed to log in. Please try again.")

            # Handle exceptions during login
            except Exception as e:
                st.error(f"❌ Error during login: {e}")


else:
    # Always fetch the latest data (cached or fresh)
    try:
        if "filtered_data" not in st.session_state or st.session_state["next_refresh_time"] is None:
            st.session_state["filtered_data"] = fetch_data()
            st.session_state["last_refresh_time"] = datetime.datetime.now()
            st.session_state["next_refresh_time"] = st.session_state["last_refresh_time"] + datetime.timedelta(seconds=300)
            logging.info(f"Data refreshed at: {st.session_state['last_refresh_time']}.")
            logging.info(f"Next refresh scheduled at: {st.session_state['next_refresh_time']}.")
        else:
            logging.info(f"Using cached data. Next refresh at: {st.session_state['next_refresh_time']}.")

    except Exception as e:
        logging.error(f"Failed to fetch data: {e}")
        st.error(f"❌ Failed to fetch data: {e}")
    
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance"],
        format_func=lambda x: x.split(" ")[1],
    )
    
    # Dummy Refresh Button
    # if st.sidebar.button("🔄 Refresh Data"):
    #     logging.info("User clicked Refresh Data button.")
    #     st.success("🔄 Refresh is automatic in the background. Check logs for details.")

    with st.spinner("🔄 Loading..."):
        if app_choice == "📊 Sales Performance":
            sales_performance.run_app()
        elif app_choice == "📈 User Performance":
            user_performance_api.run_app()

    if st.sidebar.button("🔓 Logout"):
        with st.spinner("🔄 Logging out..."):
            logging.info("User logged out.")
            st.session_state.clear()
            st.success("✅ You have been logged out successfully!")
            st.experimental_set_query_params()
            st.rerun()

st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? <a href="mailto:cmunthali@arsenal.co.uk" style="text-decoration:none; color:#FF4B4B;">Contact: cmunthali@arsenal.co.uk</a>
    </div>
""", unsafe_allow_html=True)


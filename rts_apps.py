import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import logging
import importlib
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


# Cached data fetcher
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_data():
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

    logging.info("Data successfully fetched.")
    return filtered_df_without_seats


# App Header with a logo
st.image("assets/arsenal-logo.png", width=250)  # Placeholder for the logo
st.title("🏟️ AFC Venue - MBM Hospitality")
st.markdown("---")  # A horizontal line for better UI

if not st.session_state["authenticated"]:
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!  
    **Please log in using AFC credentials to access the following modules:**

    - **📊 Sales Performance**: Analyze and track sales data.
    - **📈 User Performance**: Monitor and evaluate team performance metrics.
    """)

    login_url = app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)
    st.markdown(f"""
        <div style="text-align:center;">
            <a href="{login_url}" target="_blank" style="
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
                    st.rerun()
                else:
                    st.error("❌ Failed to log in. Please try again.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
else:
    # Always fetch the latest data (cached or fresh)
    try:
        data = fetch_data()  # Fetch cached or fresh data
    except Exception as e:
        logging.error(f"Failed to fetch data: {e}")
        st.error(f"❌ Failed to fetch data: {e}")
        data = None  # Handle gracefully if data can't be fetched

    st.sidebar.markdown("### 👤 Logged in User")
    st.sidebar.info("User: **Azure AD User**\nRole: **Premium Exec**")
    
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance"],
        format_func=lambda x: x.split(" ")[1],
    )
    
    # Dummy Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        st.info("🔄 Refreshing data... Please wait.")
        # No backend action occurs; refresh is handled by `@st.cache_data`

    # Display current data
    if data is not None:
        st.write(data)  # Replace with your display logic

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
        Need help? Contact [cmunthali@arsenal.co.uk](mailto:cmunthali@arsenal.co.uk)
    </div>
""", unsafe_allow_html=True)

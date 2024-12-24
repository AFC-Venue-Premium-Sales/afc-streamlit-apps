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

# Function to reload data
def reload_data():
    """Reloads data from `tjt_hosp_api`."""
    logging.info("🔄 [START] Data reload process initiated.")
    try:
        import tjt_hosp_api
        importlib.reload(tjt_hosp_api)

        # Log current data rows
        if "dashboard_data" in st.session_state and st.session_state["dashboard_data"] is not None:
            previous_row_count = len(st.session_state["dashboard_data"])
        else:
            previous_row_count = 0
        logging.info(f"🔢 Rows before reload: {previous_row_count}")

        # Reload data from the API
        from tjt_hosp_api import filtered_df_without_seats
        required_columns = ['Fixture Name', 'Order Id', 'First Name']
        missing_columns = [
            col for col in required_columns if col not in filtered_df_without_seats.columns
        ]
        if missing_columns:
            logging.error(f"❌ Missing required columns: {missing_columns}")
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Update data in the session state
        st.session_state["dashboard_data"] = filtered_df_without_seats
        current_row_count = len(filtered_df_without_seats)

        # Log change in data rows
        logging.info(f"🔢 Rows after reload: {current_row_count} (Change: {current_row_count - previous_row_count})")
        st.success("✅ Data refreshed successfully!")
    except Exception as e:
        logging.error(f"❌ Failed to reload data: {e}")
        st.error(f"❌ Failed to reload data: {e}")
    finally:
        logging.info("🔄 [END] Data reload process completed.")

# App Header
st.image("assets/arsenal-logo.png", width=250)
st.title("🏟️ AFC Venue - MBM Hospitality")
st.markdown("---")

# Handle login
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # Display login interface
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!
    Log in to access the dashboards.
    """)

    # Generate login URL
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
            🔐 Log in with Microsoft Entra ID
        </a>
    """, unsafe_allow_html=True)

else:
    # Sidebar Navigation
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance", "📄 Ticket Exchange Report"],
        format_func=lambda x: x.split(" ")[1],
    )

    # Refresh Data Button
    if st.sidebar.button("🔄 Refresh Data"):
        logging.info("🔄 Refresh button clicked.")
        reload_data()
        logging.info("🔄 Data refresh process successfully triggered.")

    # Render the chosen module
    if app_choice == "📄 Ticket Exchange Report":
        logging.info("📄 Loading Ticket Exchange Report module...")
        ticket_exchange_report.run_app()
    else:
        if "dashboard_data" not in st.session_state or st.session_state["dashboard_data"] is None:
            st.warning("⚠️ Data not loaded. Please refresh to load the latest data.")
            st.stop()
        else:
            # Dynamically load selected module
            app_registry = {
                "📊 Sales Performance": sales_performance.run_app,
                "📈 User Performance": user_performance_api.run_app,
            }
            app_function = app_registry.get(app_choice)
            if app_function:
                try:
                    with st.spinner("🔄 Loading..."):
                        app_function()
                    logging.info(f"✅ {app_choice} module loaded successfully.")
                except Exception as e:
                    logging.error(f"❌ Failed to load {app_choice}: {e}")
                    st.error(f"❌ An error occurred while loading the app: {e}")

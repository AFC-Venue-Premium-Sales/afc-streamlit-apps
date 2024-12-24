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
    """Reloads data from `tjt_hosp_api` script."""
    logging.info("🔄 Reloading `tjt_hosp_api`...")
    try:
        import tjt_hosp_api
        importlib.reload(tjt_hosp_api)

        # Validate the DataFrame
        required_columns = ['Fixture Name', 'Order Id', 'First Name']
        missing_columns = [
            col for col in required_columns if col not in tjt_hosp_api.filtered_df_without_seats.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Update session state
        previous_row_count = len(st.session_state.get("dashboard_data", []))
        st.session_state["dashboard_data"] = tjt_hosp_api.filtered_df_without_seats
        current_row_count = len(tjt_hosp_api.filtered_df_without_seats)

        logging.info(f"✅ Reload complete. Row change: {current_row_count - previous_row_count}")
        st.success("✅ Data refreshed successfully!")
    except Exception as e:
        logging.error(f"❌ Error reloading data: {e}")
        st.error(f"❌ Failed to reload data: {e}")
    finally:
        logging.info("🔄 Data reload finished.")




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
    # Sidebar Navigation
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance", "📄 Ticket Exchange Report"],
        format_func=lambda x: x.split(" ")[1],
    )

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        logging.info("🔄 [CLICKED] Refresh button pressed by the user.")
        logging.info("🔄 Initiating data reload process...")
        reload_data()  # Call the reload function
        logging.info("✅ Data refresh process completed successfully.")
        st.stop()  # Replace deprecated st.rerun() with st.stop() to trigger a reload



    # Handle module choice dynamically
    app_registry = {
    "📊 Sales Performance": lambda: sales_performance.run_app(st.session_state["dashboard_data"]),
    "📈 User Performance": lambda: user_performance_api.run_app(st.session_state["dashboard_data"]),
    "📄 Ticket Exchange Report": lambda: ticket_exchange_report.run_app
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
            st.stop()

   # Handle post-logout state
    if not st.session_state.get("authenticated", True):
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

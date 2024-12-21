import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import sales_performance
import user_performance_api

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
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("access_token", None)
st.session_state.setdefault("redirected", False)
st.session_state.setdefault("shared_data", None)  # Store shared data here

# Azure AD Login URL
def azure_ad_login():
    return app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)

# App Header with a logo
st.image("assets/arsenal-logo.png", width=250)  # Placeholder for the logo
st.title("🏟️ AFC Venue - MBM Hospitality")
st.markdown("---")  # A horizontal line for better UI

# Check for the logged_in query parameter
query_params = st.experimental_get_query_params()
if "logged_in" in query_params and query_params["logged_in"][0] == "true":
    st.session_state["authenticated"] = True

if not st.session_state["authenticated"]:
    # Instructions for SSO Login
    st.markdown("""
    ### 👋 Welcome to the Venue Hospitality App!  
    **Please log in using AFC credentials to access the following modules:**

    - **📊 Sales Performance**: Analyze and track sales data.
    - **📈 User Performance**: Monitor and evaluate team performance metrics.
    
    If you experience login issues, please contact [cmunthali@arsenal.co.uk](mailto:cmunthali@arsenal.co.uk).
    """)

    # Login Section
    login_url = azure_ad_login()
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
                    st.experimental_rerun()
                else:
                    st.error("❌ Failed to log in. Please try again.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
else:
    # User Profile Card
    st.sidebar.markdown("### 👤 Logged in User")
    st.sidebar.info("User: **Azure AD User**\nRole: **Premium Exec**")

    # Navigation Sidebar
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance"],
        format_func=lambda x: x.split(" ")[1],
    )

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        st.experimental_set_query_params(refresh="true")

    # Check if refresh is required
    query_params = st.experimental_get_query_params()
    if query_params.get("refresh"):
        st.experimental_set_query_params()  # Clear query parameters
        with st.spinner("🔄 Fetching the latest data..."):
            try:
                # Refresh sales or user performance data based on the selected module
                if app_choice == "📊 Sales Performance":
                    st.session_state["shared_data"] = sales_performance.refresh_data()
                elif app_choice == "📈 User Performance":
                    st.session_state["shared_data"] = user_performance_api.refresh_data()
                st.success("✅ Data refreshed successfully!")
            except Exception as e:
                st.error(f"❌ Failed to refresh data: {str(e)}")

    # Add Loading Indicator
    with st.spinner("🔄 Loading..."):
        shared_data = st.session_state.get("shared_data")
        if app_choice == "📊 Sales Performance":
            sales_performance.run_app(shared_data)
        elif app_choice == "📈 User Performance":
            user_performance_api.run_app(shared_data)

    # Logout Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        with st.spinner("🔄 Logging out..."):
            st.session_state.clear()  # Clear session state
            st.experimental_rerun()

# Footer Section
st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? Contact [cmunthali@arsenal.co.uk]
    </div>
""", unsafe_allow_html=True)

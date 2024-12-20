import streamlit as st
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import os
import requests
import sales_performance
import user_performance_api
from datetime import datetime

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
if "user_name" not in st.session_state:
    st.session_state["user_name"] = "Azure AD User"

# Function to fetch user details from Microsoft Graph API
def get_user_details(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    if response.status_code == 200:
        return response.json().get("displayName", "Azure AD User")
    return "Azure AD User"

# Azure AD Login URL
def azure_ad_login():
    return app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)

# Refresh Sales or User Data
def refresh_data(selected_module):
    """Refresh data for the selected module."""
    if selected_module == "📊 Sales Performance":
        sales_performance.run_app()
    elif selected_module == "📈 User Performance":
        user_performance_api.run_app()

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
                🔐 Log in with Microsoft Entra ID
            </a>
        </div>
    """, unsafe_allow_html=True)

    # Process login
    query_params = st.query_params
    if "code" in query_params:
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
                    st.session_state["user_name"] = get_user_details(result["access_token"])
                    st.success("🎉 Login successful!")
                else:
                    st.error("❌ Login failed. Please try again.")
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
else:
    # Display user details in the sidebar
    st.sidebar.markdown(f"### 👤 Logged in as: **{st.session_state['user_name']}**")

    # Navigation Sidebar
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Choose Module",
        ["📊 Sales Performance", "📈 User Performance"],
        format_func=lambda x: x.split(" ")[1],  # Display just the module names
    )

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        with st.spinner("Refreshing data..."):
            refresh_data(app_choice)
            st.success("✅ Data refreshed successfully!")

    # Add Loading Indicator
    with st.spinner("🔄 Loading..."):
        if app_choice == "📊 Sales Performance":
            sales_performance.run_app()
        elif app_choice == "📈 User Performance":
            user_performance_api.run_app()

    # Logout Button
    if st.sidebar.button("🔓 Logout"):
        st.session_state.clear()
        st.success("✅ Logged out successfully!")

# Footer Section
st.markdown("---")
st.markdown("""
    <div style="text-align:center; font-size:12px; color:gray;">
        🏟️ **Arsenal Property** | All Rights Reserved © 2024  
        Need help? Contact [cmunthali@arsenal.co.uk]
    </div>
""", unsafe_allow_html=True)

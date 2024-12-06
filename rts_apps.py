
# import streamlit as st
# from itsdangerous import URLSafeTimedSerializer
# import smtplib
# from email.message import EmailMessage
# import re
# import sales_performance  
# import user_performance_api
# import os
# from dotenv import load_dotenv

# # Load variables from .env file
# load_dotenv()

# import os
# import logging

# logging.basicConfig(level=logging.DEBUG)

# # Check if environment variables are loaded
# logging.debug(f"EMAIL_SENDER: {os.getenv('EMAIL_SENDER')}")
# logging.debug(f"EMAIL_PASSWORD: {'Loaded' if os.getenv('EMAIL_PASSWORD') else 'Not Loaded'}")
# logging.debug(f"SMTP_SERVER: {os.getenv('SMTP_SERVER')}")
# logging.debug(f"SMTP_PORT: {os.getenv('SMTP_PORT')}")


# # Access variables
# SECRET_KEY = os.getenv("SECRET_KEY")
# EMAIL_SENDER = os.getenv("EMAIL_SENDER")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = os.getenv("SMTP_PORT")
# ALLOWED_DOMAINS = ["arsenal.co.uk", "con.arsenal.co.uk"] 

# # Serializer for generating/verifying tokens
# serializer = URLSafeTimedSerializer(SECRET_KEY)

# # Function to send the token via email
# def send_email(email, token):
#     msg = EmailMessage()
#     msg["Subject"] = "AFC Hosp Reporting App"
#     msg["From"] = EMAIL_SENDER
#     msg["To"] = email
#     msg.set_content(f"Your access code is: {token}\n\nThis is an automated email. Please do not reply.")

#     with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
#         smtp.starttls()  # Secure the connection
#         smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
#         smtp.send_message(msg)

# # Function to validate email domain
# def is_valid_email(email):
#     pattern = rf"^.+@({'|'.join(ALLOWED_DOMAINS)})$"
#     return re.match(pattern, email)

# # Step 1: User enters email
# if "is_authenticated" not in st.session_state:
#     st.session_state["is_authenticated"] = False

# if not st.session_state["is_authenticated"]:
#     st.title("🏟️ AFC Venue - MBM Hospitality")
#     st.markdown("""
#     **Welcome to the Venue Hospitality Dashboard!**  
#     This app provides insights into MBM Sales Performance and User Metrics. 

#     **MBM Sales Performance**:  
#     Analyse sales from MBM hospitality. 

#     **Premium Exec Metrics**:  
#     View and evaluate performance metrics from the Premium Team.
#     """)

#     # Ask for email
#     email = st.text_input("Enter your work email address")
#     if st.button("Send Access Code"):
#         # Validate email
#         if is_valid_email(email):  # Check if email matches allowed domains
#             # Generate token
#             token = serializer.dumps(email)  # Create a secure token
#             try:
#                 send_email(email, token)
#                 st.success(f"Access code sent to {email}. Check your inbox!")
#                 st.session_state["email"] = email
#             except Exception as e:
#                 st.error("Failed to send email. Please check your email configuration.")
#                 st.error(str(e))
#         else:
#             st.error("Invalid email address. Only @arsenal.co.uk and @con.arsenal.co.uk are allowed.")

#     # Step 2: User enters the code
#     if "email" in st.session_state:
#         code = st.text_input("Enter the access code sent to your email")
#         if st.button("Verify Code"):
#             try:
#                 # Validate token
#                 email_from_token = serializer.loads(code, max_age=300)  # Token valid for 5 minutes
#                 if email_from_token == st.session_state["email"]:
#                     st.session_state["is_authenticated"] = True
#                     st.session_state["app_choice"] = "📊 Sales Performance"  # Default page
#                     st.success("Access granted!")
#                     st.rerun()  # Redirect immediately after login
#                 else:
#                     st.error("Invalid access code.")
#             except Exception as e:
#                 st.error("Invalid or expired access code.")

# # Step 3: Show the app after authentication
# if st.session_state["is_authenticated"]:
#     # Sidebar navigation
#     st.sidebar.title("🧭 Navigation")
#     app_choice = st.sidebar.radio(
#         "Go to",
#         ["📊 Sales Performance", "📈 User Performance", "🔓 Sign Out"],
#         index=0 if "app_choice" not in st.session_state else
#         ["📊 Sales Performance", "📈 User Performance", "🔓 Sign Out"].index(st.session_state["app_choice"])
#     )

#     # Save the selected app choice
#     st.session_state["app_choice"] = app_choice

#     # Handle page navigation
#     if app_choice == "📊 Sales Performance":
#         sales_performance.run_app()  # Pulls and renders Sales Performance data

#     elif app_choice == "📈 User Performance":
#         user_performance_api.run_app()  # Pulls and renders User Performance data

#     elif app_choice == "🔓 Sign Out":
#         # Clear session state and redirect to login page
#         st.session_state.clear()
#         st.rerun()




# import streamlit as st
# import user_performance_api
# import sales_performance
# import os

# # Authentication function
# def login(username, password):
#     PASSWORD = "Hospitality2024!"
#     USERNAME = "HospVenue"
#     return username == USERNAME and password == PASSWORD
    

# # Initialize session state for authentication
# if 'authenticated' not in st.session_state:
#     st.session_state['authenticated'] = False
# if 'login_clicked' not in st.session_state:
#     st.session_state['login_clicked'] = False
    

# # Login button logic
# if not st.session_state['authenticated']:
#     st.title("🏟️ AFC Venue - MBM Hospitality")
    
#     # Description of the app
#     st.markdown("""
#     **Welcome to the Venue Hospitality Dashboard!**  
#     This app provides insights into MBM Sales Performance and User Metrics. 

#     **MBM Sales Performance**:  
#     Analyse sales from MBM hospitality. 

#     **Premium Exec Metrics**:  
#     View and evaluate performance metrics from the Premium Team.

#     **Note:** You will need to hit the submit button again after successfully entering your login details.
#     """)

#     if not st.session_state['login_clicked']:
#         if st.button("🔐 Login"):
#             st.session_state['login_clicked'] = True

#     if st.session_state['login_clicked']:
#         username = st.text_input("👤 Username")
#         password = st.text_input("🔑 Password", type="password")
#         if st.button("Submit"):
#             if login(username, password):
#                 st.session_state['authenticated'] = True
#                 st.success("🎉 Login successful!")
#             else:
#                 st.error("❌ Username or password is incorrect")

# else:
#     st.sidebar.title("🧭 Navigation")
#     app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

#     if app_choice == "📊 Sales Performance":
#         sales_performance.run_app()

#     elif app_choice == "📈 User Performance":
#         user_performance_api.run_app()
        
        






import streamlit as st
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse
from msal import PublicClientApplication

# MSAL Configuration
client_id = "9c350612-9d05-40f3-94e9-d348d92f446a"
tenant_id = "068cb91a-8be0-49d7-be3a-38190b0ba021"
redirect_uri = "https://afc-apps-hospitality.streamlit.app"
scopes = ["User.Read"]
authority = f"https://login.microsoftonline.com/{tenant_id}"

# Initialize MSAL app
app = PublicClientApplication(client_id, authority=authority)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()]
)

# Function to set up Chrome browser
def create_chrome_browser():
    try:
        options = ChromeOptions()
        options.add_argument("--headless")  # Enable headless mode for automation
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Automatically match the installed version of Chrome
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    except Exception as e:
        logging.error(f"Chrome browser initialization failed: {e}")
        st.error(f"An error occurred while starting Chrome: {e}")
        return None

# Login function using MSAL and Selenium
def login():
    flow = app.initiate_auth_code_flow(scopes=scopes, redirect_uri=redirect_uri)

    if "auth_uri" not in flow:
        st.error("Failed to initialize authentication.")
        return None

    auth_uri = flow["auth_uri"]
    browser = create_chrome_browser()
    if not browser:
        return None

    try:
        browser.get(auth_uri)

        # Wait for Azure to redirect back with an authorization code
        WebDriverWait(browser, 300).until(EC.url_contains(redirect_uri))
        redirected_url = browser.current_url
        browser.quit()

        # Parse the query parameters from the redirected URL
        url = urllib.parse.urlparse(redirected_url)
        query_params = dict(urllib.parse.parse_qsl(url.query))

        if "code" not in query_params:
            st.error("Authorization code not found.")
            return None

        # Acquire token using the authorization code
        result = app.acquire_token_by_auth_code_flow(flow, query_params)
        if "access_token" in result:
            st.success("Logged in successfully!")
            return result["access_token"]
        else:
            st.error("Failed to retrieve access token.")
            return None
    except Exception as e:
        browser.quit()
        st.error(f"An error occurred during login: {e}")
        return None

# Main App Logic
if "login_token" not in st.session_state:
    st.session_state["login_token"] = None

if not st.session_state["login_token"]:
    st.title("🏟️ AFC Venue - MBM Hospitality")
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    Please log in using your AFC credentials to continue.
    """)
    
    if st.button("🔐 Login"):
        token = login()
        if token:
            st.session_state["login_token"] = token
else:
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])
    st.sidebar.write("Logged in successfully!")

    # Render different views based on navigation choice
    if app_choice == "📊 Sales Performance":
        st.title("📊 Sales Performance")
        st.write("This section will display sales performance data.")
    elif app_choice == "📈 User Performance":
        st.title("📈 User Performance")
        st.write("This section will display user performance metrics.")


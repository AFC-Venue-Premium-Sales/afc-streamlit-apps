
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
import user_performance_api
import sales_performance
import hashlib
import base64
import os
from urllib.parse import urlencode
import requests

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler()
    ]
)

logging.debug("Starting the Streamlit app.")

# Azure app configuration
client_id = "9c350612-9d05-40f3-94e9-d348d92f446a"
redirect_uri = "https://afc-apps-hospitality.streamlit.app"
auth_url = "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021/oauth2/v2.0/authorize"
token_url = "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021/oauth2/v2.0/token"

# PKCE helper functions
def generate_pkce_pair():
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("utf-8")).digest()
    ).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge

# Initialize PKCE and session state
if "code_verifier" not in st.session_state or "code_challenge" not in st.session_state:
    code_verifier, code_challenge = generate_pkce_pair()
    st.session_state["code_verifier"] = code_verifier
    st.session_state["code_challenge"] = code_challenge
    logging.debug(f"PKCE Code Verifier: {code_verifier}")
    logging.debug(f"PKCE Code Challenge: {code_challenge}")

# Build the authorization URL with PKCE
def get_auth_url():
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "User.Read",
        "code_challenge": st.session_state["code_challenge"],  # Use session state
        "code_challenge_method": "S256",
    }
    url = f"{auth_url}?{urlencode(params)}"
    logging.debug(f"Authorization URL: {url}")
    return url

# Exchange authorization code for access token
def exchange_code_for_token(auth_code):
    data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "code_verifier": st.session_state["code_verifier"],  # Use session state
    }
    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Token Exchange Failed! {response.json()}")
        st.error("Failed to exchange token.")
        return None

# Streamlit app logic
if "auth_code" not in st.session_state:
    st.session_state["auth_code"] = None

if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

if not st.session_state["access_token"]:
    st.title("🏟️ AFC Venue - MBM Hospitality")
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    This app provides insights into MBM Sales Performance and User Metrics. 

    **MBM Sales Performance**:  
    Analyse sales from MBM hospitality. 

    **Premium Exec Metrics**:  
    View and evaluate performance metrics from the Premium Team.
    """)
    # Display the login link
    st.markdown(f"[Click here to log in]({get_auth_url()})")

    query_params = st.query_params  # Corrected to use st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        st.session_state["auth_code"] = auth_code
        logging.debug(f"Authorization Code Retrieved: {auth_code}")

        token_response = exchange_code_for_token(auth_code)
        if token_response:
            st.session_state["access_token"] = token_response["access_token"]
            st.success("Successfully authenticated!")
            st.experimental_rerun()
else:
    # User is authenticated
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])

    if app_choice == "📊 Sales Performance":
        sales_performance.run_app()
    elif app_choice == "📈 User Performance":
        user_performance_api.run_app()

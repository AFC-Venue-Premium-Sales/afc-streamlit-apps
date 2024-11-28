
import streamlit as st
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.message import EmailMessage
import re
import sales_performance  
import user_performance_api
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Access variables
SECRET_KEY = os.getenv("SECRET_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
ALLOWED_DOMAINS = ["arsenal.co.uk", "con.arsenal.co.uk"] 

# Serializer for generating/verifying tokens
serializer = URLSafeTimedSerializer(SECRET_KEY)

# Function to send the token via email
def send_email(email, token):
    msg = EmailMessage()
    msg["Subject"] = "AFC Hosp Reporting App"
    msg["From"] = EMAIL_SENDER
    msg["To"] = email
    msg.set_content(f"Your access code is: {token}\n\nThis is an automated email. Please do not reply.")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()  # Secure the connection
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

# Function to validate email domain
def is_valid_email(email):
    pattern = rf"^.+@({'|'.join(ALLOWED_DOMAINS)})$"
    return re.match(pattern, email)

# Step 1: User enters email
if "is_authenticated" not in st.session_state:
    st.session_state["is_authenticated"] = False

if not st.session_state["is_authenticated"]:
    st.title("🏟️ AFC Venue - MBM Hospitality")
    st.markdown("""
    **Welcome to the Venue Hospitality Dashboard!**  
    This app provides insights into MBM Sales Performance and User Metrics. 

    **MBM Sales Performance**:  
    Analyse sales from MBM hospitality. 

    **Premium Exec Metrics**:  
    View and evaluate performance metrics from the Premium Team.
    """)

    # Ask for email
    email = st.text_input("Enter your work email address")
    if st.button("Send Access Code"):
        # Validate email
        if is_valid_email(email):  # Check if email matches allowed domains
            # Generate token
            token = serializer.dumps(email)  # Create a secure token
            try:
                send_email(email, token)
                st.success(f"Access code sent to {email}. Check your inbox!")
                st.session_state["email"] = email
            except Exception as e:
                st.error("Failed to send email. Please check your email configuration.")
                st.error(str(e))
        else:
            st.error("Invalid email address. Only @arsenal.co.uk and @con.arsenal.co.uk are allowed.")

    # Step 2: User enters the code
    if "email" in st.session_state:
        code = st.text_input("Enter the access code sent to your email")
        if st.button("Verify Code"):
            try:
                # Validate token
                email_from_token = serializer.loads(code, max_age=300)  # Token valid for 5 minutes
                if email_from_token == st.session_state["email"]:
                    st.session_state["is_authenticated"] = True
                    st.session_state["app_choice"] = "📊 Sales Performance"  # Default page
                    st.success("Access granted!")
                    st.rerun()  # Redirect immediately after login
                else:
                    st.error("Invalid access code.")
            except Exception as e:
                st.error("Invalid or expired access code.")

# Step 3: Show the app after authentication
if st.session_state["is_authenticated"]:
    # Sidebar navigation
    st.sidebar.title("🧭 Navigation")
    app_choice = st.sidebar.radio(
        "Go to",
        ["📊 Sales Performance", "📈 User Performance", "🔓 Sign Out"],
        index=0 if "app_choice" not in st.session_state else
        ["📊 Sales Performance", "📈 User Performance", "🔓 Sign Out"].index(st.session_state["app_choice"])
    )

    # Save the selected app choice
    st.session_state["app_choice"] = app_choice

    # Handle page navigation
    if app_choice == "📊 Sales Performance":
        sales_performance.run_app()  # Pulls and renders Sales Performance data

    elif app_choice == "📈 User Performance":
        user_performance_api.run_app()  # Pulls and renders User Performance data

    elif app_choice == "🔓 Sign Out":
        # Clear session state and redirect to login page
        st.session_state.clear()
        st.rerun()














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
        
        


# import streamlit as st
# import logging
# import user_performance_api
# import sales_performance
# from msal_streamlit_authentication import msal_authentication

# # Configure logging
# logging.basicConfig(
#     format="%(asctime)s - %(levelname)s - %(message)s",
#     level=logging.DEBUG,
#     handlers=[
#         logging.StreamHandler()
#     ]
# )

# logging.debug("Starting the Streamlit app.")

# # Initialize session state
# if "login_token" not in st.session_state:
#     st.session_state["login_token"] = None
#     logging.debug("Initialized session state for login_token.")

# # Define MSAL configuration
# msal_config = {
#     "auth": {
#         "clientId": "9c350612-9d05-40f3-94e9-d348d92f446a",
#         "authority": "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021",
#         "redirectUri": "https://afc-apps-hospitality.streamlit.app",
#         "postLogoutRedirectUri": "https://afc-apps-hospitality.streamlit.app"
#     },
#     "cache": {
#         "cacheLocation": "sessionStorage",
#         "storeAuthStateInCookie": False
#     }
# }

# # Define login request parameters
# login_request = {
#     "scopes": ["User.Read"]
# }

# # Render MSAL authentication
# if not st.session_state["login_token"]:
#     try:
#         logging.debug("Rendering msal_authentication login/logout buttons...")
#         login_token = msal_authentication(
#             auth=msal_config['auth'],
#             cache=msal_config['cache'],
#             login_request=login_request,
#             logout_request={},
#             login_button_text="🔐 Login",
#             logout_button_text="🔓 Logout",
#             key="unique_msal_key"
#         )
#         logging.debug(f"Login Token Retrieved: {login_token}")
#         st.session_state["login_token"] = login_token
#     except Exception as e:
#         logging.error(f"Error during authentication initialization: {e}")
#         st.error("An error occurred during authentication.")
# else:
#     login_token = st.session_state["login_token"]

# # Check auth
# if login_token:
#     logging.info("User is authenticated.")
#     st.sidebar.title("🧭 Navigation")
    
#     # Debugging navigation choices
#     app_choice = st.sidebar.radio("Go to", ["📊 Sales Performance", "📈 User Performance"])
#     logging.debug(f"Navigation Choice: {app_choice}")

#     if app_choice == "📊 Sales Performance":
#         logging.info("Navigating to Sales Performance.")
#         try:
#             sales_performance.run_app()
#         except Exception as e:
#             logging.error(f"Error in Sales Performance App: {e}")
#             st.error("An error occurred in the Sales Performance section.")
#     elif app_choice == "📈 User Performance":
#         logging.info("Navigating to User Performance.")
#         try:
#             user_performance_api.run_app()
#         except Exception as e:
#             logging.error(f"Error in User Performance App: {e}")
#             st.error("An error occurred in the User Performance section.")
# else:
#     logging.warning("User not authenticated. Displaying login prompt.")
#     st.title("🏟️ AFC Venue - MBM Hospitality")

#     # Description of the app
#     st.markdown("""
#     **Welcome to the Venue Hospitality Dashboard!**  
#     This app provides insights into MBM Sales Performance and User Metrics. 

#     **MBM Sales Performance**:  
#     Analyse sales from MBM hospitality. 

#     **Premium Exec Metrics**:  
#     View and evaluate performance metrics from the Premium Team.

#     **Note:** Please log in using AFC credentials to access the app.
#     """)
#     logging.debug("Login prompt displayed.")


# import streamlit as st
# from itsdangerous import URLSafeTimedSerializer
# import smtplib
# from email.message import EmailMessage
# import os
# from dotenv import load_dotenv
# import sales_performance
# import user_performance_api

# # Load environment variables
# load_dotenv()

# # Configuration
# SECRET_KEY = os.getenv("SECRET_KEY")
# EMAIL_SENDER = os.getenv("EMAIL_SENDER")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = int(os.getenv("SMTP_PORT"))
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
#         smtp.starttls()
#         smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
#         smtp.send_message(msg)

# # Function to validate email domain
# def is_valid_email(email):
#     import re
#     pattern = rf"^.+@({'|'.join(ALLOWED_DOMAINS)})$"
#     return re.match(pattern, email)

# # Initialize session state variables
# if "state" not in st.session_state:
#     st.session_state["state"] = "email_input"  # Possible states: "email_input", "code_input", "authenticated"
# if "email" not in st.session_state:
#     st.session_state["email"] = None

# # Debugging: Current state
# # st.write(f"Debug: Current State -> {st.session_state['state']}")

# # App States
# if st.session_state["state"] == "email_input":
#     # Email Input State
#     st.title("🏟️ AFC Venue - MBM Hospitality")
#     email = st.text_input("Enter your work email address", key="email_input_widget")
#     if st.button("Send Access Code", key="send_code_button_widget"):
#         if is_valid_email(email):
#             try:
#                 token = serializer.dumps(email)
#                 send_email(email, token)
#                 st.session_state["email"] = email
#                 st.session_state["state"] = "code_input"
#                 st.success(f"Access code sent to {email}. Check your inbox!")
#                 st.experimental_rerun()
#             except Exception as e:
#                 st.error("Failed to send email. Please check your email configuration.")
#                 st.error(str(e))
#         else:
#             st.error("Invalid email address. Only @arsenal.co.uk and @con.arsenal.co.uk are allowed.")

# elif st.session_state["state"] == "code_input":
#     # Code Input State
#     st.title("🏟️ AFC Venue - MBM Hospitality")
#     code = st.text_input("Enter the access code sent to your email", key="code_input_widget")
#     if st.button("Verify Code", key="verify_code_button_widget"):
#         try:
#             email_from_token = serializer.loads(code, max_age=300)  # Token valid for 5 minutes
#             if email_from_token == st.session_state["email"]:
#                 st.session_state["state"] = "authenticated"
#                 st.success("Access granted!")
#                 st.experimental_rerun()
#             else:
#                 st.error("Invalid access code.")
#         except Exception as e:
#             st.error("Invalid or expired access code.")

# elif st.session_state["state"] == "authenticated":
#     # Authenticated State
#     st.sidebar.title("🧭 Navigation")
#     app_choice = st.sidebar.radio(
#         "Go to",
#         ["📊 Sales Performance", "📈 User Performance", "🔓 Sign Out"],
#         key="navigation_radio_widget"
#     )

#     if app_choice == "📊 Sales Performance":
#         sales_performance.run_app()
#     elif app_choice == "📈 User Performance":
#         user_performance_api.run_app()
#     elif app_choice == "🔓 Sign Out":
#         st.session_state.clear()
#         st.session_state["state"] = "email_input"
        


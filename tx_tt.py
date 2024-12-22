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




import pandas as pd

# Define file paths
file_path = '/Users/cmunthali/Documents/PYTHON/APPS/sql_tx_tt.xlsx'
file_path_1 = '/Users/cmunthali/Documents/PYTHON/APPS/HOSPITALITY TICKET RELEASES SEASON 24-25.xlsx'
output_file = '/Users/cmunthali/Documents/PYTHON/APPS/updated_data2.xlsx'

# Load data
tx_sales_data = pd.read_excel(file_path, sheet_name="TX Sales Data")
seat_list = pd.read_excel(file_path, sheet_name="Seat List")
game_category = pd.read_excel(file_path, sheet_name="Game Category")

# Load all tabs from file_path_1
try:
    ticket_releases_sheets = pd.read_excel(file_path_1, sheet_name=None)  # Load all sheets as a dictionary
    ticket_releases = pd.concat(ticket_releases_sheets.values(), ignore_index=True)  # Combine all sheets
    if ticket_releases.empty:
        print("File_Path_1 (HOSPITALITY TICKET RELEASES SEASON 24-25.xlsx) is empty.")
except Exception as e:
    print(f"Error loading file_path_1: {e}")
    ticket_releases = None

# Normalize column names
tx_sales_data.columns = tx_sales_data.columns.str.strip().str.replace(" ", "_").str.lower()
seat_list.columns = seat_list.columns.str.strip().str.replace(" ", "_").str.lower()
game_category.columns = game_category.columns.str.strip().str.replace(" ", "_").str.lower()
if ticket_releases is not None:
    ticket_releases.columns = ticket_releases.columns.str.strip().str.replace(" ", "_").str.lower()

# Adjust block formatting in ticket releases and seat list
def adjust_block(block):
    if isinstance(block, str) and block.startswith("C") and block[1:].isdigit():
        block_number = int(block[1:])  # Remove leading zeros
        return f"{block_number} Club level"  # Normalize casing
    elif isinstance(block, str) and block.isdigit():
        block_number = int(block)
        return f"{block_number} Club level"
    return block

if ticket_releases is not None:
    ticket_releases["block"] = ticket_releases["block"].apply(adjust_block)
seat_list["block"] = seat_list["block"].apply(adjust_block)

# Strip whitespace in all string columns
tx_sales_data = tx_sales_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)
seat_list = seat_list.applymap(lambda x: x.strip() if isinstance(x, str) else x)
game_category = game_category.applymap(lambda x: x.strip() if isinstance(x, str) else x)
if ticket_releases is not None:
    ticket_releases = ticket_releases.applymap(lambda x: x.strip() if isinstance(x, str) else x)

# Ensure numeric columns are properly typed
game_category["seat_value"] = pd.to_numeric(game_category["seat_value"], errors="coerce")
tx_sales_data["ticket_sold_price"] = pd.to_numeric(tx_sales_data["ticket_sold_price"], errors="coerce")

# Matched and Metrics Data for TX Sales Data
matched_data = []
metrics_data = []
missing_matches = []

# Match and update data for TX Sales Data
for index, row in tx_sales_data.iterrows():
    matched_yn = "N"
    matching_seat = seat_list[
        (seat_list["block"] == row["block"]) &
        (seat_list["row"] == row["row"]) &
        (seat_list["seat"] == row["seat"])
    ]
    if not matching_seat.empty:
        row["crc_desc"] = matching_seat["crc_desc"].values[0]
        row["price_band"] = matching_seat["price_band"].values[0]
        matching_game = game_category[
            (game_category["game_name"] == row["game_name"]) &
            (game_category["game_date"] == row["game_date"]) &
            (game_category["price_band"] == matching_seat["price_band"].values[0])
        ]
        if not matching_game.empty:
            matched_yn = "Y"
            row["category"] = matching_game["category"].values[0]
            row["seat_value"] = matching_game["seat_value"].values[0]
            row["value_generated"] = row["ticket_sold_price"] - matching_game["seat_value"].values[0]
            metrics_data.append({
                "game_name": row["game_name"],
                "category": matching_game["category"].values[0],
                "price_band": row["price_band"],
                "crc_desc": row["crc_desc"],
                "transfer_type": row["transfer_type"],
                "ticket_sold_price": row["ticket_sold_price"],
                "seat_value": matching_game["seat_value"].values[0],
                "value_generated": row["value_generated"]
            })
    else:
        missing_matches.append(row.to_dict())
    row["matched_yn"] = matched_yn
    matched_data.append(row)

# Process Ticket Releases with the same logic
release_data = []
if ticket_releases is not None:
    for index, row in ticket_releases.iterrows():
        matched_yn = "N"
        sales_match = tx_sales_data[
            (tx_sales_data["game_name"] == row["game_name"]) &
            (tx_sales_data["block"] == row["block"]) &
            (tx_sales_data["row"] == row["row"]) &
            (tx_sales_data["seat"] == row["seat"])
        ]
        if not sales_match.empty:
            matched_yn = "Y"
            row["ticket_sold_price"] = sales_match["ticket_sold_price"].values[0]
        else:
            row["ticket_sold_price"] = None
        row_dict = row.to_dict()
        row_dict["matched_yn"] = matched_yn
        release_data.append(row_dict)

# Convert matched data, metrics data, unmatched rows, and release data to DataFrames
matched_df = pd.DataFrame(matched_data)
metrics_df = pd.DataFrame(metrics_data)
release_df = pd.DataFrame(release_data)
missing_matches_df = pd.DataFrame(missing_matches)

# Save results to Excel
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    tx_sales_data.to_excel(writer, sheet_name="All Data", index=False)
    matched_df.to_excel(writer, sheet_name="Matched Data", index=False)
    metrics_df.to_excel(writer, sheet_name="Detailed Metrics", index=False)
    release_df.to_excel(writer, sheet_name="From Hosp", index=False)
    missing_matches_df.to_excel(writer, sheet_name="Missing Matches", index=False)

print(f"Updated data saved to {output_file}")













# import streamlit as st
# from msal import ConfidentialClientApplication
# from dotenv import load_dotenv
# import os
# import sales_performance
# import user_performance_api

# # Load environment variables
# load_dotenv()

# # Azure AD Configuration
# CLIENT_ID = os.getenv("CLIENT_ID")
# TENANT_ID = os.getenv("TENANT_ID")
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# REDIRECT_URI = os.getenv("REDIRECT_URI")
# AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
# SCOPES = ["User.Read"]

# # MSAL Confidential Client Application
# app = ConfidentialClientApplication(
#     client_id=CLIENT_ID,
#     client_credential=CLIENT_SECRET,
#     authority=AUTHORITY
# )

# # Initialize session states
# if "authenticated" not in st.session_state:
#     st.session_state["authenticated"] = False
# if "access_token" not in st.session_state:
#     st.session_state["access_token"] = None
# if "redirected" not in st.session_state:
#     st.session_state["redirected"] = False
# if "data_refreshed" not in st.session_state:
#     st.session_state["data_refreshed"] = False

# # Azure AD Login URL
# def azure_ad_login():
#     return app.get_authorization_request_url(scopes=SCOPES, redirect_uri=REDIRECT_URI)

# # App Header with a logo
# st.image("assets/arsenal-logo.png", width=250)  # Placeholder for the logo
# st.title("🏟️ AFC Venue - MBM Hospitality")
# st.markdown("---")  # A horizontal line for better UI

# if not st.session_state["authenticated"]:
#     # Instructions for SSO Login
#     st.markdown("""
#     ### 👋 Welcome to the Venue Hospitality App!  
#     **Please log in using AFC credentials to access the following modules:**

#     - **📊 Sales Performance**: Analyze and track sales data.
#     - **📈 User Performance**: Monitor and evaluate team performance metrics.
    
#     If you experience login issues, please contact [cmunthali@arsenal.co.uk](mailto:cmunthali@arsenal.co.uk).
#     """)

#     # Login Section
#     login_url = azure_ad_login()
#     st.markdown(f"""
#         <div style="text-align:center;">
#             <a href="{azure_ad_login()}" target="_blank" style="
#                 text-decoration:none;
#                 color:white;
#                 background-color:#FF4B4B;
#                 padding:10px 20px;
#                 border-radius:5px;
#                 font-size:16px;">
#                 🔐 Log in Microsoft Entra ID
#             </a>
#         </div>
#     """, unsafe_allow_html=True)

#     # Process login
#     query_params = st.experimental_get_query_params()
#     if "code" in query_params and not st.session_state["redirected"]:
#         auth_code = query_params["code"][0]
#         with st.spinner("🔄 Logging you in..."):
#             try:
#                 result = app.acquire_token_by_authorization_code(
#                     code=auth_code,
#                     scopes=SCOPES,
#                     redirect_uri=REDIRECT_URI
#                 )
#                 if "access_token" in result:
#                     st.session_state["access_token"] = result["access_token"]
#                     st.session_state["authenticated"] = True
#                     st.session_state["redirected"] = True
#                     st.success("🎉 Login successful! Redirecting...")
#                     st.rerun()  # Reload the app to show authenticated view
#                 else:
#                     st.error("❌ Failed to log in. Please try again.")
#             except Exception as e:
#                 st.error(f"❌ An error occurred: {str(e)}")
# else:
#     # User Profile Card
#     st.sidebar.markdown("### 👤 Logged in User")
#     st.sidebar.info("User: **Azure AD User**\nRole: **Premium Exec**")
    
#     # Navigation Sidebar
#     st.sidebar.title("🧭 Navigation")
#     app_choice = st.sidebar.radio(
#         "Choose Module",
#         ["📊 Sales Performance", "📈 User Performance"],
#         format_func=lambda x: x.split(" ")[1],  # Display just the module names
#     )
    
#     # Refresh Button
#     if st.sidebar.button("🔄 Refresh Data"):
#         with st.spinner("🔄 Fetching the latest data..."):
#             try:
#                 # Simulate fetching data from APIs
#                 if app_choice == "📊 Sales Performance":
#                     sales_performance.run_app()
#                 elif app_choice == "📈 User Performance":
#                     user_performance_api.run_app()
#                 st.session_state["data_refreshed"] = True
#                 st.success("✅ Data refreshed successfully!")
#             except Exception as e:
#                 st.error(f"❌ Failed to refresh data: {str(e)}")
    
#     # Add Loading Indicator
#     with st.spinner("🔄 Loading..."):
#         if app_choice == "📊 Sales Performance":
#             sales_performance.run_app()
#         elif app_choice == "📈 User Performance":
#             user_performance_api.run_app()

#     # Logout Button
#     st.sidebar.markdown("---")
#     if st.sidebar.button("🔓 Logout"):
#         with st.spinner("🔄 Logging out..."):
#             # Clear session state
#             st.session_state["authenticated"] = False
#             st.session_state["access_token"] = None
#             st.session_state.clear()  # Clears all session state values
#             st.success("✅ You have been logged out successfully!")
            
#             # Redirect to the login screen
#             st.experimental_set_query_params()  # Clears query params to prevent re-login issues
#             st.rerun()

# # Footer Section
# st.markdown("---")
# st.markdown("""
#     <div style="text-align:center; font-size:12px; color:gray;">
#         🏟️ **Arsenal Property** | All Rights Reserved © 2024  
#         Need help? Contact [cmunthali@arsenal.co.uk]
#     </div>
# """, unsafe_allow_html=True)
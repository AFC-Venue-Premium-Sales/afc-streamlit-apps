from flask import Flask, redirect, url_for, session, request
from msal import ConfidentialClientApplication

# Flask App Configuration
app = Flask(__name__)
app.secret_key = "a-very-secure-random-key"  # Replace with a secure random key

# Azure AD Configuration
CLIENT_ID = "9c350612-9d05-40f3-94e9-d348d92f446a"  # Replace with your Azure AD client ID
TENANT_ID = "068cb91a-8be0-49d7-be3a-38190b0ba021"  # Replace with your Azure AD tenant ID
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"  # Azure AD Authority
REDIRECT_URI = "https://afc-apps-hospitality.streamlit.app/callback"  # Replace with your redirect URI
SCOPE = ["User.Read"]  # Scope for Microsoft Graph API

# MSAL Client
msal_client = ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
)

@app.route("/")
def index():
    # Check if user is authenticated
    if "access_token" in session:
        user_info = session["user"]
        return f"Hello, {user_info['name']}! Your email: {user_info['preferred_username']}"
    else:
        # Redirect to Azure AD login
        return redirect(url_for("login"))

@app.route("/login")
def login():
    # Generate the Azure AD login URL
    auth_url = msal_client.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    # Handle the redirect from Azure AD and acquire a token
    code = request.args.get("code")
    if code:
        result = msal_client.acquire_token_by_authorization_code(
            code,
            scopes=SCOPE,
            redirect_uri=REDIRECT_URI
        )
        if "access_token" in result:
            # Store the access token and user info in session
            session["access_token"] = result["access_token"]
            session["user"] = result.get("id_token_claims", {})
            return redirect(url_for("index"))
        else:
            return f"Authentication failed: {result.get('error_description')}", 400
    return "Missing authorization code", 400

@app.route("/logout")
def logout():
    # Clear the session and redirect to Azure AD logout
    session.clear()
    logout_url = f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri=https://afc-apps-hospitality.streamlit.app"
    return redirect(logout_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context=("cert.pem", "key.pem"))

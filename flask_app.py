from flask import Flask, redirect, url_for
from identity.flask import IdentityWeb

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "a-very-secure-random-key"  # Replace with a strong, random key

# Azure AD Configuration
app.config["IDENTITY_CLIENT_ID"] = "9c350612-9d05-40f3-94e9-d348d92f446a"  # Your Azure AD client ID
app.config["IDENTITY_TENANT_ID"] = "068cb91a-8be0-49d7-be3a-38190b0ba021"  # Your Azure AD tenant ID
app.config["IDENTITY_REDIRECT_PATH"] = "https://afc-apps-hospitality.streamlit.app/callback"  # Redirect path after login
app.config["IDENTITY_SCOPES"] = ["User.Read"]  # Permission scope
app.config["IDENTITY_AUTHORITY"] = f"https://login.microsoftonline.com/{app.config['IDENTITY_TENANT_ID']}"

# Initialize IdentityWeb
identity = IdentityWeb(app)

# Routes
@app.route("/")
def index():
    # Check if the user is authenticated
    user = identity.get_user()
    if user:
        return f"Hello, {user.get('name')}! Your email: {user.get('preferred_username')}"
    else:
        return identity.login_redirect()  # Redirect to Azure AD login

@app.route("/logout")
def logout():
    # Log the user out and clear the session
    return identity.logout()

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context=("cert.pem", "key.pem"))

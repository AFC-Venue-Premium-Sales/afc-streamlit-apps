import streamlit as st
from saml2 import BINDING_HTTP_POST
from saml2.response import AuthnResponse
from saml_config import get_saml_config
from saml2.client import Saml2Client

def create_saml_client():
    """Create a SAML2 client using the configuration."""
    config = get_saml_config()
    return Saml2Client(config)

def parse_saml_response(saml_response):
    """Parse and validate the SAML response."""
    saml_client = create_saml_client()
    response = saml_client.parse_authn_request_response(
        saml_response,
        BINDING_HTTP_POST,
    )
    return response.get_identity()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False 

if not st.session_state["authenticated"]:
    st.title("🏟️ AFC Venue - MBM Hospitality")

    # SAML Login Link
    login_url = get_saml_config()["idp"]["singleSignOnService"]["url"]
    st.markdown(f"[Click here to login with SAML]({login_url})")

    # Handle SAML response
    saml_response = st.experimental_get_query_params().get("SAMLResponse")
    if saml_response:
        user_info = parse_saml_response(saml_response)
        if user_info:
            st.session_state["authenticated"] = True
            st.session_state["user_info"] = user_info
            st.success(f"🎉 Login successful! Welcome {user_info['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'][0]}.")
else:
    st.sidebar.title("🧭 Navigation")
    st.sidebar.write(f"Logged in as {st.session_state['user_info']['http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'][0]}")

    if st.sidebar.button("🔓 Logout"):
        st.session_state["authenticated"] = False
        st.experimental_rerun()

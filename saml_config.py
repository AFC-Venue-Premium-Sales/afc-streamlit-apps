import os

def get_saml_config():
    """Generate the SAML configuration."""
    return {
        # Required SAML settings
        "strict": True,
        "debug": True,
        "sp": {
            "entityId": "https://afc-apps-hospitality.streamlit.app",
            "assertionConsumerService": {
                "url": "https://afc-apps-hospitality.streamlit.app",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": {
            "entityId": "https://sts.windows.net/068cb91a-8be0-49d7-be3a-38190b0ba021/",
            "singleSignOnService": {
                "url": "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021/saml2",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": "MIIC8DCCAdigAwIBAgIQHN0vcluvILZJUTuxnTTIujANBgkqhkiG9w0BAQsFADA0MTIwMAYDVQQDEylNaWNyb3NvZnQgQXp1cmUgRmVkZXJhdGVkIFNTTyBDZXJ0aWZpY2F0ZTAeFw0yNDExMjAxMTQ0NDVaFw0yNzExMjAxMTQ0NDVaMDQxMjAwBgNVBAMTKU1pY3Jvc29mdCBBenVyZSBGZWRlcmF0ZWQgU1NPIENlcnRpZmljYXRlMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1Ebt2O11eNicWX1rDIhLwEp9Y3kyHLSHNmhYex6yApp94Uq6y",
        
        },
    }


import hashlib
import base64

code_verifier = "_rRWqgkPskJNgAYR4-U4LbDnx-PYGOGa0sBkIowL8ao5_OuKgIwvxFSP5Oss1QqJYShsh61iqLd1Jsf4W1dGSA"
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode("utf-8")).digest()
).decode("utf-8").rstrip("=")

print(f"Expected code_challenge: {code_challenge}")

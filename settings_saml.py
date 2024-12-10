import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "entity_id": "https://afc-apps-hospitality.streamlit.app",
    "idp_metadata_url": "https://login.microsoftonline.com/068cb91a-8be0-49d7-be3a-38190b0ba021/federationmetadata/2007-06/federationmetadata.xml?appid=9c350612-9d05-40f3-94e9-d348d92f446a",
    "private_key_file": os.path.join(BASE_DIR, "private.key"),
    "certificate_file": os.path.join(BASE_DIR, "public.cert"),
    "acs_url": "https://afc-apps-hospitality.streamlit.app/sso/acs/",
    "logout_url": "https://afc-apps-hospitality.streamlit.app/sso/logout/",
}

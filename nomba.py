import streamlit as st

import requests

import time # NEW: Import the time module
 
# --- Configuration: Load ALL credentials ---

try:

    ACCOUNT_ID = st.secrets["NOMBA_ACCOUNT_ID"]

    CLIENT_ID = st.secrets["NOMBA_CLIENT_ID"]

    CLIENT_SECRET = st.secrets["NOMBA_CLIENT_SECRET"]

except (FileNotFoundError, KeyError) as e:

    st.error(f"Nomba API credentials not found in secrets.toml: {e}")

    ACCOUNT_ID, CLIENT_ID, CLIENT_SECRET = None, None, None
 
BASE_URL = "https://api.nomba.com"
 
 
# --- NEW FUNCTION: To get and cache the access token ---

def get_access_token():

    """

    Fetches a Nomba access token. Caches it in the session state to avoid

    requesting a new token on every API call.

    """

    # Check if a valid token already exists in the session state

    current_time = time.time()

    if 'access_token' in st.session_state and st.session_state.get('token_expiry_time', 0) > current_time:

        return st.session_state.access_token
 
    # If no valid token, fetch a new one

    url = f"{BASE_URL}/v1/auth/token/issue"

    payload = {

        "grant_type": "client_credentials",

        "client_id": CLIENT_ID,

        "client_secret": CLIENT_SECRET

    }

    headers = {

        "accountId": ACCOUNT_ID,

        "Content-Type": "application/json"

    }
 
    try:

        response = requests.post(url, json=payload, headers=headers)

        response.raise_for_status()

        token_data = response.json()

        if token_data.get("code") == "00":

            data = token_data.get("data", {})

            access_token = data.get("access_token")

            expires_in = data.get("expires_in", 3600)  # Default to 1 hour

            # Cache the new token and its expiry time

            st.session_state.access_token = access_token

            # Add a 60-second buffer to be safe

            st.session_state.token_expiry_time = current_time + expires_in - 60

            return access_token

        else:

            st.error(f"Failed to get access token: {token_data.get('message')}")

            return None

    except requests.exceptions.RequestException as e:

        st.error(f"Error fetching access token: {e}")

        return None
 
 
# --- UPDATED: create_checkout_order function ---

def create_checkout_order(email: str, amount: float, order_id: str, callback_url: str):

    """ Calls the Nomba Checkout API using a temporary access token. """

    access_token = get_access_token()

    if not access_token:

        return None # Stop if we failed to get a token
 
    url = f"{BASE_URL}/v1/checkout/order"

    # UPDATED: The Authorization header now uses the access token

    headers = {

        "accountId": ACCOUNT_ID,

        "Authorization": f"Bearer {access_token}",

        "Content-Type": "application/json"

    }

    amount_str = f"{amount:.2f}"

    payload = {

        "order": { "orderReference": order_id, "customerId": email, "callbackUrl": callback_url, "customerEmail": email, "amount": amount_str, "currency": "NGN", "accountId": ACCOUNT_ID },

        "tokenizeCard": False

    }

    try:

        response = requests.post(url, json=payload, headers=headers)

        response.raise_for_status()

        response_data = response.json()

        if response_data.get("code") == "00":

            data = response_data.get("data", {})

            return {"checkout_url": data.get("checkoutUrl"), "session_id": data.get("sessionId")}

        else:

            st.error(f"Nomba API Error: {response_data.get('message')}")

            return None

    except requests.exceptions.RequestException as e:

        st.error(f"An API error occurred: {e}")

        return None
 
 
# --- UPDATED: verify_checkout_payment function ---

def verify_checkout_payment(session_id: str):

    """ Verifies a transaction using a temporary access token. """

    access_token = get_access_token()

    if not access_token:

        return None # Stop if we failed to get a token
 
    url = f"{BASE_URL}/v1/transactions/requery/{session_id}"

    # UPDATED: The Authorization header now uses the access token

    headers = {

        "accountId": ACCOUNT_ID,

        "Authorization": f"Bearer {access_token}"

    }

    try:

        response = requests.get(url, headers=headers)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:

        st.error(f"An API verification error occurred: {e}")

        return None
 
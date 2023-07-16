from flask import Flask, redirect, url_for, session, request, Blueprint
import requests
import urllib
import base64

sub_bp = Blueprint('sub_bp', __name__)

#app = Flask(__name__)

# Your PayPal client ID and secret
CLIENT_ID = 'AUCRss-hSy_tA4sIPHAQWKfVCu8Rli4iXp7ZuJr1zM6-LV_K7P8JDYceFdFKzKxlebfGYUt5wsneAacM'
CLIENT_ID = 'ARrGmqddP3qjq37oewgzXU7Wch4VRR_9wLdnxz78Rv4aBavdMta8l-ZT0zvzYiUKKHaHxc7iT38CbL5E'
CLIENT_SECRET = 'EPAQz2BVSdYJ_fKL9l1_LSUHWLeATDVG44EIKONdiGeu-9qooszk3Bx13CjYg-DSfJqT04wkSTVHDEQ2'
CLIENT_SECRET = 'ELfEAtyGtloEOBhqgWvIPYZRuTZMxAz0pKEzKdKJoi_OTXaHVkpE3TjqToBzQ5UZZzebYQjYNwpijD2z'


# Replace these with your actual sandbox credentials
SANDBOX_CLIENT_ID = 'your_sandbox_client_id'
SANDBOX_CLIENT_SECRET = 'your_sandbox_client_secret'

SANDBOX_PAYPAL_TOKEN_URL = 'https://api.sandbox.paypal.com/v1/oauth2/token'

@sub_bp.route('/paypal_callback')
def paypal_callback():
    # Get the authorization code from the query parameters
    code = request.args.get('code')

    # Prepare the data for token exchange
    data = {
        'code': code,
        'client_id': SANDBOX_CLIENT_ID,
        'client_secret': SANDBOX_CLIENT_SECRET,
        'redirect_uri': url_for('sub_bp.paypal_callback', _external=True),
        'grant_type': 'authorization_code',
    }

    # Add basic authentication to the request headers
    auth_string = f"{SANDBOX_CLIENT_ID}:{SANDBOX_CLIENT_SECRET}"
    base64_auth_string = base64.b64encode(auth_string.encode()).decode()
    headers = {
        "Authorization": f"Basic {base64_auth_string}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Perform the token exchange request to the sandbox environment
    response = requests.post(SANDBOX_PAYPAL_TOKEN_URL, data=data, headers=headers)
    print(response.json())
    # Check if the token exchange was successful
    if response.status_code == 200:
        access_token = response.json().get('access_token')

        # Store the access token in the session or database for future use
        session['paypal_access_token'] = access_token

        # You can now use the access token to make API requests to create payment requests and handle payments
        # For example, you can use the PayPal API to create payment requests, process payments, and handle webhooks

        return redirect(url_for('user_account'))
    else:
        # Handle the error response if the token exchange failed
        error_description = response.json().get('error_description', 'Unknown error')
        return f"Error: {error_description}"

@sub_bp.route('/paypal_auth')
def paypal_auth():
    # Redirect users to PayPal for authentication
    paypal_auth_url = 'https://www.paypal.com/oauth2/authorize'
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': url_for('sub_bp.paypal_callback', _external=True),
        'scope': 'openid',
    }
    return redirect(f'{paypal_auth_url}?{urllib.parse.urlencode(params)}')

'''
@sub_bp.route('/paypal_callback')
def paypal_callback():
    # Exchange the authorization code for an access token
    code = request.args.get('code')
    paypal_token_url = 'https://api.paypal.com/v1/oauth2/token'
    paypal_token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    data = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': url_for('sub_bp.paypal_callback', _external=True),
        'grant_type': 'authorization_code',
    }
    response = requests.post(paypal_token_url, data=data)
    access_token = response.json().get('access_token')
    print(response.json())

    # Store the access token in the session or database for future use
    session['paypal_access_token'] = access_token

    # You can now use the access token to make API requests to create payment requests and handle payments
    # For example, you can use the PayPal API to create payment requests, process payments, and handle webhooks

    #return redirect(url_for('user_account'))
    return redirect(url_for('pokemon_login'))
'''
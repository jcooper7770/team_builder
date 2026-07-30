from flask import Flask, request, jsonify, send_from_directory,\
    render_template, Blueprint, redirect, url_for, session
import requests
import base64
import os

from application.pokemon.team_building import PokemonUser

paypal_bp = Blueprint('paypal', __name__)


PAYPAL_CLIENT_ID ="Ad6FHlfOgLeEbxQHlN7sKw_N6BsbZuE5CB-9HjYfwlc-7YYZluJBnQBi-GQ7wdTuvt3j3dRBvIWl5_n-"
PAYPAL_CLIENT_SECRET = "EAOQcucVL0FaXCSEVj17K4POC0nuE1FfGChH5bfh8MYSdCdA73ClryiKPGsasPVZeWRfqfwUQOIJZaM-"
PLAN_ID = os.getenv("PLAN_ID")
PORT = int(os.getenv("PORT", 8888))
BASE_URL = "https://api-m.sandbox.paypal.com"
from flask import Flask, request, jsonify, send_from_directory
import requests
import base64
import os


# Serve static files
@paypal_bp.route('/client/<path:filename>')
def serve_static(filename):
    return send_from_directory('client', filename)

# Parse JSON in request body
@paypal_bp.before_request
def parse_json():
    if request.is_json:
        request.json_data = request.get_json()

# Generate OAuth 2.0 access token
def generate_access_token():
    try:
        if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
            raise ValueError("MISSING_API_CREDENTIALS")

        auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
        response = requests.post(f"{BASE_URL}/v1/oauth2/token",
                                 data={"grant_type": "client_credentials"},
                                 headers={"Authorization": f"Basic {auth}"})

        data = response.json()
        return data["access_token"]

    except Exception as error:
        print("Failed to generate Access Token:", error)

# Create an order to start the transaction
def create_order(cart):
    try:
        print("Shopping cart information passed from the frontend create_order() callback:", cart)

        access_token = generate_access_token()
        url = f"{BASE_URL}/v2/checkout/orders"
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": "3.00",
                    },
                },
            ],
        }

        response = requests.post(url,
                                 json=payload,
                                 headers={
                                     "Content-Type": "application/json",
                                     "Authorization": f"Bearer {access_token}",
                                 })

        return handle_response(response)

    except Exception as error:
        print("Failed to create order:", error)

# Capture payment for the created order to complete the transaction
def capture_order(order_id):
    try:
        access_token = generate_access_token()
        url = f"{BASE_URL}/v2/checkout/orders/{order_id}/capture"

        response = requests.post(url,
                                 headers={
                                     "Content-Type": "application/json",
                                     "Authorization": f"Bearer {access_token}",
                                 })

        return handle_response(response)

    except Exception as error:
        print("Failed to capture order:", error)

def handle_response(response):
    print(f"Handling response: {response}")
    try:
        response_json = response.json()
        return {"json_response": response_json, "http_status_code": response.status_code}

    except Exception as err:
        error_message = response.text
        print("!!!")
        raise ValueError(error_message)

@paypal_bp.route("/api/orders", methods=["POST"])
def create_order_route():
    try:
        cart = request.json_data.get("cart")
        result = create_order(cart)
        return jsonify(result["json_response"]), result["http_status_code"]

    except Exception as error:
        print("Failed to create order:", error)
        return jsonify({"error": "Failed to create order"}), 500

@paypal_bp.route("/api/orders/<order_id>/capture", methods=["POST"])
def capture_order_route(order_id):
    print(f"Capturing order number: {order_id}")
    try:
        result = capture_order(order_id)
        print(f"result: {result}")
        return jsonify(result["json_response"]), result["http_status_code"]

    except Exception as error:
        print("Failed to capture order:", error)
        return jsonify({"error": "Failed to capture order"}), 500

# Serve index.html
@paypal_bp.route("/paypal")
def serve_index():
    username = session.get('name')
    if not username:
        return redirect(url_for('pokemon.pokemon_login'))
    user = PokemonUser.load(username)
    return render_template(
        "pokemon/paypal2.html",
        user=username,
        subscribed_user=user.subscribed if user else False
    )
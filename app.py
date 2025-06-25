from flask import Flask, request, abort
import requests
import os
import json
import ipaddress

app = Flask(__name__)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
EXPECTED_ADDRESS = os.getenv("EXPECTED_ADDRESS")
ORDERS_FILE = "orders.json"

# Allowlisted IP ranges for BlockCypher (examples — update if needed)
TRUSTED_IPS = [
    ipaddress.ip_network("34.199.80.0/20"),
    ipaddress.ip_network("54.144.0.0/15"),
    ipaddress.ip_network("52.4.0.0/14")
]


def is_trusted_ip(ip):
    try:
        ip_addr = ipaddress.ip_address(ip)
        return any(ip_addr in net for net in TRUSTED_IPS)
    except ValueError:
        return False


@app.before_request
def restrict_to_trusted_sources():
    if request.method == "POST":
        ip = request.remote_addr
        
def load_orders():
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def find_matching_order(amount):
    orders = load_orders()
    for user_id, order in orders.items():
        expected = order.get("expected_total", 0)
        if abs(amount - expected) < 0.01:
            return user_id, order
    return None, None


@app.route('/ltc-webhook', methods=['POST'])
def ltc_webhook():
    data = request.json

    if not data or 'outputs' not in data or 'hash' not in data or 'confirmations' not in data:
        return "Invalid or incomplete data", 400

    if data['confirmations'] < 1:
        return "Ignored: unconfirmed transaction", 200

    total_satoshis = 0
    matched_address = False

    for output in data['outputs']:
        if EXPECTED_ADDRESS in output.get('addresses', []):
            total_satoshis += output.get('value', 0)
            matched_address = True

    if not matched_address:
        return "Ignored: address mismatch", 200

    ltc_amount = total_satoshis / 1e8
    if ltc_amount <= 0:
        return "Ignored: zero amount", 200

    txid = data.get('hash', 'unknown')
    user_id, order = find_matching_order(ltc_amount)

    if order:
        embed = {
            "title": "✅ Payment Matched",
            "description": f"**User:** <@{user_id}>\n**Product:** {order['product']} x{order['qty']}\n**Total Paid:** {ltc_amount:.6f} LTC\n**TX ID:** `{txid}`",
            "color": 0x2ecc71
        }
    else:
        embed = {
            "title": "⚠️ Unmatched LTC Payment",
            "description": f"**Amount:** {ltc_amount:.6f} LTC\n**TX ID:** `{txid}`\n**Note:** No matching order found.",
            "color": 0xffcc00
        }

    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})

    return "ok", 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)

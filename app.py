
from flask import Flask, request
import requests
import os

app = Flask(__name__)

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
EXPECTED_ADDRESS = "ltc1qd2jtyscqruktvm7tctznsdy3verp26a2uzuv26"

@app.route('/ltc-webhook', methods=['POST'])
def ltc_webhook():
    data = request.json
    total = sum([o['value'] for o in data['outputs']]) / 1e8
    txid = data.get('hash', 'unknown')
    address = data['outputs'][0]['addresses'][0]

    embed = {
        "title": "✅ Litecoin Payment Detected",
        "description": f"**Amount:** {total:.6f} LTC\n**To:** `{address}`\n**TX ID:** `{txid}`",
        "color": 0x2ecc71
    }

    requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
    return "ok", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

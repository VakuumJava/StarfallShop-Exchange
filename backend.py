import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import aiohttp
import uuid

load_dotenv()

app = Flask(__name__)

# CORS configuration for GitHub Pages
CORS(app, origins=[
    "http://127.0.0.1:*",
    "http://localhost:*", 
    "https://*.github.io",
    "https://*.pages.dev",
    "https://*.vercel.app",
    "https://*.netlify.app"
])

# Configuration
WATA_TOKEN = os.getenv("WATA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJQdWJsaWNJZCI6IjNhMTliMmQyLTc0NjUtMTIxMy0zMzYxLTk4YmQyNjNjMGY4MCIsIlRva2VuVmVyc2lvbiI6IjIiLCJleHAiOjE3ODQ4ODYzODIsImlzcyI6Imh0dHBzOi8vYXBpLndhdGEucHJvIiwiYXVkIjoiaHR0cHM6Ly9hcGkud2F0YS5wcm8vYXBpL2gyaCJ9.43odSW6D59Zo4gT9HvZCxxERDS6AlRdaIff0Wpwac28")
SERVICE_WALLET = os.getenv("SERVICE_WALLET", "UQAGUqc7XqO7Wc8tH7QGD8LuituUvdGUVccn-SphINODx7xa")
PORT = int(os.getenv("PORT", 5001))

# Fixed exchange rate
TON_RATE_RUB = float(os.getenv("TON_RATE_RUB", "248.05"))

def to_nano(amount):
    return int(amount * 1e9)

def from_nano(nano):
    return nano / 1e9

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "StarfallShop Exchange API is running",
        "version": "1.0.0",
        "ton_rate": TON_RATE_RUB
    })

@app.route("/ton-price", methods=["GET"])
def ton_price():
    return jsonify({"price": TON_RATE_RUB})

async def create_wata_payment_link(amount, order_id):
    url = "https://api.wata.pro/api/h2h/links"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WATA_TOKEN}"
    }
    payload = {
        "amount": float(f"{amount:.2f}"),
        "currency": "RUB",
        "description": "Обмен RUB на TON - @StarfallShopRobot",
        "orderId": order_id
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"WATA API Error: {response.status} - {text}")
            return await response.json()

@app.route("/create-payment", methods=["POST"])
def create_payment():
    try:
        data = request.json
        rub_amount = float(data["rub_amount"])
        user_address = data["user_address"]
        order_id = str(uuid.uuid4())
        
        # Validate minimum amount
        if rub_amount < 10:
            return jsonify({"error": "Минимальная сумма: 10 RUB"}), 400
        
        # Store payment info
        payments[order_id] = {
            "rub_amount": rub_amount,
            "user_address": user_address,
            "status": "pending",
            "ton_amount": rub_amount / TON_RATE_RUB
        }
        
        link_data = asyncio.run(create_wata_payment_link(rub_amount, order_id))
        return jsonify({
            "url": link_data["url"],
            "id": link_data["id"],
            "order_id": order_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def check_wata_status(payment_id):
    url = f"https://api.wata.pro/api/h2h/links/{payment_id}"
    headers = {
        "Authorization": f"Bearer {WATA_TOKEN}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return False
            data = await response.json()
            return data.get("status", "").lower() == "closed"

async def send_ton_simulation(to_address, amount_nano):
    # Simulated TON sending - replace with actual implementation
    await asyncio.sleep(1)  # Simulate network delay
    return f"Sent {from_nano(amount_nano):.4f} TON to {to_address}"

@app.route("/check-payment", methods=["GET"])
def check_payment():
    try:
        payment_id = request.args.get("id")
        order_id = request.args.get("order_id")
        
        if not order_id or not payment_id:
            return jsonify({"status": "error", "message": "Missing parameters"})
        
        if order_id not in payments:
            return jsonify({"status": "error", "message": "Order not found"})
        
        is_paid = asyncio.run(check_wata_status(payment_id))
        
        if is_paid and payments[order_id]["status"] == "pending":
            order_info = payments[order_id]
            ton_amount = order_info["ton_amount"]
            nano_ton = to_nano(ton_amount)
            
            try:
                tx = asyncio.run(send_ton_simulation(order_info["user_address"], nano_ton))
                payments[order_id]["status"] = "completed"
                payments[order_id]["tx"] = tx
                return jsonify({
                    "status": "completed",
                    "tx": tx,
                    "ton_amount": ton_amount
                })
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})
        elif is_paid:
            return jsonify({"status": "completed"})
        else:
            return jsonify({"status": "pending"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# In-memory storage for payments
payments = {}

if __name__ == "__main__":
    print(f"🚀 StarfallShop Exchange Server запущен на http://0.0.0.0:{PORT}")
    print(f"💰 Курс: 1 TON = {TON_RATE_RUB} RUB")
    app.run(host='0.0.0.0', port=PORT, debug=os.getenv("DEBUG", "False").lower() == "true") 
import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import aiohttp
import uuid
import time

load_dotenv()

app = Flask(__name__)

# CORS configuration for GitHub Pages
CORS(app, origins=[
    "http://127.0.0.1:*",
    "http://localhost:*", 
    "https://vakuumjava.github.io",
    "https://*.github.io",
    "https://*.pages.dev",
    "https://*.vercel.app",
    "https://*.netlify.app"
], methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type', 'Accept'], supports_credentials=False)

# Configuration
WATA_TOKEN = os.getenv("WATA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJQdWJsaWNJZCI6IjNhMTliMmQyLTc0NjUtMTIxMy0zMzYxLTk4YmQyNjNjMGY4MCIsIlRva2VuVmVyc2lvbiI6IjIiLCJleHAiOjE3ODQ4ODYzODIsImlzcyI6Imh0dHBzOi8vYXBpLndhdGEucHJvIiwiYXVkIjoiaHR0cHM6Ly9hcGkud2F0YS5wcm8vYXBpL2gyaCJ9.43odSW6D59Zo4gT9HvZCxxERDS6AlRdaIff0Wpwac28")
SERVICE_WALLET = os.getenv("SERVICE_WALLET", "UQAGUqc7XqO7Wc8tH7QGD8LuituUvdGUVccn-SphINODx7xa")
PORT = int(os.getenv("PORT", 8080))

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
    """Create WATA payment link"""
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
    
    print(f"💳 Creating WATA payment: {amount} RUB, order: {order_id}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"📡 WATA API response: HTTP {response.status}")
                
                if response.status != 200:
                    text = await response.text()
                    print(f"❌ WATA API Error: {response.status} - {text}")
                    raise Exception(f"WATA API Error: {response.status} - {text}")
                
                data = await response.json()
                print(f"✅ WATA payment created: {data.get('id', 'N/A')}")
                return data
                
    except Exception as e:
        print(f"❌ Error creating WATA payment: {e}")
        raise

@app.route("/create-payment", methods=["POST", "OPTIONS"])
def create_payment():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        rub_amount = data.get("rub_amount")
        user_address = data.get("user_address")
        
        print(f"💰 Payment request: {rub_amount} RUB for {user_address}")
        
        if not rub_amount or not user_address:
            print("❌ Missing required fields")
            return jsonify({"error": "rub_amount and user_address required"}), 400
        
        # Validate minimum amount
        if rub_amount < 10:
            print(f"❌ Amount too small: {rub_amount} RUB")
            return jsonify({"error": "Минимальная сумма: 10 RUB"}), 400
        
        # Generate order ID
        order_id = str(uuid.uuid4())
        ton_amount = rub_amount / TON_RATE_RUB
        
        print(f"📊 Exchange: {rub_amount} RUB → {ton_amount:.4f} TON")
        
        # Store payment info
        payments[order_id] = {
            "rub_amount": rub_amount,
            "user_address": user_address,
            "status": "pending",
            "ton_amount": ton_amount,
            "created_at": time.time()
        }
        
        # Create WATA payment
        link_data = asyncio.run(create_wata_payment_link(rub_amount, order_id))
        
        print(f"✅ Payment created successfully: {order_id}")
        return jsonify({
            "url": link_data["url"],
            "id": link_data["id"],
            "order_id": order_id
        })
        
    except Exception as e:
        print(f"❌ Create payment error: {e}")
        return jsonify({"error": str(e)}), 500

async def check_wata_status(payment_id):
    """Check WATA payment status"""
    url = f"https://api.wata.pro/api/h2h/links/{payment_id}"
    headers = {
        "Authorization": f"Bearer {WATA_TOKEN}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"🔍 Checking WATA status for {payment_id}: HTTP {response.status}")
                
                if response.status != 200:
                    print(f"❌ WATA API error: {response.status}")
                    return False
                    
                data = await response.json()
                status = data.get("status", "").lower()
                print(f"📊 WATA payment status: {status}")
                
                # WATA статусы: pending, processing, closed, cancelled
                return status == "closed"
                
    except Exception as e:
        print(f"❌ Error checking WATA status: {e}")
        return False

async def send_ton_simulation(to_address, amount_nano):
    """Simulate TON transfer - replace with real implementation"""
    print(f"💸 Simulating TON transfer: {from_nano(amount_nano):.4f} TON to {to_address}")
    await asyncio.sleep(1)
    
    # TODO: Replace with real TON transfer
    # 
    # Для реального перевода TON:
    # 1. Добавьте в .env файл:
    #    SERVICE_WALLET_MNEMONIC="word1 word2 word3 ... word24"
    #    или
    #    SERVICE_WALLET_PRIVATE_KEY="your_private_key"
    # 
    # 2. Раскомментируйте код ниже:
    #
    # try:
    #     from pytoniq import LiteBalancer, WalletV4R2
    #     
    #     # Подключение к TON
    #     provider = LiteBalancer.from_mainnet_config(1)
    #     await provider.start_up()
    #     
    #     # Загрузка кошелька
    #     mnemonic = os.getenv("SERVICE_WALLET_MNEMONIC", "").split()
    #     if not mnemonic or len(mnemonic) != 24:
    #         raise Exception("SERVICE_WALLET_MNEMONIC not configured")
    #     
    #     wallet = await WalletV4R2.from_mnemonic(provider, mnemonic)
    #     
    #     # Отправка TON
    #     result = await wallet.transfer(to_address, amount_nano, comment="StarfallShop Exchange")
    #     
    #     await provider.close_all()
    #     return f"✅ TON sent: {result}"
    #     
    # except Exception as e:
    #     print(f"❌ Real TON transfer error: {e}")
    #     raise Exception(f"TON transfer failed: {e}")
    
    return f"✅ Sent {from_nano(amount_nano):.4f} TON to {to_address} (СИМУЛЯЦИЯ)"

@app.route("/check-payment", methods=["GET", "OPTIONS"])
def check_payment():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
        
    try:
        payment_id = request.args.get("id")
        order_id = request.args.get("order_id")
        
        print(f"🔍 Checking payment: id={payment_id}, order_id={order_id}")
        
        if not order_id or not payment_id:
            print("❌ Missing parameters")
            return jsonify({"status": "error", "message": "Missing parameters"})
        
        if order_id not in payments:
            print(f"❌ Order {order_id} not found")
            return jsonify({"status": "error", "message": "Order not found"})
        
        order_info = payments[order_id]
        print(f"📋 Order info: {order_info}")
        
        # If already completed, return completed status
        if order_info["status"] == "completed":
            print("✅ Order already completed")
            return jsonify({
                "status": "completed",
                "tx": order_info.get("tx", ""),
                "ton_amount": order_info["ton_amount"]
            })
        
        # Check WATA payment status
        is_paid = asyncio.run(check_wata_status(payment_id))
        print(f"💳 WATA payment status: {'PAID' if is_paid else 'PENDING'}")
        
        if is_paid and order_info["status"] == "pending":
            print("🚀 Processing TON transfer...")
            ton_amount = order_info["ton_amount"]
            nano_ton = to_nano(ton_amount)
            
            try:
                tx = asyncio.run(send_ton_simulation(order_info["user_address"], nano_ton))
                payments[order_id]["status"] = "completed"
                payments[order_id]["tx"] = tx
                
                print(f"✅ Transfer completed: {tx}")
                return jsonify({
                    "status": "completed",
                    "tx": tx,
                    "ton_amount": ton_amount
                })
            except Exception as e:
                print(f"❌ TON transfer error: {e}")
                return jsonify({"status": "error", "message": f"Transfer failed: {str(e)}"})
        else:
            print("⏳ Payment still pending")
            return jsonify({"status": "pending"})
            
    except Exception as e:
        print(f"❌ Check payment error: {e}")
        return jsonify({"status": "error", "message": str(e)})

# In-memory storage for payments
payments = {}

if __name__ == "__main__":
    print(f"🚀 StarfallShop Exchange Server запущен на http://0.0.0.0:{PORT}")
    print(f"💰 Курс: 1 TON = {TON_RATE_RUB} RUB")
    app.run(host='0.0.0.0', port=PORT, debug=os.getenv("DEBUG", "False").lower() == "true") 
import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import aiohttp
import uuid
import time
from datetime import datetime, timedelta

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

# Cache for WATA API responses to avoid 429 errors
wata_cache = {}
CACHE_DURATION = 30  # seconds

def cleanup_wata_cache():
    """Clean up expired cache entries"""
    current_time = time.time()
    expired_keys = [
        key for key, data in wata_cache.items() 
        if current_time - data['timestamp'] > CACHE_DURATION * 2
    ]
    for key in expired_keys:
        del wata_cache[key]
    
    if expired_keys:
        print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

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

@app.route("/force-refresh-payment", methods=["POST"])
def force_refresh_payment():
    """Force refresh payment status by clearing cache"""
    try:
        data = request.get_json()
        payment_id = data.get("payment_id")
        order_id = data.get("order_id")
        
        if not payment_id or not order_id:
            return jsonify({"error": "payment_id and order_id required"}), 400
            
        # Clear cache for this payment
        if payment_id in wata_cache:
            del wata_cache[payment_id]
            print(f"🧹 Manually cleared cache for payment {payment_id}")
        
        # Force check status
        is_paid = asyncio.run(check_wata_status(payment_id))
        
        return jsonify({
            "payment_id": payment_id,
            "order_id": order_id,
            "is_paid": is_paid,
            "cache_cleared": True
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

async def check_wata_status(payment_id, force_refresh=False):
    """Check WATA payment status with caching to avoid 429 errors"""
    current_time = time.time()
    
    # Check cache first (unless force refresh)
    if not force_refresh and payment_id in wata_cache:
        cached_data = wata_cache[payment_id]
        if current_time - cached_data['timestamp'] < CACHE_DURATION:
            print(f"🔄 Using cached WATA status for {payment_id}: {cached_data['status']}")
            return cached_data['status'] == "closed"
    
    url = f"https://api.wata.pro/api/h2h/links/{payment_id}"
    headers = {
        "Authorization": f"Bearer {WATA_TOKEN}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Add delay to avoid rate limiting
            await asyncio.sleep(1)
            
            async with session.get(url, headers=headers) as response:
                print(f"🔍 Checking WATA status for {payment_id}: HTTP {response.status}")
                
                if response.status == 429:
                    print(f"⚠️ WATA API rate limit hit")
                    # Return cached data if available, otherwise assume pending
                    if payment_id in wata_cache:
                        cached_status = wata_cache[payment_id]['status']
                        print(f"🔄 Using cached status: {cached_status}")
                        return cached_status == "closed"
                    else:
                        print("⏳ No cached data, assuming pending")
                        return False
                
                if response.status != 200:
                    print(f"❌ WATA API error: {response.status}")
                    # Return cached data if available
                    if payment_id in wata_cache:
                        cached_status = wata_cache[payment_id]['status']
                        print(f"🔄 Using cached status due to error: {cached_status}")
                        return cached_status == "closed"
                    return False
                    
                data = await response.json()
                status = data.get("status", "").lower()
                print(f"📊 WATA payment status: {status}")
                
                # Cache the result
                wata_cache[payment_id] = {
                    'status': status,
                    'timestamp': current_time
                }
                
                # WATA статусы: pending, processing, opened, closed, cancelled
                return status == "closed"
                
    except Exception as e:
        print(f"❌ Error checking WATA status: {e}")
        # Return cached data if available
        if payment_id in wata_cache:
            cached_status = wata_cache[payment_id]['status']
            print(f"🔄 Using cached status due to exception: {cached_status}")
            return cached_status == "closed"
        return False

async def send_ton_real(to_address, amount_nano):
    """Real TON transfer implementation"""
    print(f"💸 Sending {from_nano(amount_nano):.4f} TON to {to_address}")
    
    try:
        # Try to import pytoniq
        try:
            from pytoniq import LiteBalancer, WalletV5R1
            print(f"✅ pytoniq imported successfully")
        except ImportError as e:
            print(f"❌ pytoniq import failed: {e}")
            # Try alternative import
            try:
                from pytoniq import LiteBalancer, WalletV4R2 as WalletV5R1
                print(f"✅ Using WalletV4R2 as fallback")
            except ImportError:
                raise Exception("pytoniq library not available. Please check Railway deployment logs.")
        
        # Get service wallet mnemonic from environment
        mnemonic_str = os.getenv("SERVICE_WALLET_MNEMONIC", "")
        if not mnemonic_str or len(mnemonic_str.strip()) == 0:
            raise Exception("SERVICE_WALLET_MNEMONIC not configured in environment variables")
        
        mnemonic = mnemonic_str.strip().split()
        if len(mnemonic) != 24:
            raise Exception(f"Invalid mnemonic: expected 24 words, got {len(mnemonic)}")
        
        print(f"🔑 Loading service wallet from mnemonic...")
        
        # Connect to TON network
        provider = LiteBalancer.from_mainnet_config(1)
        await provider.start_up()
        print(f"🌐 Connected to TON mainnet")
        
        # Load service wallet
        wallet = await WalletV5R1.from_mnemonic(provider, mnemonic)
        wallet_address = wallet.address.to_str()
        print(f"👛 Service wallet loaded: {wallet_address}")
        
        # Check wallet balance
        balance = await wallet.get_balance()
        balance_ton = from_nano(balance)
        required_ton = from_nano(amount_nano)
        
        print(f"💰 Wallet balance: {balance_ton:.4f} TON")
        print(f"💸 Required amount: {required_ton:.4f} TON")
        
        if balance < amount_nano + 50000000:  # +0.05 TON for fees
            raise Exception(f"Insufficient balance: {balance_ton:.4f} TON, required: {required_ton + 0.05:.4f} TON")
        
        # Send TON
        print(f"🚀 Initiating transfer...")
        result = await wallet.transfer(
            destination=to_address,
            amount=amount_nano
        )
        
        await provider.close_all()
        
        tx_hash = result.hash.hex() if hasattr(result, 'hash') else str(result)
        print(f"✅ TON transfer completed! TX: {tx_hash}")
        
        return f"✅ Sent {from_nano(amount_nano):.4f} TON to {to_address} | TX: {tx_hash}"
        
    except Exception as e:
        print(f"❌ Real TON transfer error: {e}")
        raise Exception(f"TON transfer failed: {str(e)}")

async def send_ton_simulation(to_address, amount_nano):
    """Simulate TON transfer - DEPRECATED: Use send_ton_real instead"""
    print(f"⚠️ SIMULATION MODE - Real transfers disabled")
    print(f"💸 Would send {from_nano(amount_nano):.4f} TON to {to_address}")
    await asyncio.sleep(1)
    return f"✅ SIMULATION: {from_nano(amount_nano):.4f} TON to {to_address}"

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
        
        # Clean up old cache entries periodically
        cleanup_wata_cache()
        
        # Check WATA payment status
        is_paid = asyncio.run(check_wata_status(payment_id))
        print(f"💳 WATA payment status: {'PAID' if is_paid else 'PENDING'}")
        
        if is_paid and order_info["status"] == "pending":
            print("🚀 Processing TON transfer...")
            ton_amount = order_info["ton_amount"]
            nano_ton = to_nano(ton_amount)
            
            try:
                tx = asyncio.run(send_ton_real(order_info["user_address"], nano_ton))
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
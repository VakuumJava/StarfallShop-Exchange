import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import aiohttp
import uuid
import time
from datetime import datetime, timedelta
import random

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

# ---------------- TON provider helpers ----------------
STATIC_LITESERVERS = [
    {
        "ip": 109,
        "port": 48888,
        "id": {"@type": "pub.ed25519", "key": "aF91CuUHuuOv9rm2W5+O/4h38M3sRm+KDoFvPb2Nca0="},
    },
    {
        "ip": 159,
        "port": 49236,
        "id": {"@type": "pub.ed25519", "key": "3XO67K5i1F2d4uNbgkSFgX1d8v5gq2nF1qeJ4qL+Ku0="},
    },
    {
        "ip": 65,
        "port": 49616,
        "id": {"@type": "pub.ed25519", "key": "0v1zQQJ0lWQEGnGX3l3x5Oc1P8qZvCgPyVcE8JhJXK4="},
    },
]

# fix STATIC_LITESERVERS config issue by adding minimal validators field
STATIC_CONFIG = {"liteservers": STATIC_LITESERVERS, "validators": []}

async def _provider_from_global():
    """Try to build provider from fresh global config"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://ton.org/global-config.json", timeout=10) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                cfg = await resp.json()
        from pytoniq import LiteBalancer
        provider = LiteBalancer.from_config(cfg)
        await asyncio.wait_for(provider.start_up(), timeout=10)
        return provider
    except Exception as e:
        raise Exception(f"global config failed: {e}")

async def _provider_from_builtin(idx: int):
    try:
        from pytoniq import LiteBalancer
        provider = LiteBalancer.from_mainnet_config(idx)
        await asyncio.wait_for(provider.start_up(), timeout=10)
        return provider
    except Exception as e:
        raise Exception(f"builtin config {idx} failed: {e}")

async def _provider_from_static():
    try:
        from pytoniq import LiteBalancer
        provider = LiteBalancer.from_config(STATIC_CONFIG)
        await asyncio.wait_for(provider.start_up(), timeout=10)
        return provider
    except Exception as e:
        raise Exception(f"static config failed: {e}")

async def get_ton_provider(max_attempts: int = 5):
    """Return a connected provider or raise."""
    attempts = [_provider_from_global]
    for i in range(3):
        attempts.append(lambda idx=i: _provider_from_builtin(idx))

    random.shuffle(attempts)  # randomize order a bit

    last_err = None
    for fn in attempts[:max_attempts]:
        try:
            provider = await fn()
            print("✅ Connected to TON network")
            return provider
        except Exception as e:
            last_err = e
            print(f"⚠️ Provider attempt failed: {e}")
    raise Exception(last_err or "have no alive peers")

# -------------- Replace send_ton_real ------------------
async def send_ton_real(to_address: str, amount_nano: int):
    """Send TON with robust retries."""
    print(f"💸 Sending {from_nano(amount_nano):.4f} TON to {to_address}")

    # choose wallet class
    try:
        from pytoniq import WalletV5R1 as _Wallet
    except ImportError:
        from pytoniq import WalletV4R2 as _Wallet
    WalletClass = _Wallet

    mnemonic_str = os.getenv("SERVICE_WALLET_MNEMONIC", "").strip()
    if not mnemonic_str:
        raise Exception("SERVICE_WALLET_MNEMONIC not configured")
    mnemonic = mnemonic_str.split()
    if len(mnemonic) != 24:
        raise Exception("Invalid mnemonic length")

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        print(f"🔄 TON transfer attempt {attempt}/{max_attempts}")
        provider = None
        try:
            provider = await get_ton_provider()
            wallet = await WalletClass.from_mnemonic(provider, mnemonic)
            # after provider and wallet creation
            await ensure_wallet_deployed(wallet)
            balance = await wallet.get_balance()
            if balance < amount_nano + 50000000:
                raise Exception("Insufficient balance for transfer + fees")
            try:
                result = await wallet.transfer(destination=to_address, amount=amount_nano)
            except Exception as tx_err:
                if "seqno" in str(tx_err) or "-256" in str(tx_err):
                    print("⚠️ Seqno error during transfer; redeploy+retry once")
                    await ensure_wallet_deployed(wallet)
                    result = await wallet.transfer(destination=to_address, amount=amount_nano)
                else:
                    raise
            tx_hash = result.hash.hex() if hasattr(result, "hash") else str(result)
            print(f"✅ TON transfer completed! TX: {tx_hash}")
            await provider.close_all()
            return f"✅ Sent {from_nano(amount_nano):.4f} TON | TX: {tx_hash}"
        except Exception as e:
            print(f"❌ Attempt {attempt} failed: {e}")
            if provider:
                try:
                    await provider.close_all()
                except Exception:
                    pass
            if attempt == max_attempts:
                raise Exception(f"TON transfer failed after {max_attempts} attempts: {e}")
            await asyncio.sleep(2)  # small backoff

async def send_ton_simulation(to_address, amount_nano):
    """Simulate TON transfer - DEPRECATED: Use send_ton_real instead"""
    print(f"⚠️ SIMULATION MODE - Real transfers disabled")
    print(f"💸 Would send {from_nano(amount_nano):.4f} TON to {to_address}")
    await asyncio.sleep(1)
    return f"✅ SIMULATION: {from_nano(amount_nano):.4f} TON to {to_address}"

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

# In-memory storage for payments
payments = {}

# ---------------- Ensure /check-payment route exists ----------------
try:
    payments  # noqa: F401
except NameError:
    payments = {}

# Only add the route if it was removed accidentally
if not any(getattr(rule, 'rule', None) == '/check-payment' for rule in app.url_map.iter_rules()):
    @app.route('/check-payment', methods=['GET', 'OPTIONS'])
    def check_payment():
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'}), 200
        try:
            payment_id = request.args.get('id')
            order_id = request.args.get('order_id')
            print(f'🔍 Checking payment: id={payment_id}, order_id={order_id}')
            if not payment_id or not order_id:
                return jsonify({'status': 'error', 'message': 'Missing parameters'})
            if order_id not in payments:
                return jsonify({'status': 'error', 'message': 'Order not found'})
            order = payments[order_id]
            if order['status'] == 'completed':
                return jsonify({'status': 'completed', 'tx': order.get('tx', ''), 'ton_amount': order['ton_amount']})
            # refresh WATA status
            cleanup_wata_cache()
            is_paid = asyncio.run(check_wata_status(payment_id))
            if is_paid and order['status'] == 'pending':
                nano = to_nano(order['ton_amount'])
                try:
                    tx = asyncio.run(send_ton_real(order['user_address'], nano))
                    order['status'] = 'completed'
                    order['tx'] = tx
                    return jsonify({'status': 'completed', 'tx': tx, 'ton_amount': order['ton_amount']})
                except Exception as e:
                    return jsonify({'status': 'error', 'message': f'Transfer failed: {str(e)}'})
            return jsonify({'status': 'pending'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

if __name__ == "__main__":
    print(f"🚀 StarfallShop Exchange Server запущен на http://0.0.0.0:{PORT}")
    print(f"💰 Курс: 1 TON = {TON_RATE_RUB} RUB")
    app.run(host='0.0.0.0', port=PORT, debug=os.getenv("DEBUG", "False").lower() == "true") 
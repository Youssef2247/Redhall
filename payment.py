# payment.py

import aiohttp
import hmac
import hashlib
from config import PAYMOB_API_KEY, PAYMOB_INTEGRATION_ID, PAYMOB_HMAC_SECRET


async def get_auth_token() -> str:
    """Step 1: Get authentication token from Paymob."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://accept.paymob.com/api/auth/tokens",
            json={"api_key": PAYMOB_API_KEY}
        ) as resp:
            data = await resp.json()
            return data["token"]


async def create_order(auth_token: str, amount_cents: int, order_id: int) -> str:
    """Step 2: Register order with Paymob."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://accept.paymob.com/api/ecommerce/orders",
            json={
                "auth_token": auth_token,
                "delivery_needed": False,
                "amount_cents": amount_cents,
                "currency": "EGP",
                "merchant_order_id": str(order_id),
                "items": []
            }
        ) as resp:
            data = await resp.json()
            return data["id"]


async def get_payment_key(auth_token: str, paymob_order_id: str, amount_cents: int, customer_name: str) -> str:
    """Step 3: Get payment key."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://accept.paymob.com/api/acceptance/payment_keys",
            json={
                "auth_token": auth_token,
                "amount_cents": amount_cents,
                "expiration": 3600,
                "order_id": paymob_order_id,
                "currency": "EGP",
                "integration_id": PAYMOB_INTEGRATION_ID,
                "billing_data": {
                    "first_name": customer_name,
                    "last_name": ".",
                    "email": "customer@restaurant.com",
                    "phone_number": "01000000000",
                    "apartment": "NA",
                    "floor": "NA",
                    "street": "NA",
                    "building": "NA",
                    "shipping_method": "NA",
                    "postal_code": "NA",
                    "city": "Cairo",
                    "country": "EG",
                    "state": "Cairo"
                }
            }
        ) as resp:
            data = await resp.json()
            return data["token"]


async def create_payment_link(amount_egp: float, order_id: int, customer_name: str) -> str:
    """Full flow: returns a ready-to-use payment URL."""
    amount_cents = int(amount_egp * 100)
    auth_token     = await get_auth_token()
    paymob_order   = await create_order(auth_token, amount_cents, order_id)
    payment_key    = await get_payment_key(auth_token, paymob_order, amount_cents, customer_name)
    payment_url    = f"https://accept.paymob.com/api/acceptance/iframes/YOUR_IFRAME_ID?payment_token={payment_key}"
    return payment_url


def verify_hmac(data: dict) -> bool:
    """Verify that the callback from Paymob is genuine."""
    received_hmac = data.get("hmac", "")
    fields = [
        "amount_cents", "created_at", "currency", "error_occured",
        "has_parent_transaction", "id", "integration_id", "is_3d_secure",
        "is_auth", "is_capture", "is_refunded", "is_standalone_payment",
        "is_voided", "order", "owner", "pending",
        "source_data_pan", "source_data_sub_type", "source_data_type", "success"
    ]
    concatenated = "".join(str(data.get(f, "")) for f in fields)
    expected = hmac.new(
        PAYMOB_HMAC_SECRET.encode(),
        concatenated.encode(),
        hashlib.sha512
    ).hexdigest()
    return received_hmac == expected

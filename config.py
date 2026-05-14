import os

CUSTOMER_BOT_TOKEN = os.environ.get("CUSTOMER_BOT_TOKEN", "")
STAFF_BOT_TOKEN    = os.environ.get("STAFF_BOT_TOKEN", "")
STAFF_GROUP_ID     = int(os.environ.get("STAFF_GROUP_ID", "0"))
PAYMOB_API_KEY        = os.environ.get("PAYMOB_API_KEY", "")
PAYMOB_INTEGRATION_ID = int(os.environ.get("PAYMOB_INTEGRATION_ID", "0"))
PAYMOB_HMAC_SECRET    = os.environ.get("PAYMOB_HMAC_SECRET", "")
DATABASE_PATH      = os.environ.get("DATABASE_PATH", "restaurant.db")

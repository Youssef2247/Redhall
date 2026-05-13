import os

CUSTOMER_BOT_TOKEN = os.environ.get("CUSTOMER_BOT_TOKEN", "")
STAFF_BOT_TOKEN    = os.environ.get("STAFF_BOT_TOKEN", "")
STAFF_GROUP_ID     = int(os.environ.get("STAFF_GROUP_ID", "0"))
DATABASE_PATH      = os.environ.get("DATABASE_PATH", "restaurant.db")

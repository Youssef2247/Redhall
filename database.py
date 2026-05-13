import aiosqlite
import json
from config import DATABASE_PATH


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                username    TEXT,
                items       TEXT NOT NULL,
                total       REAL NOT NULL,
                status      TEXT DEFAULT 'pending',
                notes       TEXT DEFAULT '',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def create_order(customer_id, username, items, total, notes=""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO orders (customer_id, username, items, total, notes) VALUES (?, ?, ?, ?, ?)",
            (customer_id, username, json.dumps(items), total, notes)
        )
        await db.commit()
        return cursor.lastrowid


async def get_order(order_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            if row:
                order = dict(row)
                order["items"] = json.loads(order["items"])
                return order
    return None


async def update_order_status(order_id, status):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()


async def get_orders_by_status(status):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,)
        ) as cur:
            rows = await cur.fetchall()
            orders = []
            for row in rows:
                o = dict(row)
                o["items"] = json.loads(o["items"])
                orders.append(o)
            return orders
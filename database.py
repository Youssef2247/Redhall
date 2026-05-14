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

async def toggle_item_availability(item_id: str) -> bool:
    """Toggle an item's availability. Returns the new state (True = available)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS item_availability (
                item_id     TEXT PRIMARY KEY,
                available   INTEGER DEFAULT 1
            )
        """)
        await db.commit()

        async with db.execute(
            "SELECT available FROM item_availability WHERE item_id = ?", (item_id,)
        ) as cur:
            row = await cur.fetchone()

        if row is None:
            # Item not in table yet — means it was available, now mark unavailable
            await db.execute(
                "INSERT INTO item_availability (item_id, available) VALUES (?, 0)", (item_id,)
            )
            new_state = False
        else:
            new_state = not bool(row[0])
            await db.execute(
                "UPDATE item_availability SET available = ? WHERE item_id = ?",
                (int(new_state), item_id)
            )
        await db.commit()
        return new_state


async def get_unavailable_items() -> set:
    """Return a set of item_ids that are currently unavailable."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS item_availability (
                item_id     TEXT PRIMARY KEY,
                available   INTEGER DEFAULT 1
            )
        """)
        await db.commit()
        async with db.execute(
            "SELECT item_id FROM item_availability WHERE available = 0"
        ) as cur:
            rows = await cur.fetchall()
            return {row[0] for row in rows}

async def create_group_order(host_id: int, host_username: str) -> str:
    """Create a new group order session, returns the group_code."""
    import random, string
    group_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_orders (
                group_code   TEXT PRIMARY KEY,
                host_id      INTEGER NOT NULL,
                host_username TEXT,
                status       TEXT DEFAULT 'open',
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_order_members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_code  TEXT NOT NULL,
                user_id     INTEGER NOT NULL,
                username    TEXT,
                items       TEXT DEFAULT '[]',
                confirmed   INTEGER DEFAULT 0
            )
        """)
        await db.commit()
        await db.execute(
            "INSERT INTO group_orders (group_code, host_id, host_username) VALUES (?, ?, ?)",
            (group_code, host_id, host_username)
        )
        await db.execute(
            "INSERT INTO group_order_members (group_code, user_id, username) VALUES (?, ?, ?)",
            (group_code, host_id, host_username)
        )
        await db.commit()
    return group_code


async def get_group_order(group_code: str) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_orders (
                group_code   TEXT PRIMARY KEY,
                host_id      INTEGER NOT NULL,
                host_username TEXT,
                status       TEXT DEFAULT 'open',
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_order_members (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                group_code  TEXT NOT NULL,
                user_id     INTEGER NOT NULL,
                username    TEXT,
                items       TEXT DEFAULT '[]',
                confirmed   INTEGER DEFAULT 0
            )
        """)
        await db.commit()
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM group_orders WHERE group_code = ?", (group_code,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            order = dict(row)
        async with db.execute(
            "SELECT * FROM group_order_members WHERE group_code = ?", (group_code,)
        ) as cur:
            rows = await cur.fetchall()
            order["members"] = []
            for r in rows:
                m = dict(r)
                m["items"] = json.loads(m["items"])
                order["members"].append(m)
        return order


async def join_group_order(group_code: str, user_id: int, username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT id FROM group_order_members WHERE group_code = ? AND user_id = ?",
            (group_code, user_id)
        ) as cur:
            exists = await cur.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO group_order_members (group_code, user_id, username) VALUES (?, ?, ?)",
                (group_code, user_id, username)
            )
            await db.commit()


async def update_member_items(group_code: str, user_id: int, items: list):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE group_order_members SET items = ?, confirmed = 1 WHERE group_code = ? AND user_id = ?",
            (json.dumps(items), group_code, user_id)
        )
        await db.commit()


async def close_group_order(group_code: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE group_orders SET status = 'closed' WHERE group_code = ?",
            (group_code,)
        )
        await db.commit()

# staff_bot.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from database import get_order, update_order_status, get_orders_by_status
from config import STAFF_BOT_TOKEN


# ─── Helpers ─────────────────────────────────────────────────────────────────

def format_order(order: dict) -> str:
    items_text = "\n".join(
        f"  • {i['name']} x{i['qty']}  ({i['price'] * i['qty']:.2f} EGP)"
        for i in order["items"]
    )
    return (
        f"📋 Order #{order['id']}\n"
        f"👤 Customer: @{order['username']}\n"
        f"📝 Notes: {order['notes'] or 'None'}\n\n"
        f"Items:\n{items_text}\n\n"
        f"💰 Total: {order['total']:.2f} EGP\n"
        f"🕐 Status: {order['status'].upper()}\n"
        f"🗓 Time: {order['created_at']}"
    )


# ─── Menu management ──────────────────────────────────────────────────────────

async def manage_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from menu import MENU
    from database import get_unavailable_items
    unavailable = await get_unavailable_items()

    keyboard = []
    for category, items in MENU.items():
        keyboard.append([InlineKeyboardButton(f"── {category} ──", callback_data="noop")])
        for item in items:
            status = "❌ OFF" if item["id"] in unavailable else "✅ ON"
            keyboard.append([InlineKeyboardButton(
                f"{status}  |  {item['name']}",
                callback_data=f"toggleitem_{item['id']}"
            )])

    await update.message.reply_text(
        "📋 Menu Availability\nTap any item to toggle it on/off:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def toggle_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    item_id = query.data[len("toggleitem_"):]
    from database import toggle_item_availability, get_unavailable_items
    from menu import MENU, get_item_by_id

    new_state = await toggle_item_availability(item_id)
    item = get_item_by_id(item_id)
    status_text = "✅ now AVAILABLE" if new_state else "❌ now UNAVAILABLE"
    await query.answer(f"{item['name']} is {status_text}", show_alert=True)

    unavailable = await get_unavailable_items()
    keyboard = []
    for category, items in MENU.items():
        keyboard.append([InlineKeyboardButton(f"── {category} ──", callback_data="noop")])
        for i in items:
            status = "❌ OFF" if i["id"] in unavailable else "✅ ON"
            keyboard.append([InlineKeyboardButton(
                f"{status}  |  {i['name']}",
                callback_data=f"toggleitem_{i['id']}"
            )])

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))


# ─── Order actions ────────────────────────────────────────────────────────────

async def handle_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔔 Staff action triggered: {update.callback_query.data}")
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    action      = parts[1]
    order_id    = int(parts[2])
    customer_id = int(parts[3])

    status_map = {"accept": "accepted", "reject": "rejected", "ready": "ready"}
    new_status = status_map.get(action)
    if not new_status:
        return

    await update_order_status(order_id, new_status)

    status_labels = {
        "accepted": "✅ Accepted",
        "rejected": "❌ Rejected",
        "ready":    "🍽 Ready for pickup",
    }
    staff_name = query.from_user.first_name

    try:
        if new_status == "accepted":
            remaining_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🍽 Ready", callback_data=f"staff_ready_{order_id}_{customer_id}")]
            ])
            await query.edit_message_text(
                query.message.text + f"\n\n── {status_labels[new_status]} by {staff_name} ──",
                reply_markup=remaining_keyboard
            )
        else:
            await query.edit_message_text(
                query.message.text + f"\n\n── {status_labels[new_status]} by {staff_name} ──"
            )
    except Exception as e:
        print(f"Could not edit staff message: {e}")

    try:
        messages = {
            "accepted": f"✅ Your order #{order_id} has been accepted and is being prepared. We will notify you when it is ready!",
            "rejected": f"❌ Sorry, your order #{order_id} was rejected. Please contact us for more information.",
            "ready":    f"🍽 Your order #{order_id} is ready for pickup! Please come collect it. Thank you!",
        }
        from telegram import Bot
        from config import CUSTOMER_BOT_TOKEN
        customer_bot = Bot(token=CUSTOMER_BOT_TOKEN)
        await customer_bot.send_message(chat_id=customer_id, text=messages[new_status])
        print(f"✅ Customer {customer_id} notified: order #{order_id} is {new_status}")
    except Exception as e:
        print(f"❌ Could not notify customer: {e}")


# ─── /orders command ──────────────────────────────────────────────────────────

async def list_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = await get_orders_by_status("pending")
    if not orders:
        await update.message.reply_text("✅ No pending orders right now.")
        return
    for order in orders:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"staff_accept_{order['id']}_{order['customer_id']}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"staff_reject_{order['id']}_{order['customer_id']}"),
            ],
            [InlineKeyboardButton("🍽 Ready", callback_data=f"staff_ready_{order['id']}_{order['customer_id']}")],
        ])
        await update.message.reply_text(format_order(order), reply_markup=keyboard)


# ─── /allorders command ───────────────────────────────────────────────────────

async def all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    valid = ["pending", "accepted", "rejected", "ready"]
    if not args or args[0] not in valid:
        await update.message.reply_text(f"Usage: /allorders <status>\nValid: {', '.join(valid)}")
        return
    orders = await get_orders_by_status(args[0])
    if not orders:
        await update.message.reply_text(f"No {args[0]} orders found.")
        return
    for order in orders:
        await update.message.reply_text(format_order(order))


# ─── App builder ──────────────────────────────────────────────────────────────

def build_staff_app() -> Application:
    app = Application.builder().token(STAFF_BOT_TOKEN).build()

    app.add_handler(CommandHandler("orders",    list_pending_orders))
    app.add_handler(CommandHandler("allorders", all_orders))
    app.add_handler(CommandHandler("menu",      manage_menu))
    app.add_handler(CallbackQueryHandler(handle_order_action, pattern="^staff_"))
    app.add_handler(CallbackQueryHandler(toggle_item,         pattern="^toggleitem_"))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))

    return app

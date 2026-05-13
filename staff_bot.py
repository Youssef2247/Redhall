# staff_bot.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from database import get_order, update_order_status, get_orders_by_status
from config import STAFF_BOT_TOKEN


# ─── Helpers ────────────────────────────────────────────────────────────────

def format_order(order: dict) -> str:
    """Format an order dict into a readable message."""
    items_text = "\n".join(
        f"  • {i['name']} x{i['qty']}  ({i['price'] * i['qty']:.2f} EGP)"
        for i in order["items"]
    )
    return (
        f"📋 *Order #{order['id']}*\n"
        f"👤 Customer: @{order['username']}\n"
        f"📝 Notes: {order['notes'] or 'None'}\n\n"
        f"Items:\n{items_text}\n\n"
        f"💰 Total: {order['total']:.2f} EGP\n"
        f"🕐 Status: {order['status'].upper()}\n"
        f"🗓 Time: {order['created_at']}"
    )


# ─── Order action buttons (Accept / Reject / Ready) ─────────────────────────
# These callbacks are triggered when staff tap the buttons on order notifications.
# The callback_data format is: "staff_<action>_<order_id>_<customer_id>"
# This is set in customer_bot.py when the order notification is sent to the group.

async def handle_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"🔔 Staff action triggered: {update.callback_query.data}")  # ADD THIS LINE
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    action      = parts[1]
    order_id    = int(parts[2])
    customer_id = int(parts[3])

    status_map = {
        "accept": "accepted",
        "reject": "rejected",
        "ready":  "ready",
    }
    new_status = status_map.get(action)
    if not new_status:
        return

    await update_order_status(order_id, new_status)

    status_labels = {
        "accepted": "✅ Accepted",
        "rejected":  "❌ Rejected",
        "ready":     "🍽 Ready for pickup",
    }

    staff_name = query.from_user.first_name

    # Update the message in the staff group
    try:
        from telegram import Bot
        from config import CUSTOMER_BOT_TOKEN
        
        messages = {
            "accepted": (
                f"✅ Good news! Your order #{order_id} has been accepted "
                f"and is being prepared. We will notify you when it is ready!"
            ),
            "rejected": (
                f"❌ Sorry, your order #{order_id} was rejected. "
                f"Please contact us for more information."
            ),
            "ready": (
                f"🍽 Your order #{order_id} is ready for pickup! "
                f"Please come collect it. Thank you for ordering with us!"
            ),
        }

        print(f"📨 Attempting to notify customer_id={customer_id} status={new_status}")
        customer_bot = Bot(token=CUSTOMER_BOT_TOKEN)
        await customer_bot.send_message(
            chat_id=customer_id,
            text=messages[new_status]
        )
        print(f"✅ Customer {customer_id} notified: order #{order_id} is {new_status}")
    except Exception as e:
        import traceback
        print(f"❌ Could not notify customer: {e}")
        traceback.print_exc()
    # Notify the customer via the customer bot token
    messages = {
        "accepted": (
            f"✅ Good news! Your order #{order_id} has been accepted "
            f"and is being prepared. We will notify you when it is ready!"
        ),
        "rejected": (
            f"❌ Sorry, your order #{order_id} was rejected. "
            f"Please contact us for more information."
        ),
        "ready": (
            f"🍽 Your order #{order_id} is ready for pickup! "
            f"Please come collect it. Thank you for ordering with us!"
        ),
    }

    # Update the message in the staff group
    try:
        if new_status == "accepted":
            # Keep the Ready button visible after accepting
            remaining_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🍽 Ready", callback_data=f"staff_ready_{order_id}_{customer_id}")]
            ])
            await query.edit_message_text(
                query.message.text + f"\n\n── {status_labels[new_status]} by {staff_name} ──",
                reply_markup=remaining_keyboard
            )
        else:
            # For rejected or ready, remove all buttons
            await query.edit_message_text(
                query.message.text + f"\n\n── {status_labels[new_status]} by {staff_name} ──"
            )
    except Exception as e:
        print(f"Could not edit staff message: {e}")
# ─── /orders command — view pending orders ───────────────────────────────────

async def list_pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all currently pending orders."""
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
            [InlineKeyboardButton("🍽 Ready",    callback_data=f"staff_ready_{order['id']}_{order['customer_id']}")],
        ])
        await update.message.reply_text(
            format_order(order),
            parse_mode="Markdown",
            reply_markup=keyboard
        )


# ─── /allorders command — view orders by status ──────────────────────────────

async def all_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Usage: /allorders <status>   e.g. /allorders accepted"""
    args = context.args
    valid = ["pending", "accepted", "rejected", "ready"]

    if not args or args[0] not in valid:
        await update.message.reply_text(
            f"Usage: /allorders <status>\nValid statuses: {', '.join(valid)}"
        )
        return

    orders = await get_orders_by_status(args[0])
    if not orders:
        await update.message.reply_text(f"No {args[0]} orders found.")
        return

    for order in orders:
        await update.message.reply_text(format_order(order), parse_mode="Markdown")


# ─── App builder ─────────────────────────────────────────────────────────────

def build_staff_app() -> Application:
    app = Application.builder().token(STAFF_BOT_TOKEN).build()

    app.add_handler(CommandHandler("orders", list_pending_orders))
    app.add_handler(CommandHandler("allorders", all_orders))
    app.add_handler(CallbackQueryHandler(handle_order_action, pattern="^staff_"))

    # 👇 ADD THIS LINE
    app.add_handler(MessageHandler(filters.ALL, debug_chat_id))

    return app
from telegram.ext import MessageHandler, filters

async def debug_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("CHAT ID:", update.effective_chat.id)
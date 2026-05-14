from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from menu import MENU, get_item_by_id
from database import create_order
from config import CUSTOMER_BOT_TOKEN, STAFF_GROUP_ID


def get_cart(context):
    return context.user_data.get("cart", [])


def format_cart(cart):
    if not cart:
        return "Your cart is empty."
    lines = []
    total = 0
    for item in cart:
        subtotal = item["price"] * item["qty"]
        lines.append(f"• {item['name']} x{item['qty']}  —  {subtotal:.2f} EGP")
        total += subtotal
    lines.append(f"\n🧾 Total: {total:.2f} EGP")
    return "\n".join(lines)


def cart_total(cart):
    return sum(item["price"] * item["qty"] for item in cart)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("🍽 View Menu", callback_data="show_menu")]]
    await update.message.reply_text(
        f"👋 Welcome to our restaurant, {update.effective_user.first_name}!\n\n"
        "Browse our menu and place your order right here.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"cat_{category}")]
        for category in MENU.keys()
    ]
    keyboard.append([InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")])
    await query.edit_message_text("Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data[4:]
    items = MENU.get(category, [])

    from database import get_unavailable_items
    unavailable = await get_unavailable_items()

    keyboard = []
    for item in items:
        status = "❌" if item["id"] in unavailable else "✅"
        keyboard.append([InlineKeyboardButton(
            f"{status} {item['name']}  —  {item['price']:.2f} EGP",
            callback_data=f"add_{item['id']}" if item["id"] not in unavailable else "unavailable"
        )])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="show_menu")])

    await query.edit_message_text(
        f"{category}\n\nTap an available item to add it to your cart:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = query.data[4:]
    item = get_item_by_id(item_id)
    if not item:
        await query.answer("Item not found.", show_alert=True)
        return
    cart = context.user_data.setdefault("cart", [])
    for cart_item in cart:
        if cart_item["id"] == item_id:
            cart_item["qty"] += 1
            break
    else:
        cart.append({**item, "qty": 1})
    keyboard = [
        [InlineKeyboardButton("➕ Add More Items", callback_data="show_menu")],
        [InlineKeyboardButton("🛒 View Cart", callback_data="view_cart")],
    ]
    await query.edit_message_text(
        f"✅ *{item['name']}* added to your cart!\n\n{format_cart(cart)}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = get_cart(context)
    if not cart:
        keyboard = [[InlineKeyboardButton("🍽 View Menu", callback_data="show_menu")]]
        await query.edit_message_text(
            "Your cart is empty. Start by browsing the menu!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    keyboard = [
        [InlineKeyboardButton("✅ Place Order", callback_data="confirm_order")],
        [InlineKeyboardButton("🗑 Clear Cart", callback_data="clear_cart")],
        [InlineKeyboardButton("➕ Add More Items", callback_data="show_menu")],
    ]
    await query.edit_message_text(
        f"🛒 *Your Cart*\n\n{format_cart(cart)}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["cart"] = []
    keyboard = [[InlineKeyboardButton("🍽 View Menu", callback_data="show_menu")]]
    await query.edit_message_text("🗑 Cart cleared.", reply_markup=InlineKeyboardMarkup(keyboard))


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cart = get_cart(context)
    if not cart:
        await query.edit_message_text("Your cart is empty!")
        return
    context.user_data["awaiting_notes"] = True
    keyboard = [[InlineKeyboardButton("⏭ No notes, place order", callback_data="place_order_no_notes")]]
    await query.edit_message_text(
        f"🛒 *Order Summary*\n\n{format_cart(cart)}\n\n"
        "Any special requests? Type them below, or tap to skip.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def receive_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_notes"):
        return
    notes = update.message.text
    context.user_data["awaiting_notes"] = False
    await place_order(update, context, notes=notes)


async def place_order_no_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_notes"] = False
    await place_order(update, context, notes="")

async def place_order(update: Update, context: ContextTypes.DEFAULT_TYPE, notes: str = ""):
    user = update.effective_user
    cart = get_cart(context)
    total = cart_total(cart)

    try:
        order_id = await create_order(
            customer_id=user.id,
            username=user.username or user.first_name,
            items=cart,
            total=total,
            notes=notes
        )

        items_text = "\n".join(
            f"  • {i['name']} x{i['qty']}  ({i['price'] * i['qty']:.2f} EGP)"
            for i in cart
        )
        staff_message = (
            f"🔔 New Order #{order_id}\n\n"
            f"👤 Customer: @{user.username or user.first_name}\n"
            f"📋 Items:\n{items_text}\n\n"
            f"💰 Total: {total:.2f} EGP\n"
            f"📝 Notes: {notes or 'None'}"
        )
        staff_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"staff_accept_{order_id}_{user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"staff_reject_{order_id}_{user.id}"),
            ],
            [InlineKeyboardButton("🍽 Ready", callback_data=f"staff_ready_{order_id}_{user.id}")],
        ])

        from telegram import Bot
        from config import STAFF_BOT_TOKEN
        staff_bot = Bot(token=STAFF_BOT_TOKEN)
        await staff_bot.send_message(
            chat_id=STAFF_GROUP_ID,
            text=staff_message,
            reply_markup=staff_keyboard
        )

        context.user_data["cart"] = []
        confirmation = (
            f"🎉 Order #{order_id} placed successfully!\n\n"
            f"{format_cart(cart)}\n\n"
            "We'll notify you as soon as your order is confirmed."
        )

        
        if update.callback_query:
            await update.callback_query.edit_message_text(confirmation)
        else:
            await update.message.reply_text(confirmation)
    except Exception as e:
        print(f"❌ Error in place_order: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ Something went wrong placing your order. Please try again.")
            else:
                await update.message.reply_text("❌ Something went wrong. Please try again.")
        except:
            pass


def build_customer_app():
    app = Application.builder().token(CUSTOMER_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_menu,            pattern="^show_menu$"))
    app.add_handler(CallbackQueryHandler(show_category,        pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(add_to_cart,          pattern="^add_"))
    app.add_handler(CallbackQueryHandler(view_cart,            pattern="^view_cart$"))
    app.add_handler(CallbackQueryHandler(clear_cart,           pattern="^clear_cart$"))
    app.add_handler(CallbackQueryHandler(confirm_order,        pattern="^confirm_order$"))
    app.add_handler(CallbackQueryHandler(place_order_no_notes, pattern="^place_order_no_notes$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_notes))
    # Make sure customer bot does NOT handle staff callbacks
    # (remove any wildcard callback handler if present)
    app.add_handler(CallbackQueryHandler(
        lambda u, c: u.callback_query.answer("❌ This item is currently unavailable.", show_alert=True),
        pattern="^unavailable$"
    ))
    return app

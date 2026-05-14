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
    args = context.args

    # Check if joining a group order
    if args and args[0].startswith("join_"):
        group_code = args[0].replace("join_", "")
        from database import get_group_order, join_group_order
        group = await get_group_order(group_code)

        if not group or group["status"] == "closed":
            await update.message.reply_text("❌ This group order is no longer active.")
            return

        user = update.effective_user
        await join_group_order(group_code, user.id, user.username or user.first_name)
        context.user_data["group_code"] = group_code

        keyboard = [[InlineKeyboardButton("🛒 Add My Items", callback_data=f"group_add_items_{group_code}")]]
        await update.message.reply_text(
            f"👥 You joined {group['host_username']}'s group order!\n\n"
            f"Add your items and the host will confirm the order.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Normal start
    keyboard = [
        [InlineKeyboardButton("🍽 View Menu", callback_data="show_menu")],
        [InlineKeyboardButton("👥 Start Group Order", callback_data="start_group_order")],
    ]
    await update.message.reply_text(
        f"👋 Welcome to our restaurant, {update.effective_user.first_name}!\n\n"
        "Browse our menu or start a group order with friends.",
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

    # If part of a group order, save items to group instead
    group_code = context.user_data.get("group_code")
    if group_code:
        cart = get_cart(context)
        if cart:
            from database import update_member_items
            await update_member_items(group_code, update.effective_user.id, cart)
            context.user_data["cart"] = []
            keyboard = [[InlineKeyboardButton("👀 View Group Order", callback_data=f"group_view_{group_code}")]]
            await query.edit_message_text(
                "✅ Your items have been added to the group order!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

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

# ─── Group Order ─────────────────────────────────────────────────────────────

async def start_group_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Host creates a new group order."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    from database import create_group_order
    group_code = await create_group_order(
        host_id=user.id,
        host_username=user.username or user.first_name
    )

    context.user_data["group_code"] = group_code
    context.user_data["is_host"] = True

    bot_username = (await context.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=join_{group_code}"

    keyboard = [
        [InlineKeyboardButton("🛒 Add My Items", callback_data=f"group_add_items_{group_code}")],
        [InlineKeyboardButton("👀 View Group Order", callback_data=f"group_view_{group_code}")],
        [InlineKeyboardButton("❌ Cancel Group Order", callback_data=f"group_cancel_{group_code}")],
    ]
    await query.edit_message_text(
        f"👥 Group Order Created!\n\n"
        f"Code: {group_code}\n\n"
        f"Share this link with your friends:\n{invite_link}\n\n"
        f"Everyone adds their own items, then you confirm the order.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def view_group_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current group order status."""
    query = update.callback_query
    await query.answer()

    group_code = query.data.replace("group_view_", "")
    from database import get_group_order
    group = await get_group_order(group_code)

    if not group or group["status"] == "closed":
        await query.edit_message_text("❌ This group order is no longer active.")
        return

    lines = [f"👥 Group Order — {group_code}\n"]
    total = 0
    all_confirmed = True

    for member in group["members"]:
        if not member["items"]:
            lines.append(f"⏳ {member['username']} — still choosing...")
            all_confirmed = False
        else:
            member_total = sum(i["price"] * i["qty"] for i in member["items"])
            items_str = ", ".join(f"{i['name']} x{i['qty']}" for i in member["items"])
            lines.append(f"✅ {member['username']} — {items_str} ({member_total:.2f} EGP)")
            total += member_total

    lines.append(f"\n💰 Total: {total:.2f} EGP")

    keyboard = []
    user = update.effective_user
    if user.id == group["host_id"]:
        keyboard.append([InlineKeyboardButton("✅ Confirm & Place Order", callback_data=f"group_confirm_{group_code}")])
    keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data=f"group_view_{group_code}")])
    keyboard.append([InlineKeyboardButton("🛒 Add/Edit My Items", callback_data=f"group_add_items_{group_code}")])

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def group_add_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Let a member browse the menu and add items for the group order."""
    query = update.callback_query
    await query.answer()

    group_code = query.data.replace("group_add_items_", "")
    context.user_data["group_code"] = group_code
    context.user_data["cart"] = []

    keyboard = [
        [InlineKeyboardButton(category, callback_data=f"cat_{category}")]
        for category in MENU.keys()
    ]
    await query.edit_message_text(
        "🛒 Browse the menu and add your items.\n"
        "When done, tap 'View Cart' and confirm.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def group_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Host confirms and places the group order."""
    query = update.callback_query
    await query.answer()

    group_code = query.data.replace("group_confirm_", "")
    from database import get_group_order, close_group_order

    group = await get_group_order(group_code)
    if not group:
        await query.edit_message_text("❌ Group order not found.")
        return

    # Build combined order for staff
    all_items = []
    total = 0
    member_summary = []

    for member in group["members"]:
        if member["items"]:
            member_total = sum(i["price"] * i["qty"] for i in member["items"])
            items_str = "\n".join(
                f"    • {i['name']} x{i['qty']}  ({i['price'] * i['qty']:.2f} EGP)"
                for i in member["items"]
            )
            member_summary.append(
                f"👤 {member['username']} ({member_total:.2f} EGP):\n{items_str}"
            )
            all_items.extend(member["items"])
            total += member_total

    order_id = await create_order(
        customer_id=update.effective_user.id,
        username=f"GROUP-{group_code}",
        items=all_items,
        total=total,
        notes=f"Group order by {group['host_username']}"
    )

    await close_group_order(group_code)

    # Notify staff
    staff_message = (
        f"🔔 New GROUP Order #{order_id}\n\n"
        f"👥 Group Code: {group_code}\n"
        f"👤 Host: @{group['host_username']}\n"
        f"💰 Total: {total:.2f} EGP\n"
        f"💵 Payment: Cash on Delivery (each pays separately)\n\n"
        + "\n\n".join(member_summary)
    )

    staff_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"staff_accept_{order_id}_{update.effective_user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"staff_reject_{order_id}_{update.effective_user.id}"),
        ],
        [InlineKeyboardButton("🍽 Ready", callback_data=f"staff_ready_{order_id}_{update.effective_user.id}")],
    ])

    from telegram import Bot
    from config import STAFF_BOT_TOKEN
    staff_bot = Bot(token=STAFF_BOT_TOKEN)
    await staff_bot.send_message(
        chat_id=STAFF_GROUP_ID,
        text=staff_message,
        reply_markup=staff_keyboard
    )

    # Notify all members
    for member in group["members"]:
        if member["user_id"] != update.effective_user.id:
            try:
                await context.bot.send_message(
                    chat_id=member["user_id"],
                    text=f"✅ Your group order #{order_id} has been placed!\n"
                         f"💵 Please pay your share in cash when you collect your items."
                )
            except:
                pass

    await query.edit_message_text(
        f"🎉 Group Order #{order_id} placed!\n\n"
        f"💰 Total: {total:.2f} EGP\n"
        f"💵 Each person pays their share in cash.\n\n"
        f"We'll notify everyone when the order is ready!"
    )


async def group_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    group_code = query.data.replace("group_cancel_", "")
    from database import close_group_order
    await close_group_order(group_code)
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="show_menu")]]
    await query.edit_message_text("❌ Group order cancelled.", reply_markup=InlineKeyboardMarkup(keyboard))


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
    app.add_handler(CallbackQueryHandler(start_group_order,   pattern="^start_group_order$"))
    app.add_handler(CallbackQueryHandler(view_group_order,    pattern="^group_view_"))
    app.add_handler(CallbackQueryHandler(group_add_items,     pattern="^group_add_items_"))
    app.add_handler(CallbackQueryHandler(group_confirm_order, pattern="^group_confirm_"))
    app.add_handler(CallbackQueryHandler(group_cancel,        pattern="^group_cancel_"))
    # Make sure customer bot does NOT handle staff callbacks
    # (remove any wildcard callback handler if present)
    app.add_handler(CallbackQueryHandler(
        lambda u, c: u.callback_query.answer("❌ This item is currently unavailable.", show_alert=True),
        pattern="^unavailable$"
    ))
    return app

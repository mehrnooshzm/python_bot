import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Temporary storage (use DB for real projects)
registrations = {}


# ---------------- START COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Register / Edit Name", callback_data="register")],
        [InlineKeyboardButton("📋 Show List", callback_data="list")],
    ]

    await update.message.reply_text(
        "🎮 Welcome to Tournament Bot!\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # Register / Edit
    if query.data == "register":
        context.user_data["waiting_for_name"] = True
        await query.message.reply_text("✍️ Send me your name:")

    # Show list
    elif query.data == "list":
        if not registrations:
            await query.message.reply_text("⚠️ No players registered yet.")
        else:
            text = "🏆 Registered Players:\n\n"
            for name in registrations.values():
                text += f"• {name}\n"
            await query.message.reply_text(text)


# ---------------- TEXT HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    # If user is registering
    if context.user_data.get("waiting_for_name"):
        registrations[user_id] = text
        context.user_data["waiting_for_name"] = False

        await update.message.reply_text(f"✅ Saved: {text}")
    else:
        await update.message.reply_text("ℹ️ Press /start to use the bot.")


# ---------------- MAIN ----------------
def main():
    TOKEN = os.getenv("")  # safer than hardcoding

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
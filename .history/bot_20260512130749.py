import os
from dotenv import load_dotenv
import database
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

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
        users = database.get_users()
        print(users)
        if not users:
            await query.message.reply_text("⚠️ No players registered yet.")
        else:
            text = "🏆 Registered Players:\n\n"
            for user in users:
                # user is (id, user_id, username)
                username = user[2]
                text += f"• {username}\n"
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
        database.add_user(user_id, text)

        # Send private message with registered name
        await context.bot.send_message(
            chat_id=user_id, text=f"📝 Your registered name: {text}"
        )
    else:
        await update.message.reply_text("ℹ️ Press /start to use the bot.")


# ---------------- MAIN ----------------
def main():
    # Initialize database table (runs once, IF NOT EXISTS prevents errors)
    database.create_table()
    print('')

    TOKEN = os.getenv("BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

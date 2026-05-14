import os
from dotenv import load_dotenv
import database

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# user_id -> "waiting" OR registered name
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
    chat_type = query.message.chat.type

    # ---------------- REGISTER ----------------
    if query.data == "register":

        # Set waiting state
        registrations[user_id] = "waiting"

        # If already in PV
        if chat_type == "private":
            await query.message.reply_text("✍️ Send me your name:")

        # If inside group
        else:
            await query.message.reply_text("📩 Check your private chat with me.")

            await context.bot.send_message(
                chat_id=user_id,
                text="✍️ Send me your name here to register/edit.",
            )

    # ---------------- SHOW LIST ----------------
    elif query.data == "list":

        users = database.get_users()

        if not users:
            await query.message.reply_text("⚠️ No players registered yet.")

        else:
            text = "🏆 Registered Players:\n\n"

            for user in users:
                # (id, user_id, username)
                username = user[2]
                text += f"• {username}\n"

            await query.message.reply_text(text)


# ---------------- TEXT HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if context.user_data.get("waiting_for_name"):

        try:
            await update.message.delete()
        except:
            pass

        context.user_data["waiting_for_name"] = False

        database.add_user(user_id, text)

        # فقط به خود user پیام بده (private)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Your name saved: {text}"
        )

    else:
        return

# ---------------- MAIN ----------------
def main():

    # Create DB table
    database.create_table()

    print(database.get_users())

    TOKEN = os.getenv("BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("🤖 Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()

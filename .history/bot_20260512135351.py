import os
import asyncio
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

# users waiting to send name
waiting_users = set()


# ---------------- AUTO DELETE ----------------
async def auto_delete(message, delay):

    await asyncio.sleep(delay)

    try:
        await message.delete()
    except:
        pass


# ---------------- START ----------------
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

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(user_id)

        msg = await query.message.reply_text("✍️ Send your name now...")

        # delete bot message after 10 sec
        asyncio.create_task(auto_delete(msg, 10))

    # ---------------- SHOW LIST ----------------
    elif query.data == "list":

        users = database.get_users()

        if not users:

            msg = await query.message.reply_text("⚠️ No players registered yet.")

            asyncio.create_task(auto_delete(msg, 10))

        else:

            text = "🏆 Registered Players:\n\n"

            for user in users:
                username = user[2]
                text += f"• {username}\n"

            msg = await query.message.reply_text(text)

            asyncio.create_task(auto_delete(msg, 20))


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id
    text = update.message.text

    # if waiting for name
    if user_id in waiting_users:

        # save to database
        database.add_user(user_id, text)

        # remove waiting state
        waiting_users.remove(user_id)

        # send confirmation
        confirm = await update.message.reply_text(f"✅ Saved: {text}")

        # delete user message
        try:
            await update.message.delete()
        except:
            pass

        # delete confirmation
        asyncio.create_task(auto_delete(confirm, 5))

    else:
        pass


# ---------------- MAIN ----------------
def main():

    database.create_table()

    TOKEN = os.getenv("BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

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

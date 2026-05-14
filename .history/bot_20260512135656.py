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


# ---------------- BUILD PLAYER LIST ----------------
def build_players_text():

    users = database.get_users()

    if not users:
        return "⚠️ No players registered yet."

    text = "🏆 Registered Players:\n\n"

    for user in users:
        username = user[2]
        text += f"• {username}\n"

    return text


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
    print(query)
    await query.answer()

    user_id = query.from_user.id

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(user_id)

        msg = await query.message.reply_text("✍️ Send your name now...")

        asyncio.create_task(auto_delete(msg, 10))

    # ---------------- SHOW LIST ----------------
    elif query.data == "list":

        msg = await query.message.reply_text(build_players_text())

        asyncio.create_task(auto_delete(msg, 20))


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id
    text = update.message.text

    # only if waiting for name
    if user_id in waiting_users:

        # save/update user in database
        database.add_user(user_id, text)

        # remove waiting state
        waiting_users.remove(user_id)

        # delete user's name message
        try:
            await update.message.delete()
        except:
            pass

        # confirmation message
        confirm = await update.message.reply_text(f"✅ Saved: {text}")

        asyncio.create_task(auto_delete(confirm, 5))

        # send updated list automatically
        players_msg = await update.message.reply_text(build_players_text())

        asyncio.create_task(auto_delete(players_msg, 20))

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

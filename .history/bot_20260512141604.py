import os
import asyncio
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

waiting_users = set()


# ---------------- AUTO DELETE ----------------
async def auto_delete(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print("delete error:", e)


# ---------------- BUILD LIST ----------------
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
    await query.answer()

    user_id = query.from_user.id

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(user_id)

        msg = await query.message.reply_text("✍️ Send your name now...")
        asyncio.create_task(auto_delete(msg, 10))

    # ---------------- LIST ----------------
    elif query.data == "list":

        msg = await query.message.reply_text(build_players_text())


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    text = update.message.text

    # only if user is registering
    if user_id in waiting_users:

        database.add_user(user_id, text)
        waiting_users.remove(user_id)

        # delete user message (if allowed)
        try:
            await update.message.delete()
        except Exception as e:
            print("delete error:", e)

        # confirmation
        confirm = await update.message.reply_text(f"✅ Saved: {text}")
        asyncio.create_task(auto_delete(confirm, 5))

        # send updated list
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=build_players_text()
        )

    else:
        await update.message.reply_text("ℹ️ Press /start to use the bot.")


# ---------------- MAIN ----------------
def main():

    database.create_table()

    TOKEN = os.getenv("BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

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
mode = {}  # add / edit


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
        text += f"• {user[2]}\n"

    return text


# ---------------- LIST BUTTONS ----------------
def build_players_markup():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add Name", callback_data="add_name")],
            [InlineKeyboardButton("✏️ Edit Name", callback_data="edit_name")],
        ]
    )


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [[InlineKeyboardButton("📝 Register / Edit Name", callback_data="list")]]

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

    # ---------------- SHOW LIST ----------------
    if query.data == "list":

        await query.message.reply_text(
            build_players_text(), reply_markup=build_players_markup()
        )

    # ---------------- ADD ----------------
    elif query.data == "add_name":

        waiting_users.add(user_id)
        mode[user_id] = "add"

        msg = await query.message.reply_text("✍️ Send your name to add...")
        asyncio.create_task(auto_delete(msg, 10))

    # ---------------- EDIT ----------------
    elif query.data == "edit_name":

        waiting_users.add(user_id)
        mode[user_id] = "edit"

        msg = await query.message.reply_text("✏️ Send your new name...")
        asyncio.create_task(auto_delete(msg, 10))


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    text = update.message.text

    if user_id in waiting_users:

        action = mode.get(user_id, "add")

        # save/update
        database.add_user(user_id, text)

        waiting_users.remove(user_id)
        mode.pop(user_id, None)

        # delete user message
        try:
            await update.message.delete()
        except Exception as e:
            print("delete error:", e)

        # confirm
        confirm = await update.message.reply_text(f"✅ Saved: {text}")
        asyncio.create_task(auto_delete(confirm, 5))

        # send updated list
        await update.message.reply_text(build_players_text())

    else:
        # فقط تو private پیام بده
        if update.effective_chat.type == "private":
            await update.message.reply_text("ℹ️ Press /start")


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

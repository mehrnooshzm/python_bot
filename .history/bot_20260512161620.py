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
waiting_jobs = {}  # ✅ ADD


# ---------------- AUTO DELETE ----------------
async def auto_delete(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print("delete error:", e)


# ---------------- TIMEOUT FUNCTION (NEW) ----------------
async def timeout_user(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    chat_id = context.job.data["chat_id"]
    msg_id = context.job.data["msg_id"]

    if user_id in waiting_users:
        waiting_users.remove(user_id)

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass

        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ زمان تمام شد! دوباره باید روی Register بزنی."
        )


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


def build_players_markup():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add Name", callback_data="add_name")],
            [InlineKeyboardButton("✏️ Edit Name", callback_data="edit_name")],
        ]
    )


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

        msg = await query.message.reply_text("✍️ Send your name now... (2 min)")

       
        if user_id in waiting_jobs:
            waiting_jobs[user_id].schedule_removal()

        job = context.job_queue.run_once(
            timeout_user,
            when=120,  # 2 minutes
            data={
                "user_id": user_id,
                "chat_id": query.message.chat_id,
                "msg_id": msg.message_id,
            }
        )

        waiting_jobs[user_id] = job

    # ---------------- LIST ----------------
    elif query.data == "list":

        await query.message.edit_text(
            build_players_text(),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📝 Register / Edit Name", callback_data="register"
                        )
                    ],
                ]
            ),
        )


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    text = update.message.text

    if user_id in waiting_users:

        # ❌ cancel timeout job
        if user_id in waiting_jobs:
            waiting_jobs[user_id].schedule_removal()
            del waiting_jobs[user_id]

        database.add_user(user_id, text)
        waiting_users.remove(user_id)

        try:
            await update.message.delete()
        except Exception as e:
            print("delete error:", e)

        confirm = await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"✅ Saved: {text}"
        )
        asyncio.create_task(auto_delete(confirm, 5))

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=build_players_text(),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📝 Register / Edit Name", callback_data="register"
                        )
                    ],
                ]
            ),
        )

    else:
        if update.effective_chat.type == "private":
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="ℹ️ Press /start"
            )


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
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

ADMIN_IDS = [70991185]

waiting_users = set()
waiting_jobs = {}

waiting_edit = {}
waiting_setup = set()

waiting_temp_messages = {}
waiting_register_messages = {}
waiting_edit_messages = {}


# ---------------- AUTO DELETE ----------------
async def auto_delete_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.data["chat_id"]
    message_id = job.data["message_id"]

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print("delete error:", e)


def schedule_delete(context, chat_id, message_id, seconds):
    context.job_queue.run_once(
        auto_delete_job,
        when=seconds,
        data={"chat_id": chat_id, "message_id": message_id},
    )


# ---------------- TIMEOUT ----------------
async def timeout_user(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    chat_id = context.job.data["chat_id"]

    if user_id in waiting_users:
        waiting_users.remove(user_id)

        if user_id in waiting_register_messages:
            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=waiting_register_messages[user_id]
                )
            except:
                pass
            del waiting_register_messages[user_id]


# ---------------- BUILD UI ----------------
def build_players_text(viewer_id, is_admin=False):

    users = database.get_users()

    if not users:
        keyboard = [[InlineKeyboardButton("📝 Register", callback_data="register")]]
        print(is_admin)
        if is_admin:
            keyboard.append(
                [InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")]
            )

        return "⚠️ No players registered yet.", InlineKeyboardMarkup(keyboard)

    name = database.get_value("tournament_name") or "Tournament"

    text = f"🏆 {name}:\n\n"
    keyboard = []

    for index, user in enumerate(users):
        row_id = user[0]
        user_id = int(user[1])
        username = user[2]

        text += f"{index + 1} - {username}\n"

        # فقط مالک دیتا
        if user_id == viewer_id:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✏️ {username}", callback_data=f"edit_{row_id}"
                    ),
                    InlineKeyboardButton("❌", callback_data=f"delete_{row_id}"),
                ]
            )

    keyboard.append([InlineKeyboardButton("📝 Register", callback_data="register")])

    if is_admin:
        keyboard.append(
            [InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")]
        )

    return text, InlineKeyboardMarkup(keyboard)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    viewer_id = update.effective_user.id
    is_admin = viewer_id in ADMIN_IDS

    text, markup = build_players_text(viewer_id, is_admin)

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="♟️ Welcome to Chess Tournament!",
        reply_markup=markup,
    )

    schedule_delete(context, update.effective_chat.id, msg.message_id, 120)


# ---------------- CALLBACK ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    viewer_id = query.from_user.id
    chat_id = query.message.chat.id
    is_admin = viewer_id in ADMIN_IDS

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(viewer_id)

        msg = await context.bot.send_message(
            chat_id=chat_id, text="✍️ Send name now..."
        )
        waiting_register_messages[viewer_id] = msg.message_id

        schedule_delete(context, chat_id, msg.message_id, 60)

        context.job_queue.run_once(
            timeout_user,
            when=60,
            data={"user_id": viewer_id, "chat_id": chat_id},
        )

    # ---------------- LIST ----------------
    elif query.data == "list":

        text, markup = build_players_text(viewer_id, is_admin)

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=markup,
        )

    # ---------------- DELETE ----------------
    elif query.data.startswith("delete_"):

        row_id = int(query.data.split("_")[1])

        # 🔥 SECURITY CHECK
        row = database.get_user(row_id)
        if row[1] != viewer_id and not is_admin:
            await query.answer("⛔ Not allowed", show_alert=True)
            return

        database.delete_name(row_id)

        text, markup = build_players_text(viewer_id, is_admin)

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=markup,
        )

    # ---------------- EDIT ----------------
    elif query.data.startswith("edit_"):

        row_id = int(query.data.split("_")[1])

        row = database.get_user(row_id)
        if row[1] != viewer_id:
            await query.answer("⛔ Not your data", show_alert=True)
            return

        waiting_edit[viewer_id] = row_id

        msg = await context.bot.send_message(
            chat_id=chat_id, text="✏️ Send new name..."
        )
        waiting_edit_messages[viewer_id] = msg.message_id

        schedule_delete(context, chat_id, msg.message_id, 60)

    # ---------------- SETUP ----------------
    elif query.data == "setup":

        if not is_admin:
            await context.bot.send_message(chat_id=chat_id, text="⛔ Not admin")
            return

        waiting_setup.add(viewer_id)

        await context.bot.send_message(chat_id=chat_id, text="📌 Send tournament name")


# ---------------- MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    text = update.message.text
    chat_id = update.effective_chat.id

    # ---------------- SETUP ----------------
    if user_id in waiting_setup:

        database.set_value("tournament_name", text.strip())
        waiting_setup.remove(user_id)

        await update.message.delete()

        await context.bot.send_message(chat_id=chat_id, text="✅ Tournament saved!")
        return

    # ---------------- EDIT ----------------
    if user_id in waiting_edit:

        row_id = waiting_edit[user_id]
        del waiting_edit[user_id]

        database.update_name(row_id, text)

        await update.message.delete()

        await context.bot.send_message(chat_id=chat_id, text="✅ Updated!")

        is_admin = user_id in ADMIN_IDS
        text, markup = build_players_text(user_id, is_admin)

        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        return

    # ---------------- REGISTER ----------------
    if user_id in waiting_users:

        database.add_user(user_id, text)
        waiting_users.remove(user_id)

        await update.message.delete()

        await context.bot.send_message(chat_id=chat_id, text=f"✅ Saved: {text}")

        is_admin = user_id in ADMIN_IDS
        text, markup = build_players_text(user_id, is_admin)

        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
        return


# ---------------- MAIN ----------------
def main():

    database.create_table()
    database.create_settings_table()

    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

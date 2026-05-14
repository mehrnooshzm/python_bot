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

# NEW
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

        # delete register prompt
        if user_id in waiting_register_messages:

            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=waiting_register_messages[user_id]
                )
            except:
                pass

            del waiting_register_messages[user_id]

        msg = await context.bot.send_message(
            chat_id=chat_id, text="⏰ Time is finished. press Register again"
        )

        schedule_delete(context, chat_id, msg.message_id, 8)


# ---------------- BUILD LIST ----------------
def build_players_text():

    users = database.get_users()

    if not users:

        return (
            "⚠️ No players registered yet.",
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("📝 Register", callback_data="register")]]
            ),
        )

    name = database.get_value("tournament_name") or "Tournament"

    text = f"🏆 {name}:\n\n"

    keyboard = []

    for index, user in enumerate(users):

        row_id = user[0]
        username = user[2]

        text += f"{index + 1} - {username}\n"

        keyboard.append(
            [
                InlineKeyboardButton(f"✏️ {username}", callback_data=f"edit_{row_id}"),
                InlineKeyboardButton("❌", callback_data=f"delete_{row_id}"),
            ]
        )

    keyboard.append([InlineKeyboardButton("📝 Register", callback_data="register")])

    return text, InlineKeyboardMarkup(keyboard)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("📝 Register / Add Name", callback_data="register")],
        [InlineKeyboardButton("📋 Show List", callback_data="list")],
    ]

    if update.effective_user.id in ADMIN_IDS:

        keyboard.append(
            [InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")]
        )

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🎮 Welcome!",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    schedule_delete(context, update.effective_chat.id, msg.message_id, 120)


# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(user_id)

        msg = await context.bot.send_message(
            chat_id=chat_id, text="✍️ Send name now... (1 min)"
        )

        waiting_register_messages[user_id] = msg.message_id

        schedule_delete(context, chat_id, msg.message_id, 60)

        job = context.job_queue.run_once(
            timeout_user,
            when=60,
            data={"user_id": user_id, "chat_id": chat_id},
        )

        waiting_jobs[user_id] = job

    # ---------------- LIST ----------------
    elif query.data == "list":

        text, markup = build_players_text()

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=markup,
        )

        schedule_delete(context, chat_id, query.message.message_id, 120)

    # ---------------- DELETE ----------------
    elif query.data.startswith("delete_"):

        row_id = int(query.data.split("_")[1])

        database.delete_name(row_id)

        text, markup = build_players_text()

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=markup,
        )

        schedule_delete(context, chat_id, query.message.message_id, 120)

    # ---------------- EDIT ----------------
    elif query.data.startswith("edit_"):

        row_id = int(query.data.split("_")[1])

        waiting_edit[user_id] = row_id

        msg = await context.bot.send_message(
            chat_id=chat_id, text="✏️ Send new name..."
        )

        waiting_edit_messages[user_id] = msg.message_id

        schedule_delete(context, chat_id, msg.message_id, 60)

    # ---------------- SETUP ----------------
    elif query.data == "setup":

        if user_id not in ADMIN_IDS:

            msg = await context.bot.send_message(
                chat_id=chat_id, text="⛔ You are not admin"
            )

            schedule_delete(context, chat_id, msg.message_id, 5)

            return

        waiting_setup.add(user_id)

        msg = await context.bot.send_message(
            chat_id=chat_id, text="📌 Send tournament name"
        )

        waiting_temp_messages[user_id] = msg.message_id

        schedule_delete(context, chat_id, msg.message_id, 60)


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    text = update.message.text
    chat_id = update.effective_chat.id

    # ---------------- SETUP MODE ----------------
    if user_id in waiting_setup:

        try:

            database.set_value("tournament_name", text.strip())

            waiting_setup.remove(user_id)

            # delete user message
            try:
                await update.message.delete()
            except:
                pass

            # delete setup prompt
            if user_id in waiting_temp_messages:

                try:
                    await context.bot.delete_message(
                        chat_id=chat_id, message_id=waiting_temp_messages[user_id]
                    )
                except:
                    pass

                del waiting_temp_messages[user_id]

            msg = await context.bot.send_message(
                chat_id=chat_id, text="✅ Tournament saved!"
            )

            schedule_delete(context, chat_id, msg.message_id, 5)

        except:

            msg = await context.bot.send_message(
                chat_id=chat_id, text="❌ Error saving tournament"
            )

            schedule_delete(context, chat_id, msg.message_id, 5)

        return

    # ---------------- EDIT MODE ----------------
    if user_id in waiting_edit:

        row_id = waiting_edit[user_id]

        del waiting_edit[user_id]

        database.update_name(row_id, text)

        # delete user message
        try:
            await update.message.delete()
        except:
            pass

        # delete edit prompt
        if user_id in waiting_edit_messages:

            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=waiting_edit_messages[user_id]
                )
            except:
                pass

            del waiting_edit_messages[user_id]

        msg = await context.bot.send_message(chat_id=chat_id, text="✅ Updated!")

        schedule_delete(context, chat_id, msg.message_id, 5)

        text, markup = build_players_text()

        list_msg = await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=markup
        )

        schedule_delete(context, chat_id, list_msg.message_id, 120)

        return

    # ---------------- REGISTER MODE ----------------
    if user_id in waiting_users:

        if user_id in waiting_jobs:

            waiting_jobs[user_id].schedule_removal()

            del waiting_jobs[user_id]

        database.add_user(user_id, text)

        waiting_users.remove(user_id)

        # delete user message
        try:
            await update.message.delete()
        except:
            pass

        # delete register prompt
        if user_id in waiting_register_messages:

            try:
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=waiting_register_messages[user_id]
                )
            except:
                pass

            del waiting_register_messages[user_id]

        msg = await context.bot.send_message(chat_id=chat_id, text=f"✅ Saved: {text}")

        schedule_delete(context, chat_id, msg.message_id, 5)

        text, markup = build_players_text()

        list_msg = await context.bot.send_message(
            chat_id=chat_id, text=text, reply_markup=markup
        )

        schedule_delete(context, chat_id, list_msg.message_id, 120)

    else:

        if update.effective_chat.type == "private":

            msg = await context.bot.send_message(
                chat_id=chat_id, text="ℹ️ Press /start"
            )

            schedule_delete(context, chat_id, msg.message_id, 5)


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

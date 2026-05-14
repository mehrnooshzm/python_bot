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

        msg = await context.bot.send_message(
            chat_id=chat_id, text="⏰ Time is finished. press Register again"
        )
        schedule_delete(context, chat_id, msg.message_id, 8)


# ---------------- BUILD LIST ----------------
def build_players_text():
    """Builds a clean group list with NO personal edit/delete buttons."""
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

    for index, user in enumerate(users):
        username = user[2]
        text += f"{index + 1} - {username}\n"

    # Group buttons: Everyone sees the same dynamic options
    keyboard = [
        [
            InlineKeyboardButton("📝 Register", callback_data="register"),
            InlineKeyboardButton("⚙️ Manage My Entry", callback_data="manage_entry"),
        ]
    ]

    return text, InlineKeyboardMarkup(keyboard)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Register / Add Name", callback_data="register")],
        [InlineKeyboardButton("📋 Show List", callback_data="list")],
    ]

    if (
        update.effective_chat.type == "private"
        and update.effective_user.id in ADMIN_IDS
    ):
        keyboard.append(
            [InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")]
        )

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="♟️ Welcome to Chess Tournament!",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    schedule_delete(context, update.effective_chat.id, msg.message_id, 120)


# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id

    # ---------------- REGISTER ----------------
    if query.data == "register":
        await query.answer()
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
        await query.answer()
        text, markup = build_players_text()

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=markup,
        )
        schedule_delete(context, chat_id, query.message.message_id, 120)

    # ---------------- MANAGE ENTRY (NEW) ----------------
    elif query.data == "manage_entry":
        # Find this user's specific registration entry row
        users = database.get_users()
        user_row = None
        for u in users:
            if u[1] == user_id:
                user_row = u
                break

        if not user_row:
            await query.answer(
                text="❌ You are not registered in this tournament!", show_alert=True
            )
            return

        row_id = user_row[0]

        # Open a private URL link to the bot or redirect them safely
        # Alternatively, we change the group view into a short temporary menu just for them
        keyboard = [
            [
                InlineKeyboardButton("✏️ Edit My Name", callback_data=f"edit_{row_id}"),
                InlineKeyboardButton("❌ Delete Me", callback_data=f"delete_{row_id}"),
            ],
            [InlineKeyboardButton("🔙 Back to List", callback_data="list")],
        ]

        await query.edit_message_text(
            text=f"🛠️ **Management Menu**\nLogged in as: {query.from_user.first_name}\nChoose an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    # ---------------- DELETE ----------------
    elif query.data.startswith("delete_"):
        row_id = int(query.data.split("_")[1])
        database.delete_name(row_id)
        await query.answer(text="✅ Registration deleted!")

        text, markup = build_players_text()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=query.message.message_id,
            text=text,
            reply_markup=markup,
        )

    # ---------------- EDIT ----------------
    elif query.data.startswith("edit_"):
        row_id = int(query.data.split("_")[1])
        await query.answer()
        waiting_edit[user_id] = row_id

        msg = await context.bot.send_message(
            chat_id=chat_id, text="✏️ Send new name..."
        )
        waiting_edit_messages[user_id] = msg.message_id
        schedule_delete(context, chat_id, msg.message_id, 60)

    # ---------------- SETUP ----------------
    elif query.data == "setup":
        await query.answer()
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
            try:
                await update.message.delete()
            except:
                pass

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
        try:
            await update.message.delete()
        except:
            pass

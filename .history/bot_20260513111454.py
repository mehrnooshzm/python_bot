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
waiting_edit = {}
waiting_setup = set()

# Tracks all group chats where the bot is active
known_groups = set()


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


# -----------------------------------------------
# BUILD LIST — group version (plain text only)
# -----------------------------------------------
def build_group_list_text():

    users = database.get_users()
    name = database.get_value("tournament_name") or "Tournament"

    if not users:
        return "⚠️ No players registered yet."

    text = f"🏆 {name}:\n\n"
    for index, user in enumerate(users):
        username = user[2]
        text += f"{index + 1} - {username}\n"

    return text


# -----------------------------------------------
# BUILD LIST — PV version (with edit/delete for own entry)
# -----------------------------------------------
def build_pv_list(current_user_id):

    users = database.get_users()
    name = database.get_value("tournament_name") or "Tournament"

    if not users:
        return (
            "⚠️ No players registered yet.",
            InlineKeyboardMarkup(
                [[InlineKeyboardButton("📝 Register", callback_data="register")]]
            ),
        )

    text = f"🏆 {name}:\n\n"
    keyboard = []

    for index, user in enumerate(users):
        row_id = user[0]
        user_id = user[1]
        username = user[2]

        text += f"{index + 1} - {username}\n"

        if user_id == current_user_id:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✏️ Edit: {username}", callback_data=f"edit_{row_id}"
                    ),
                    InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{row_id}"),
                ]
            )

    keyboard.append([InlineKeyboardButton("📝 Register", callback_data="register")])

    return text, InlineKeyboardMarkup(keyboard)


# -----------------------------------------------
# Send updated list to group
# -----------------------------------------------
async def post_group_list(context):
    """Send updated list to ALL known group chats."""
    group_text = build_group_list_text()
    group_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📝 Register", callback_data="register"),
                InlineKeyboardButton("✏️ Edit", callback_data="edit_menu"),
            ]
        ]
    )
    for group_id in known_groups:
        try:
            await context.bot.send_message(
                chat_id=group_id,
                text=group_text,
                reply_markup=group_keyboard,
            )
        except Exception as e:
            print(f"Failed to send list to group {group_id}:", e)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    is_private = update.effective_chat.type == "private"
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "Player"

    keyboard = [
        [InlineKeyboardButton("📝 Register / Add Name", callback_data="register")],
        [InlineKeyboardButton("📋 Show List", callback_data="list")],
    ]

    if is_private and user_id in ADMIN_IDS:
        keyboard.append(
            [InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")]
        )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"♟️ Welcome, {first_name}! \nWelcome to Chess Tournament!",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    first_name = query.from_user.first_name or "Player"
    chat_id = query.message.chat.id
    is_private = query.message.chat.type == "private"

    # Remember every group this bot is used in
    if not is_private:
        known_groups.add(chat_id)

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(user_id)

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="✍️ Please send me your name:",
            )
        except Exception:
            waiting_users.discard(user_id)
            err = await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⚠️ {first_name}, I can't send you a private message.\n"
                    f"Please start me in private first: @{context.bot.username}"
                ),
            )
            schedule_delete(context, chat_id, err.message_id, 60)

    # ---------------- LIST ----------------
    elif query.data == "list":

        text = build_group_list_text()

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📝 Register", callback_data="register"),
                    InlineKeyboardButton("✏️ Edit", callback_data="edit_menu"),
                ]
            ]
        )

        # Delete the original start message (which has a delete timer on it)
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=query.message.message_id,
            )
        except Exception:
            pass

        # Send a fresh list message with NO auto-delete timer (stays permanently)
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
        )

    # ---------------- EDIT MENU ----------------
    elif query.data == "edit_menu":

        try:
            pv_text, pv_markup = build_pv_list(user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=pv_text,
                reply_markup=pv_markup,
            )
        except Exception:
            err = await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⚠️ {first_name}, I can't send you a private message.\n"
                    f"Please start me in private first: @{context.bot.username}"
                ),
            )
            schedule_delete(context, chat_id, err.message_id, 60)

    # ---------------- DELETE (PV only) ----------------
    elif query.data.startswith("delete_"):

        if not is_private:
            await query.answer("⚠️ Please use this in private chat.", show_alert=True)
            return

        row_id = int(query.data.split("_")[1])
        database.delete_name(row_id)

        pv_text, pv_markup = build_pv_list(user_id)

        await context.bot.edit_message_text(
            chat_id=user_id,
            message_id=query.message.message_id,
            text="✅ Deleted!\n\n" + pv_text,
            reply_markup=pv_markup,
        )

        # Send updated list to all groups
        await post_group_list(context)

    # ---------------- EDIT (PV only) ----------------
    elif query.data.startswith("edit_"):

        if not is_private:
            await query.answer("⚠️ Please use this in private chat.", show_alert=True)
            return

        row_id = int(query.data.split("_")[1])
        waiting_edit[user_id] = row_id

        await context.bot.send_message(
            chat_id=user_id,
            text="✏️ Please send me your new name:",
        )

    # ---------------- SETUP ----------------
    elif query.data == "setup":

        if user_id not in ADMIN_IDS:
            await context.bot.send_message(chat_id=chat_id, text="⛔ You are not admin")
            return

        waiting_setup.add(user_id)

        await context.bot.send_message(chat_id=chat_id, text="📌 Send tournament name")


# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    msg_text = update.message.text
    chat_id = update.effective_chat.id

    # ---------------- SETUP MODE ----------------
    if user_id in waiting_setup:

        try:
            database.set_value("tournament_name", msg_text.strip())
            waiting_setup.remove(user_id)
            await context.bot.send_message(chat_id=chat_id, text="✅ Tournament saved!")
        except:
            await context.bot.send_message(
                chat_id=chat_id, text="❌ Error saving tournament"
            )

        return

    # All register/edit interactions only in private chat
    if update.effective_chat.type != "private":
        return

    # ---------------- EDIT MODE (PV) ----------------
    if user_id in waiting_edit:

        row_id = waiting_edit.pop(user_id)
        database.update_name(row_id, msg_text.strip())

        await context.bot.send_message(chat_id=user_id, text="✅ Name updated!")

        pv_text, pv_markup = build_pv_list(user_id)
        await context.bot.send_message(
            chat_id=user_id, text=pv_text, reply_markup=pv_markup
        )

        # Send updated list to all groups
        await post_group_list(context)

        return

    # ---------------- REGISTER MODE (PV) ----------------
    if user_id in waiting_users:

        database.add_user(user_id, msg_text.strip())
        waiting_users.remove(user_id)

        await context.bot.send_message(
            chat_id=user_id, text=f"✅ Registered as: {msg_text.strip()}"
        )

        pv_text, pv_markup = build_pv_list(user_id)
        await context.bot.send_message(
            chat_id=user_id, text=pv_text, reply_markup=pv_markup
        )

        # Send updated list to all groups
        await post_group_list(context)

    else:
        await context.bot.send_message(chat_id=chat_id, text="ℹ️ Press /start")


# ---------------- MAIN ----------------
def main():

    database.create_table()
    database.create_settings_table()

    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot running...")
    print(__name__)
    app.run_polling()


if __name__ == "__main__":
    main()

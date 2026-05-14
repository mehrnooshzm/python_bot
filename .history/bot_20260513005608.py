import os
from dotenv import load_dotenv
import database

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

load_dotenv()

ADMIN_IDS = [70991185]

# ---------------- STATE ----------------
waiting_users = set()
waiting_edit = {}
waiting_setup = set()


# ---------------- BUILD UI ----------------
def build_players_text(viewer_id, is_admin=False):

    users = database.get_users()

    if not users:
        keyboard = [[InlineKeyboardButton("📝 Register", callback_data="register")]]

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
    chat_id = update.effective_chat.id

    text, markup = build_players_text(viewer_id, is_admin)

    await context.bot.send_message(
        chat_id=chat_id,
        text="♟️ Welcome to Chess Tournament!",
        reply_markup=markup,
    )


# ---------------- CALLBACK ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    viewer_id = query.from_user.id
    chat_id = query.message.chat.id
    is_admin = viewer_id in ADMIN_IDS

    # ---------------- REGISTER ----------------
    if query.data == "register":
        waiting_users.add((chat_id, viewer_id))
        await context.bot.send_message(chat_id=chat_id, text="✍️ Send name now...")

    # ---------------- LIST ----------------
    elif query.data == "list":
        text, markup = build_players_text(viewer_id, is_admin)
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)

    # ---------------- DELETE ----------------
    elif query.data.startswith("delete_"):

        row_id = int(query.data.split("_")[1])

        row = database.get_user(row_id)
        if row[1] != viewer_id and not is_admin:
            await query.answer("⛔ Not allowed", show_alert=True)
            return

        database.delete_name(row_id)

        text, markup = build_players_text(viewer_id, is_admin)
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)

    # ---------------- EDIT ----------------
    elif query.data.startswith("edit_"):

        row_id = int(query.data.split("_")[1])

        row = database.get_user(row_id)
        if row[1] != viewer_id:
            await query.answer("⛔ Not your data", show_alert=True)
            return

        waiting_edit[(chat_id, viewer_id)] = row_id
        await context.bot.send_message(chat_id=chat_id, text="✏️ Send new name...")

    # ---------------- SETUP ----------------
    elif query.data == "setup":

        if not is_admin:
            await context.bot.send_message(chat_id=chat_id, text="⛔ Not admin")
            return

        waiting_setup.add((chat_id, viewer_id))
        await context.bot.send_message(chat_id=chat_id, text="📌 Send tournament name")


# ---------------- MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    text = update.message.text

    key = (chat_id, user_id)

    # ---------------- SETUP ----------------
    if key in waiting_setup:

        database.set_value("tournament_name", text.strip())
        waiting_setup.remove(key)

        await update.message.delete()
        await context.bot.send_message(chat_id=chat_id, text="✅ Tournament saved!")
        return

    # ---------------- EDIT ----------------
    if key in waiting_edit:

        row_id = waiting_edit[key]
        del waiting_edit[key]

        database.update_name(row_id, text)

        await update.message.delete()
        await context.bot.send_message(chat_id=chat_id, text="✅ Updated!")
        return

    # ---------------- REGISTER ----------------
    if key in waiting_users:

        database.add_user(user_id, text)
        waiting_users.remove(key)

        await update.message.delete()
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Saved: {text}")
        return


# ---------------- SILENT JOIN DETECTOR ----------------
async def detect_user_join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_member = update.chat_member

    # 🔥 SAFE CHECK (خیلی مهم)
    if not chat_member:
        return

    new_member = chat_member.new_chat_member

    if not new_member:
        return

    # فقط وقتی status معتبر داریم
    if new_member.status in ["member", "administrator"]:

        user_id = new_member.user.id
        chat_id = update.effective_chat.id

        print(f"JOIN -> user_id={user_id}, chat_id={chat_id}")

        database.add_active_user(user_id, chat_id)


# ---------------- MAIN ----------------
def main():

    database.create_table()
    database.create_settings_table()

    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 🔥 JOIN DETECTOR
    app.add_handler(ChatMemberHandler(detect_user_join))

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

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

# ---------------- STATE (FIXED) ----------------
waiting_users = set()   # (chat_id, user_id)
waiting_edit = {}       # (chat_id, user_id) -> row_id
waiting_setup = set()   # (chat_id, user_id)


# ---------------- BUILD UI ----------------
def build_players_text(viewer_id, is_admin=False):

    users = database.get_users()

    if not users:
        keyboard = [[InlineKeyboardButton("📝 Register", callback_data="register")]]

        if is_admin:
            keyboard.append([InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")])

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
            keyboard.append([
                InlineKeyboardButton(f"✏️ {username}", callback_data=f"edit_{row_id}"),
                InlineKeyboardButton("❌", callback_data=f"delete_{row_id}")
            ])

    keyboard.append([InlineKeyboardButton("📝 Register", callback_data="register")])

    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Setup Tournament", callback_data="setup")])

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

    key = (chat_id, viewer_id)

    # ---------------- REGISTER ----------------
    if query.data == "register":

        waiting_users.add(key)

        await context.bot.send_message(
            chat_id=chat_id,
            text="✍️ Send name now..."
        )

    # ---------------- LIST ----------------
    elif query.data == "list":

        text, markup = build_players_text(viewer_id, is_admin)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
        )

    # ---------------- DELETE ----------------
    elif query.data.startswith("delete_"):

        row_id = int(query.data.split("_")[1])

        row = database.get_user(row_id)
        if row[1] != viewer_id and not is_admin:
            await query.answer("⛔ Not allowed", show_alert=True)
            return

        database.delete_name(row_id)

        text, markup = build_players_text(viewer_id, is_admin)

        await context.bot.send_message(
            chat_id=chat_id,
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

        waiting_edit[key] = row_id

        await context.bot.send_message(
            chat_id=chat_id,
            text="✏️ Send new name..."
        )

    # ---------------- SETUP ----------------
    elif query.data == "setup":

        if not is_admin:
            await context.bot.send_message(chat_id=chat_id, text="⛔ Not admin")
            return

        waiting_setup.add(key)

        await context.bot.send_message(
            chat_id=chat_id,
            text="📌 Send tournament name"
        )


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
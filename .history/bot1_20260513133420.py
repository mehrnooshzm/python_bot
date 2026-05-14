from dotenv import load_dotenv
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from bot import button_handler

load_dotenv()
waiting

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_private = update.effective_chat.type == "private"
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or "Player"
    keyboards = [
        [InlineKeyboardButton("Register", callback_data="register")],
        [InlineKeyboardButton("Show Player List", callback_data="list")],
    ]

    if is_private and user_id in [os.getenv("ADMIN_IDS")]:
        keyboards.append([InlineKeyboardButton("Setup", callback_data="setup")])
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"♟️ Welcome, {first_name}! \nWelcome to Chess Tournament!",
        reply_markup=InlineKeyboardMarkup(keyboards),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query()
    await query.answer()
    user_id = query.from_user.id
    first_name = query.from_user.first_name or "Player"
    chat_id = query.message.chat.id
    is_private = query.message.chat.type == "private"

# Register
    if query.data=='register':
        print ('meh')



def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

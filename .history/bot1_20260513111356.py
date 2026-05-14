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

load_dotenv()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_private=update.effective_chat.type='private'
    user = update.effective_user
    print(update)
    print(context)


def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

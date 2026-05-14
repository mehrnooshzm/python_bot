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



def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    print("🤖 Bot running...")
    app.run_polling()
    
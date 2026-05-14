
from telegram.ext import (
   
    ContextTypes,
  
)

async def auto_delete_job(context=ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.de




def schedule_delete(context,chat_id,message_id,seconds):
    context.job_queue.run_once(auto_delete_job,when=seconds,data={"chat_id": chat_id, "message_id": message_id})

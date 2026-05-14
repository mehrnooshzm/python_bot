from telegram.ext import (
    ContextTypes,
)

import database


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

def build_group_list_text():
    users=database.get_users()
    
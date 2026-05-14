

from bot import auto_delete_job


def schedule_delete(context,chat_id,message_id,seconds):
    context.job_queue.run_once(auto_delete_job,)

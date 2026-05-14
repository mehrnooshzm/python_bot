

def schedule_delete(context,chat_id,message_id,seconds):
    context.job_queue.run_once()

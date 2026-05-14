

async def auto_delete_job(context):



def schedule_delete(context,chat_id,message_id,seconds):
    context.job_queue.run_once(auto_delete_job,when=seconds,data={"chat_id": chat_id, "message_id": message_id})

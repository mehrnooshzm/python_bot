async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    viewer_id = update.effective_user.id
    is_admin = viewer_id in ADMIN_IDS

    text, markup = build_players_text(viewer_id, is_admin)

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="♟️ Welcome to Chess Tournament!",
        reply_markup=markup,
    )

    schedule_delete(context, update.effective_chat.id, msg.message_id, 120)
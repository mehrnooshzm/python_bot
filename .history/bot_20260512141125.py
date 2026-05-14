async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id
    text = update.message.text

    if user_id in waiting_users:

        database.add_user(user_id, text)
        waiting_users.remove(user_id)

        try:
            await update.message.delete()
        except Exception as e:
            print("delete error:", e)

        await update.message.reply_text(f"✅ Saved: {text}")

        # 🔥 IMPORTANT: force send list AFTER save
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=build_players_text()
        )

    else:
        await update.message.reply_text("ℹ️ Press /start")
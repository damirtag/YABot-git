from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.dispatcher.flags import get_flag

from database.repo import DB_actions

db = DB_actions()


class HandlerMiddleware(BaseMiddleware):
    """
    Reads handler flags:
        feature: bot_settings column (e.g. "roll_disabled"); if set for the chat, the
                 handler is skipped and the event falls through to the next handler.
        log:     command name written to the `commands` table, only after the handler
                 finished without raising and without returning False.
    """

    async def __call__(self, handler, event, data):
        chat = data.get("event_chat")
        feature = get_flag(data, "feature")
        if feature and chat and db.get_setting(chat.id, feature):
            raise SkipHandler

        result = await handler(event, data)

        command = get_flag(data, "log")
        user = data.get("event_from_user")
        if command and user and result is not False:
            db.add_user(user.id, user.username, user.first_name, user.last_name)
            if chat and chat.type != "private":
                db.add_chat(chat.id)
            db.log_command(user.id, command)

        return result

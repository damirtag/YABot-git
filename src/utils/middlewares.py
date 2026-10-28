import math
import time

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.dispatcher.flags import get_flag

from config import logger
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
            db.log_command(user.id, command)

        return result


class MemberTrackerMiddleware(BaseMiddleware):
    """
    Outer message middleware: records which users were seen in which groups
    (`chats` + `chat_members`). Each (chat, user) pair is written at most once per
    `interval` seconds; a failed write is retried on the next message.
    """

    def __init__(self, interval: float = 3600):
        self.interval = interval
        # ponytail: grows with distinct (chat, user) pairs; swap for a TTLCache if that gets big
        self.written_at: dict[tuple[int, int], float] = {}

    async def __call__(self, handler, event, data):
        chat = data.get("event_chat")
        user = data.get("event_from_user")
        if chat and user and chat.type in ("group", "supergroup") and not user.is_bot:
            key = (chat.id, user.id)
            now = time.monotonic()
            if now - self.written_at.get(key, -math.inf) >= self.interval:
                try:
                    db.track_member(chat.id, chat.title, user.id)
                    self.written_at[key] = now
                except Exception:
                    logger.exception("Failed to track chat member %s", key)

        return await handler(event, data)

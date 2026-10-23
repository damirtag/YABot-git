from aiogram import Dispatcher

from utils.middlewares import HandlerMiddleware

from . import admin, callbacks, commands, common, inline, jokes, media, voice


def setup_routers(dp: Dispatcher):
    """Set up all handlers."""
    middleware = HandlerMiddleware()
    for observer in (dp.message, dp.callback_query, dp.inline_query, dp.chosen_inline_result):
        observer.middleware(middleware)

    dp.include_router(admin.router)
    dp.include_router(commands.router)
    dp.include_router(voice.router)
    dp.include_router(common.router)
    dp.include_router(media.router)
    dp.include_router(callbacks.router)
    dp.include_router(inline.router)
    dp.include_router(jokes.router)

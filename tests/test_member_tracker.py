from types import SimpleNamespace

import pytest

from utils import middlewares
from utils.middlewares import MemberTrackerMiddleware


def chat(chat_id=-100, kind="supergroup", title="Group"):
    return SimpleNamespace(id=chat_id, type=kind, title=title)


def user(user_id=7, is_bot=False):
    return SimpleNamespace(id=user_id, is_bot=is_bot)


@pytest.fixture
def writes(monkeypatch):
    calls = []
    monkeypatch.setattr(middlewares.db, "track_member", lambda *a: calls.append(a))
    return calls


async def handler(event, data):
    return "handled"


async def test_records_group_member_once_per_interval(writes):
    mw = MemberTrackerMiddleware(interval=3600)
    data = {"event_chat": chat(), "event_from_user": user()}

    assert await mw(handler, None, data) == "handled"
    assert await mw(handler, None, data) == "handled"

    assert writes == [(-100, "Group", 7)]


async def test_writes_again_after_interval(writes):
    mw = MemberTrackerMiddleware(interval=0)
    data = {"event_chat": chat(), "event_from_user": user()}

    await mw(handler, None, data)
    await mw(handler, None, data)

    assert len(writes) == 2


async def test_ignores_private_chats_and_bots(writes):
    mw = MemberTrackerMiddleware()

    await mw(handler, None, {"event_chat": chat(7, "private"), "event_from_user": user()})
    await mw(handler, None, {"event_chat": chat(), "event_from_user": user(is_bot=True)})
    await mw(handler, None, {"event_chat": chat()})

    assert writes == []


async def test_db_failure_never_blocks_handler_and_retries(monkeypatch):
    calls = []

    def flaky(*args):
        calls.append(args)
        if len(calls) == 1:
            raise RuntimeError("db down")

    monkeypatch.setattr(middlewares.db, "track_member", flaky)
    mw = MemberTrackerMiddleware(interval=3600)
    data = {"event_chat": chat(), "event_from_user": user()}

    assert await mw(handler, None, data) == "handled"
    assert await mw(handler, None, data) == "handled"

    assert len(calls) == 2

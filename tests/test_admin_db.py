"""Repo queries behind the admin user card, run against a real Postgres.

Skipped unless TEST_PG_DSN points at a disposable database (it is wiped), e.g.
    TEST_PG_DSN="dbname=test user=test host=localhost port=55432" just test
"""

import os
from datetime import datetime

import psycopg2
import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import GetMe, SendAudio, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from config.constants import DAMIR_USER_ID
from database.repo import DB_actions

DSN = os.environ.get("TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="TEST_PG_DSN not set")


@pytest.fixture
def db(monkeypatch):
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    monkeypatch.setattr(DB_actions, "_get_connection", lambda self: psycopg2.connect(DSN))
    repo = DB_actions()
    repo.init_db()
    return repo


def test_tracked_groups_show_on_user_details(db):
    db.add_user(7, "neo", "Thomas", "Anderson")
    db.track_member(-100, "Old title", 7)
    db.track_member(-100, "Zion", 7)
    db.track_member(-200, None, 7)
    db.track_member(-100, "Zion", 8)

    groups = db.get_user_details(7)["groups"]

    assert sorted((g["chat_id"], g["title"]) for g in groups) == [(-200, None), (-100, "Zion")]


def test_init_db_backfills_membership_from_jokes_idempotently(db):
    db.add_user(7, "neo", None, None)
    joke_id = db.create_joke(-300, 9, "author", 1)
    db.upsert_vote(joke_id, 7, 10)

    db.init_db()
    db.init_db()

    assert [g["chat_id"] for g in db.get_user_details(7)["groups"]] == [-300]
    count = db.execute_query("SELECT COUNT(*) FROM chat_members", fetch_all=False)[0]
    assert count == 2  # author + voter, once each


def test_user_details_summarize_activity(db):
    db.add_user(7, "neo", None, None)
    for cmd in ["dl", "dl", "joke"]:
        db.log_command(7, cmd)
    db.save_file(7, "file-a", "audio/mpeg")

    details = db.get_user_details(7)

    assert details["command_count"] == 3
    assert details["saved_files"] == 1
    assert details["top_commands"] == [("dl", 2), ("joke", 1)]
    assert details["last_active"] is not None


def test_user_list_rows_carry_activity_counts(db):
    db.add_user(7, "neo", None, None)
    db.add_user(8, "trinity", None, None)
    db.log_command(7, "dl")
    db.save_file(8, "file-a", "video/mp4")

    rows = {u["user_id"]: u for u in db.get_all_users()}
    found = db.search_users("neo")

    assert (rows[7]["command_count"], rows[7]["saved_files"]) == (1, 0)
    assert (rows[8]["command_count"], rows[8]["saved_files"]) == (0, 1)
    assert [u["user_id"] for u in found] == [7]
    assert found[0]["command_count"] == 1


def test_dashboard_renders_from_real_stats(db):
    from utils.helpers import generate_stats_text

    db.add_user(7, None, "Neo", None)
    db.log_command(7, "dl")
    db.save_file(7, "file-a", "audio/mpeg")

    text = generate_stats_text(db.get_stats())

    assert text.count("Neo /u7") == 3  # recent, most active, top savers


class FakeSession(BaseSession):
    """Records every Bot API call instead of talking to Telegram."""

    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(id=1, is_bot=True, first_name="bot", username="bot")
        if isinstance(method, SendMessage):
            return Message(message_id=2, date=datetime.now(), chat=Chat(id=1, type="private"))
        return True

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        yield b""


@pytest.fixture(scope="module")
def dispatcher():
    from handlers import admin

    dp = Dispatcher()
    dp.include_router(admin.router)
    return dp


def admin_message(text):
    return Message(
        message_id=1,
        date=datetime.now(),
        chat=Chat(id=DAMIR_USER_ID, type="private"),
        from_user=User(id=DAMIR_USER_ID, is_bot=False, first_name="admin"),
        text=text,
        entities=[MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))],
    )


def admin_callback(data):
    return CallbackQuery(
        id="1",
        chat_instance="1",
        data=data,
        from_user=User(id=DAMIR_USER_ID, is_bot=False, first_name="admin"),
        message=admin_message("/admin"),
    )


async def send(dp, **update):
    session = FakeSession()
    await dp.feed_update(Bot("1:x", session=session), Update(update_id=1, **update))
    return [c for c in session.calls if not isinstance(c, GetMe)]


async def test_admin_opens_user_card_with_groups_and_files(db, dispatcher):
    db.add_user(7, "neo", None, None)
    db.track_member(-100, "Zion", 7)
    db.save_file(7, "tg-file-id", "audio/mpeg")

    [card] = await send(dispatcher, message=admin_message("/u7"))
    [files_page, _] = await send(dispatcher, callback_query=admin_callback("admin_files:7:0:h"))
    file_db_id = db.get_user_saved_files(7)[0]["id"]
    [sent, _] = await send(dispatcher, callback_query=admin_callback(f"admin_file:{file_db_id}"))

    assert "Zion" in card.text and "Saved files: <b>1</b>" in card.text
    assert any(
        b.callback_data == "admin_files:7:0:h" for r in card.reply_markup.inline_keyboard for b in r
    )
    assert "Saved files" in files_page.text
    assert isinstance(sent, SendAudio) and sent.audio == "tg-file-id"


async def test_non_admin_gets_nothing(db, dispatcher):
    msg = admin_message("/u7").model_copy(
        update={"from_user": User(id=42, is_bot=False, first_name="x")}
    )

    assert await send(dispatcher, message=msg) == []

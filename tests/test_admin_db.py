"""Repo queries behind the admin user card, run against a real Postgres.

Skipped unless TEST_PG_DSN points at a disposable database (it is wiped), e.g.
    TEST_PG_DSN="dbname=test user=test host=localhost port=55432" just test
"""

import os

import psycopg2
import pytest

from database.repo import DB_actions

DSN = os.environ.get("TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="TEST_PG_DSN not set")


@pytest.fixture
def db(monkeypatch):
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    repo = DB_actions()
    monkeypatch.setattr(repo, "_get_connection", lambda: psycopg2.connect(DSN))
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

from datetime import datetime

from utils.helpers import (
    generate_stats_text,
    render_user_card,
    saved_files_keyboard,
    user_card_keyboard,
)

BIG_ID = -1001234567890123


def user(**over):
    base = {
        "user_id": 7,
        "username": None,
        "first_name": "<Neo>",
        "last_name": None,
        "joined_at": datetime(2025, 1, 1, 12, 0),
        "command_count": 3,
        "saved_files": 2,
        "last_active": datetime(2025, 2, 1, 12, 0),
        "top_commands": [("dl", 2), ("joke", 1)],
        "recent_commands": [{"command": "dl", "used_at": datetime(2025, 2, 1, 12, 0)}],
        "groups": [
            {"chat_id": -100, "title": "Zion & co", "last_seen": datetime(2025, 2, 1)},
            {"chat_id": -200, "title": None, "last_seen": datetime(2025, 1, 5)},
        ],
    }
    return base | over


def callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


def test_card_lists_groups_and_escapes_html():
    card = render_user_card(user())

    assert "&lt;Neo&gt;" in card and "<Neo>" not in card
    assert "Zion &amp; co" in card
    assert "-200" in card  # untitled group still identifiable
    assert "Groups (2)" in card
    assert "/dl" in card


def test_card_without_groups_says_so():
    assert "not seen in any group" in render_user_card(user(groups=[])).lower()


def test_card_caps_long_group_list():
    groups = [
        {"chat_id": -i, "title": f"g{i}", "last_seen": datetime(2025, 1, 1)} for i in range(50)
    ]

    card = render_user_card(user(groups=groups))

    assert "Groups (50)" in card
    assert "g49" not in card
    assert "more" in card


def test_card_keyboard_opens_files_and_goes_back():
    assert "admin_files:7:0:3" in callbacks(user_card_keyboard(user(), back="3"))
    assert "view_users:3" in callbacks(user_card_keyboard(user(), back="3"))
    assert "back_to_search_results" in callbacks(user_card_keyboard(user(), back="s"))
    assert "refresh_admin" in callbacks(user_card_keyboard(user(), back="h"))


def test_card_keyboard_hides_files_when_none_saved():
    assert not any(
        c.startswith("admin_files") for c in callbacks(user_card_keyboard(user(saved_files=0), "h"))
    )


def test_saved_files_keyboard_pages_and_returns_to_card():
    files = [{"id": i, "type": "audio/mpeg", "saved_at": datetime(2025, 1, 1)} for i in range(8)]

    data = callbacks(saved_files_keyboard(7, files, page=1, total=20, back="s"))

    assert "admin_file:0" in data
    assert "admin_files:7:0:s" in data and "admin_files:7:2:s" in data
    assert "user_details:7:s" in data


def test_callback_data_fits_telegram_limit():
    u = user(user_id=BIG_ID)
    files = [{"id": 2**31, "type": "video/mp4", "saved_at": datetime(2025, 1, 1)}]
    markups = [user_card_keyboard(u, "999"), saved_files_keyboard(BIG_ID, files, 999, 99999, "999")]

    assert all(len(c.encode()) <= 64 for m in markups for c in callbacks(m))


def test_stats_names_link_to_user_cards():
    stats = {
        "user_count": 1,
        "chat_count": 1,
        "total_saved_files": 1,
        "top_commands": [("dl", 5)],
        "recent_users": [(7, None, "<b>", None, "dl", datetime(2025, 1, 1))],
        "active_users": [(8, "neo", None, None, 5)],
        "top_savers": [(9, None, None, None, 2)],
    }

    text = generate_stats_text(stats)

    assert "/u7" in text and "/u8" in text and "/u9" in text
    assert "&lt;b&gt;" in text

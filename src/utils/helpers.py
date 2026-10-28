from datetime import datetime
from html import escape

import pytz
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import constants
from database.repo import DB_actions

db = DB_actions()

ADMIN_TZ = pytz.timezone("Etc/GMT-5")
CARD_MAX_GROUPS = 20
ADMIN_FILES_PER_PAGE = 8
FILE_ICONS = {"audio": "🎵", "video": "🎬", "voice": "🎙"}

# Admin navigation: a user card remembers where it was opened from via `back`:
#   "<page>" -> users list page, "s" -> last search results, "h" -> dashboard.


def fmt_ts(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """DB timestamps are naive UTC; show them in admin time."""
    return dt.replace(tzinfo=pytz.utc).astimezone(ADMIN_TZ).strftime(fmt) if dt else "—"


def display_name(user_id: int, username: str | None, first: str | None, last: str | None) -> str:
    """HTML-safe @username, else full name, else `User <id>`."""
    if username:
        return "@" + escape(username)
    return escape(f"{first or ''} {last or ''}".strip()) or f"User {user_id}"


def user_link(user_id, username, first, last) -> str:
    """Name followed by a tappable /u<id> that opens the user card."""
    return f"{display_name(user_id, username, first, last)} /u{user_id}"


def user_row_line(u: dict) -> str:
    """Two-line list entry: tappable name, then activity counts and join date."""
    name = user_link(u["user_id"], u["username"], u["first_name"], u["last_name"])
    joined = fmt_ts(u["joined_at"], "%Y-%m-%d")
    return f"• {name}\n   ⚡ {u['command_count']} · 📂 {u['saved_files']} · 📅 {joined}"


def add_user_buttons(builder: InlineKeyboardBuilder, users: list[dict], back: str) -> None:
    for u in users:
        name = display_name(u["user_id"], u["username"], u["first_name"], u["last_name"])
        builder.row(
            types.InlineKeyboardButton(
                text=f"👤 {name[:24]}", callback_data=f"user_details:{u['user_id']}:{back}"
            )
        )


def back_button(back: str) -> types.InlineKeyboardButton:
    if back == "s":
        return types.InlineKeyboardButton(
            text="« Search results", callback_data="back_to_search_results"
        )
    if back.isdigit():
        return types.InlineKeyboardButton(text="« Users", callback_data=f"view_users:{back}")
    return types.InlineKeyboardButton(text="📊 Dashboard", callback_data="refresh_admin")


def page_nav(page: int, pages: int, callback: str) -> list[types.InlineKeyboardButton]:
    """« n/N » buttons; `callback` is a format string taking the target page."""
    nav = [types.InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="noop")]
    if page > 0:
        nav.insert(0, types.InlineKeyboardButton(text="«", callback_data=callback.format(page - 1)))
    if page < pages - 1:
        nav.append(types.InlineKeyboardButton(text="»", callback_data=callback.format(page + 1)))
    return nav


def render_user_card(u: dict) -> str:
    full_name = escape(f"{u['first_name'] or ''} {u['last_name'] or ''}".strip()) or "—"
    username = "@" + escape(u["username"]) if u["username"] else "no username"
    lines = [
        f"👤 <b>{full_name}</b>",
        f"{username} · <code>{u['user_id']}</code>",
        "",
        f"📅 Joined: {fmt_ts(u['joined_at'])}",
        f"⏱ Last active: {fmt_ts(u['last_active'])}",
        f"⚡ Commands: <b>{u['command_count']}</b> · 📂 Saved files: <b>{u['saved_files']}</b>",
    ]

    if u["top_commands"]:
        top = " · ".join(f"/{escape(cmd)} ×{n}" for cmd, n in u["top_commands"])
        lines += ["", f"🏆 <b>Top commands:</b> {top}"]

    groups = u["groups"]
    lines += ["", f"👥 <b>Groups ({len(groups)})</b>"]
    for g in groups[:CARD_MAX_GROUPS]:
        title = escape(g["title"]) if g["title"] else "<i>untitled</i>"
        lines.append(
            f"• {title} <code>{g['chat_id']}</code> · {fmt_ts(g['last_seen'], '%Y-%m-%d')}"
        )
    if len(groups) > CARD_MAX_GROUPS:
        lines.append(f"… and {len(groups) - CARD_MAX_GROUPS} more")
    if not groups:
        lines.append("Not seen in any group yet")

    if u["recent_commands"]:
        lines += ["", "🕘 <b>Recent:</b>"]
        lines += [f"/{escape(c['command'])} · {fmt_ts(c['used_at'])}" for c in u["recent_commands"]]

    return "\n".join(lines)


def user_card_keyboard(u: dict, back: str) -> types.InlineKeyboardMarkup:
    uid = u["user_id"]
    builder = InlineKeyboardBuilder()
    if u["saved_files"]:
        builder.button(
            text=f"📂 Saved files ({u['saved_files']})", callback_data=f"admin_files:{uid}:0:{back}"
        )
    builder.button(text="🔄 Refresh", callback_data=f"user_details:{uid}:{back}")
    builder.add(back_button(back))
    builder.adjust(*((1, 2) if u["saved_files"] else (2,)))
    return builder.as_markup()


def saved_files_keyboard(user_id: int, files: list[dict], page: int, total: int, back: str):
    pages = max(1, -(-total // ADMIN_FILES_PER_PAGE))
    builder = InlineKeyboardBuilder()
    for f in files:
        kind = f["type"].split("/")[0]
        label = f"{FILE_ICONS.get(kind, '📄')} {kind.capitalize()} · {fmt_ts(f['saved_at'], '%d.%m.%Y')}"
        builder.row(types.InlineKeyboardButton(text=label, callback_data=f"admin_file:{f['id']}"))

    builder.row(*page_nav(page, pages, f"admin_files:{user_id}:{{}}:{back}"))
    builder.row(
        types.InlineKeyboardButton(
            text="« Back to user", callback_data=f"user_details:{user_id}:{back}"
        )
    )
    return builder.as_markup()


async def show_users_page(message: types.Message, page=0, is_edit=False):
    per_page = constants.ADMIN_USERS_PER_PAGE
    total_users = db.get_total_users_count()
    total_pages = max(1, -(-total_users // per_page))
    page = min(max(page, 0), total_pages - 1)
    users = db.get_all_users(limit=per_page, offset=page * per_page)

    text = f"👥 <b>Users</b> · {total_users} total · page {page + 1}/{total_pages}\n\n"
    text += "\n".join(user_row_line(u) for u in users)

    builder = InlineKeyboardBuilder()
    add_user_buttons(builder, users, back=str(page))

    builder.row(*page_nav(page, total_pages, "view_users:{}"))
    builder.row(
        types.InlineKeyboardButton(text="🔍 Search", callback_data="search_user"),
        back_button("h"),
    )

    send = message.edit_text if is_edit else message.reply
    await send(text, reply_markup=builder.as_markup())


def generate_stats_text(stats):
    """Dashboard text. User rows are (user_id, username, first, last, *extra)."""
    lines = [
        "📊 <b>Admin dashboard</b>",
        "",
        f"👥 Users: <code>{stats['user_count']}</code> · 💬 Chats: <code>{stats['chat_count']}</code>"
        f" · 📂 Files: <code>{stats['total_saved_files']}</code>",
        "",
        "<b>Top commands:</b>",
        " · ".join(f"/{escape(cmd)} {n}" for cmd, n in stats["top_commands"]),
        "",
        "🕘 <b>Recently active:</b>",
        *(
            f"• {user_link(*u[:4])} · /{escape(u[4])} {fmt_ts(u[5], '%m-%d %H:%M')}"
            for u in stats["recent_users"]
        ),
        "",
        "🔥 <b>Most active:</b>",
        *(f"• {user_link(*u[:4])} · {u[4]} cmds" for u in stats["active_users"]),
        "",
        "💾 <b>Top savers:</b>",
        *(f"• {user_link(*u[:4])} · {u[4]} files" for u in stats["top_savers"]),
        "",
        f"<i>Tap /u… to open a user · updated {datetime.now(ADMIN_TZ):%H:%M:%S}</i>",
    ]
    return "\n".join(lines)


def build_saved_files_keyboard(user_id: int, page: int = 0) -> types.InlineKeyboardMarkup | None:
    files = db.get_user_saved_files(user_id, page)
    if not files:
        return None

    query = "SELECT COUNT(*) FROM user_saved WHERE user_id = %s"
    result = db.execute_query(query, (user_id,), fetch_all=False)
    total_files = result[0]

    items_per_page = 5
    total_pages = (total_files + items_per_page - 1) // items_per_page

    builder = InlineKeyboardBuilder()

    # Add file buttons
    for file in files:
        file_type = file["type"].split("/")[0].capitalize()
        file_id = file["id"]

        saved_date = file["saved_at"].strftime("%d.%m.%Y")

        builder.row(
            types.InlineKeyboardButton(
                text=f"{file_type} ({saved_date})", callback_data=f"saved_file:{file_id}"
            )
        )

    navigation_row = []

    if page > 0:
        navigation_row.append(
            types.InlineKeyboardButton(text="⬅️ Previous", callback_data=f"saved_page:{page - 1}")
        )

    if page < total_pages - 1:
        navigation_row.append(
            types.InlineKeyboardButton(text="Next ➡️", callback_data=f"saved_page:{page + 1}")
        )

    if total_pages > 1:
        builder.row(
            types.InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop")
        )

    if navigation_row:
        builder.row(*navigation_row)

    return builder.as_markup()


def build_file_action_keyboard(file_id: int) -> types.InlineKeyboardMarkup:
    file_info = db.get_file_by_id(file_id)
    file_type = file_info["type"].split("/")[0].capitalize() if file_info else "File"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text=f"🗑 Delete saved {file_type}", callback_data=f"delete_file:{file_id}"
        )
    )

    builder.row(types.InlineKeyboardButton(text="⬅️ Back to files", callback_data="back_to_files"))

    return builder.as_markup()


def build_delete_confirmation_keyboard(file_id: int) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Add confirmation buttons
    builder.row(
        types.InlineKeyboardButton(
            text="Yes, pretty sure", callback_data=f"confirm_delete:{file_id}"
        )
    )

    builder.row(types.InlineKeyboardButton(text="No", callback_data="back_to_files"))

    return builder.as_markup()

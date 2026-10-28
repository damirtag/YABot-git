import asyncio
import re
from html import escape

from aiogram import Bot, F, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.constants import ADMIN_KEYBOARD, DAMIR_USER_ID
from database.repo import DB_actions
from utils.broadcast import BroadcastManager
from utils.helpers import (
    ADMIN_FILES_PER_PAGE,
    add_user_buttons,
    back_button,
    fmt_ts,
    generate_stats_text,
    render_user_card,
    saved_files_keyboard,
    show_users_page,
    user_card_keyboard,
    user_row_line,
)

router = Router()
db = DB_actions()

# Admin panel: everything in here is admin-only, checked once.
panel = Router()
panel.message.filter(F.from_user.id == DAMIR_USER_ID)
panel.callback_query.filter(F.from_user.id == DAMIR_USER_ID)
router.include_router(panel)

SEARCH_HELP = (
    "🔍 <b>Search users</b>\n\n"
    "Send an ID, @username, or first/last name.\n"
    "Tip: tap any <code>/u…</code> link to open a user directly."
)


class SearchStates(StatesGroup):
    waiting_for_search_term = State()


async def show_dashboard(message: types.Message, is_edit: bool = False):
    send = message.edit_text if is_edit else message.reply
    await send(generate_stats_text(db.get_stats()), reply_markup=ADMIN_KEYBOARD)


async def show_user_card(message: types.Message, user_id: int, back: str, is_edit: bool) -> bool:
    user = db.get_user_details(user_id)
    if not user:
        return False
    send = message.edit_text if is_edit else message.reply
    await send(render_user_card(user), reply_markup=user_card_keyboard(user, back))
    return True


async def perform_user_search(
    message: types.Message, search_term: str, state: FSMContext, is_edit: bool = False
):
    term = search_term.strip()
    await state.update_data(last_search_term=term)
    users = db.search_users(term) if term else []

    if users:
        text = f"🔍 <b>{len(users)} result(s) for</b> <code>{escape(term)}</code>\n\n"
        text += "\n".join(user_row_line(u) for u in users)
    else:
        text = f"❌ No users found for <code>{escape(term)}</code>"

    builder = InlineKeyboardBuilder()
    add_user_buttons(builder, users, back="s")
    builder.row(
        InlineKeyboardButton(text="🔍 New search", callback_data="search_user"),
        back_button("h"),
    )

    send = message.edit_text if is_edit else message.reply
    await send(text, reply_markup=builder.as_markup())


@panel.message(Command("admin"))
async def get_stats(message: types.Message):
    await show_dashboard(message)


@panel.message(Command("users"))
async def view_users_command(message: types.Message):
    await show_users_page(message, page=0)


@panel.message(Command(re.compile(r"u(\d+)$")))
async def user_card_command(message: types.Message, command: CommandObject):
    user_id = int(command.regexp_match.group(1))
    if not await show_user_card(message, user_id, back="h", is_edit=False):
        await message.reply(f"❌ No user with ID <code>{user_id}</code>")


@panel.message(Command("search"))
async def search_user_command(message: types.Message, command: CommandObject, state: FSMContext):
    if command.args:
        await perform_user_search(message, command.args, state)
    else:
        await message.reply(SEARCH_HELP + "\n\nExample: <code>/search john</code>")


@panel.callback_query(F.data == "refresh_admin")
async def refresh_stats(callback_query: types.CallbackQuery):
    await show_dashboard(callback_query.message, is_edit=True)
    await callback_query.answer("Updated")


@panel.callback_query(F.data == "search_user")
async def search_user_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_search_term)
    await state.update_data(message_to_edit=callback_query.message)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_search")]]
    )
    await callback_query.message.edit_text(SEARCH_HELP, reply_markup=keyboard)
    await callback_query.answer()


@panel.message(SearchStates.waiting_for_search_term)
async def process_search_term(message: types.Message, state: FSMContext):
    original_message = (await state.get_data()).get("message_to_edit")
    await state.clear()

    try:
        await message.delete()
    except Exception:
        pass

    if original_message:
        await perform_user_search(original_message, message.text or "", state, is_edit=True)


@panel.callback_query(F.data == "cancel_search")
async def cancel_search(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_dashboard(callback_query.message, is_edit=True)
    await callback_query.answer("Search cancelled")


@panel.callback_query(F.data == "back_to_search_results")
async def back_to_search_results(callback_query: types.CallbackQuery, state: FSMContext):
    search_term = (await state.get_data()).get("last_search_term")

    if search_term:
        await perform_user_search(callback_query.message, search_term, state, is_edit=True)
    else:
        await callback_query.message.edit_text(
            SEARCH_HELP,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 New search", callback_data="search_user")],
                    [back_button("h")],
                ]
            ),
        )
    await callback_query.answer()


@panel.callback_query(F.data.startswith("view_users:"))
async def users_pagination_callback(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split(":")[1])
    await show_users_page(callback_query.message, page, is_edit=True)
    await callback_query.answer()


@panel.callback_query(F.data.startswith("user_details:"))
async def user_details_callback(callback_query: types.CallbackQuery):
    _, user_id, back = callback_query.data.split(":")
    if not await show_user_card(callback_query.message, int(user_id), back, is_edit=True):
        return await callback_query.answer("User not found.", show_alert=True)
    await callback_query.answer()


@panel.callback_query(F.data.startswith("admin_files:"))
async def admin_files_callback(callback_query: types.CallbackQuery):
    _, user_id, page, back = callback_query.data.split(":")
    user_id, page = int(user_id), int(page)
    user = db.get_user_details(user_id)
    if not user:
        return await callback_query.answer("User not found.", show_alert=True)

    files = db.get_user_saved_files(user_id, page, ADMIN_FILES_PER_PAGE)
    text = (
        f"📂 <b>Saved files</b> · {user['saved_files']} total\n"
        f"{user_row_line(user)}\n\n"
        "Tap a file to get it here."
    )
    keyboard = saved_files_keyboard(user_id, files, page, user["saved_files"], back)
    await callback_query.message.edit_text(text, reply_markup=keyboard)
    await callback_query.answer()


# Saved file type prefix -> Bot method that can resend that file_id.
SEND_BY_TYPE = {"audio": "send_audio", "video": "send_video", "voice": "send_voice"}


@panel.callback_query(F.data.startswith("admin_file:"))
async def admin_file_callback(callback_query: types.CallbackQuery, bot: Bot):
    file = db.get_file_by_id(int(callback_query.data.split(":")[1]))
    if not file:
        return await callback_query.answer("File not found.", show_alert=True)

    send = getattr(bot, SEND_BY_TYPE.get(file["type"].split("/")[0], "send_document"))
    caption = f"📂 {escape(file['type'])} · saved {fmt_ts(file['saved_at'])} by /u{file['user_id']}"
    try:
        await send(callback_query.message.chat.id, file["file_id"], caption=caption)
        await callback_query.answer()
    except Exception as e:
        await callback_query.answer(f"Failed to send: {e}"[:200], show_alert=True)


@panel.message(Command("get"))
async def send_file(message: types.Message, command: CommandObject, bot: Bot):
    if not command.args:
        return await message.reply("Usage: /get {file_id}")

    try:
        await bot.send_document(chat_id=message.chat.id, document=command.args.strip())
    except Exception as e:
        await message.reply(f"Failed to send file: {e}")


# user quality survey
broadcast_manager = BroadcastManager()
MAX_RETRIES = 3
BASE_DELAY = 0.05
BATCH_SIZE = 50


async def copy_with_retry(
    bot: Bot,
    target_id: int,
    from_chat_id: int,
    message_id: int,
    keyboard: InlineKeyboardMarkup | None = None,
    retries: int = MAX_RETRIES,
) -> dict:
    """Copy a composed message to a recipient with retry + error categorization.

    Uses ``copy_message`` so the broadcast keeps the exact formatting/media the
    admin wrote in Telegram (entities are preserved, no parse_mode needed).
    """
    for attempt in range(retries):
        try:
            await bot.copy_message(target_id, from_chat_id, message_id, reply_markup=keyboard)
            return {"status": "sent", "error": None}
        except Exception as e:
            error_msg = str(e).lower()

            # Categorize errors
            if "blocked" in error_msg or "bot was blocked" in error_msg:
                return {"status": "blocked", "error": "User blocked the bot"}
            elif "chat not found" in error_msg or "user not found" in error_msg:
                return {"status": "not_found", "error": "User/chat not found"}
            elif "too many requests" in error_msg or "retry after" in error_msg:
                if attempt < retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                    continue
                return {"status": "rate_limited", "error": "Rate limit exceeded"}
            elif attempt < retries - 1:
                await asyncio.sleep(1)
                continue
            else:
                return {"status": "failed", "error": str(e)}

    return {"status": "failed", "error": "Max retries exceeded"}


def _vote_keyboard(broadcast_id: str | None) -> InlineKeyboardMarkup:
    """👍/👎 voting keyboard. ``broadcast_id=None`` for previews (no campaign yet)."""
    suffix = f":{broadcast_id}" if broadcast_id else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍", callback_data=f"vote_up{suffix}"),
                InlineKeyboardButton(text="👎", callback_data=f"vote_down{suffix}"),
            ]
        ]
    )


@router.message(Command("sendall"))
async def send_broadcast(m: types.Message, command: CommandObject, bot: Bot):
    """
    Broadcast a message you compose in Telegram (full formatting/media kept).

    Reply to the message you want to send with /sendall:
        /sendall          - broadcast to users, with voting buttons
        /sendall rmvote   - without voting buttons
        /sendall chat     - broadcast to chats instead of users
        /sendall preview  - send the message back to you only (no broadcast)
    """
    if m.from_user.id != DAMIR_USER_ID:
        return

    if not m.reply_to_message:
        return await m.reply(
            "✍️ <b>How to broadcast</b>\n\n"
            "1. Send (or forward) the message you want to broadcast — with any "
            "formatting, links, or media.\n"
            "2. <b>Reply</b> to it with <code>/sendall</code>.\n\n"
            "Flags: <code>rmvote</code> (no buttons), <code>chat</code> (to chats), "
            "<code>preview</code> (test on yourself)."
        )

    args = command.args
    is_chat = args and "chat" in args.lower()
    is_no_vote = args and "rmvote" in args.lower()
    is_preview = args and "preview" in args.lower()

    # The message to broadcast is whatever the admin replied to.
    from_chat_id = m.chat.id
    source_message_id = m.reply_to_message.message_id

    # Preview mode — copy the message back to the admin, nothing is broadcast.
    if is_preview:
        await bot.copy_message(
            m.chat.id,
            from_chat_id,
            source_message_id,
            reply_markup=None if is_no_vote else _vote_keyboard(None),
        )
        return

    # Get recipients
    if is_chat:
        chats_list = db.execute_query("SELECT chat_Id FROM chats")
        recipients = [row[0] for row in chats_list]
        recipient_type = "chats"
    else:
        users = db.execute_query("SELECT user_id FROM users")
        recipients = [row[0] for row in users]
        recipient_type = "users"

    if not recipients:
        await m.reply("No recipients found!")
        return

    # Create broadcast campaign — store a text snippet for history/results.
    snippet = m.reply_to_message.text or m.reply_to_message.caption or "[media message]"
    broadcast_id = broadcast_manager.create_broadcast(snippet, not is_no_vote)

    keyboard = None if is_no_vote else _vote_keyboard(broadcast_id)

    # Progress message
    progress_msg = await m.reply(
        f"🚀 Starting broadcast to {len(recipients)} {recipient_type}...\n\n"
        f"Progress: 0/{len(recipients)}\n"
        f"✅ Sent: 0\n"
        f"❌ Failed: 0\n"
        f"🚫 Blocked: 0"
    )

    # Send to all recipients
    stats = {
        "total": len(recipients),
        "sent": 0,
        "failed": 0,
        "blocked": 0,
        "not_found": 0,
        "rate_limited": 0,
    }

    failed_ids = []

    for i, recipient_id in enumerate(recipients, 1):
        result = await copy_with_retry(bot, recipient_id, from_chat_id, source_message_id, keyboard)

        # Update stats
        if result["status"] == "sent":
            stats["sent"] += 1
        elif result["status"] == "blocked":
            stats["blocked"] += 1
            failed_ids.append((recipient_id, result["error"]))
        elif result["status"] == "not_found":
            stats["not_found"] += 1
            failed_ids.append((recipient_id, result["error"]))
        elif result["status"] == "rate_limited":
            stats["rate_limited"] += 1
            failed_ids.append((recipient_id, result["error"]))
        else:
            stats["failed"] += 1
            failed_ids.append((recipient_id, result["error"]))

        # Update progress every BATCH_SIZE messages
        if i % BATCH_SIZE == 0 or i == len(recipients):
            progress_text = (
                f"🚀 Broadcast Progress\n\n"
                f"Progress: {i}/{len(recipients)}\n"
                f"✅ Sent: {stats['sent']}\n"
                f"❌ Failed: {stats['failed']}\n"
                f"🚫 Blocked: {stats['blocked']}\n"
                f"👻 Not Found: {stats['not_found']}\n"
                f"⏱ Rate Limited: {stats['rate_limited']}"
            )
            try:
                await progress_msg.edit_text(progress_text)
            except Exception:
                pass

        await asyncio.sleep(BASE_DELAY)

    # Save final stats
    broadcast_manager.update_broadcast_stats(broadcast_id, stats)

    # Final report
    success_rate = (stats["sent"] / stats["total"] * 100) if stats["total"] > 0 else 0
    final_text = (
        f"✅ Broadcast Complete!\n\n"
        f"📊 Results:\n"
        f"Total: {stats['total']}\n"
        f"✅ Sent: {stats['sent']} ({success_rate:.1f}%)\n"
        f"❌ Failed: {stats['failed']}\n"
        f"🚫 Blocked: {stats['blocked']}\n"
        f"👻 Not Found: {stats['not_found']}\n"
        f"⏱ Rate Limited: {stats['rate_limited']}\n\n"
        f"Broadcast ID: {broadcast_id}"
    )

    if failed_ids:
        final_text += f"\n\nUse /failures {broadcast_id} to see failed IDs"

    await progress_msg.edit_text(final_text)


@router.message(Command("results"))
async def show_results(m: types.Message, command: CommandObject):
    """Show voting results for a broadcast. Usage: /results [broadcast_id]"""
    if m.from_user.id != 1038468423:
        return

    args = command.args

    if not args:
        # Show all broadcasts
        history = broadcast_manager.get_broadcast_history()
        if not history:
            await m.reply("No broadcasts found.")
            return

        text = "📊 Broadcast History:\n\n"
        for b in history[:10]:  # Show last 10
            text += (
                f"ID: {b['id']}\n"
                f"Created: {b['created_at'][:19]}\n"
                f"Sent: {b['stats']['sent']}/{b['stats']['total']}\n"
                f"Message: {b['message']}\n\n"
            )

        await m.reply(text)
        return

    # Show specific broadcast results
    broadcast_id = args
    vote_stats = broadcast_manager.get_vote_stats(broadcast_id)

    if vote_stats["total"] == 0:
        await m.reply(f"No votes yet for broadcast {broadcast_id}")
        return

    yes_pct = (vote_stats["yes"] / vote_stats["total"] * 100) if vote_stats["total"] > 0 else 0
    no_pct = (vote_stats["no"] / vote_stats["total"] * 100) if vote_stats["total"] > 0 else 0

    text = (
        f"📊 Voting Results for {broadcast_id}\n\n"
        f"👍 Yes: {vote_stats['yes']} ({yes_pct:.1f}%)\n"
        f"👎 No: {vote_stats['no']} ({no_pct:.1f}%)\n"
        f"Total Votes: {vote_stats['total']}"
    )

    await m.reply(text)


@router.callback_query(lambda c: c.data and c.data.startswith(("vote_up:", "vote_down:")))
async def vote_handler(callback_query: types.CallbackQuery):
    """Handle voting on broadcasts"""
    parts = callback_query.data.split(":")
    vote_type = parts[0]
    broadcast_id = parts[1] if len(parts) > 1 else "default"

    user_id = str(callback_query.from_user.id)
    chat_id = str(callback_query.message.chat.id)
    is_private = callback_query.message.chat.type == "private"

    vote = "Yes" if vote_type == "vote_up" else "No"
    identifier = user_id if is_private else chat_id

    # Try to add vote
    if not broadcast_manager.add_vote(broadcast_id, identifier, vote):
        await callback_query.answer("You've already voted!", show_alert=True)
        return

    await callback_query.answer(f"Vote recorded: {vote}")

    msg = callback_query.message
    is_media = msg.text is None  # photo/video broadcasts carry a caption, not text

    # Update message
    if is_private:
        # For media messages we can't edit text — just drop the buttons.
        try:
            if is_media:
                await msg.edit_reply_markup(reply_markup=None)
            else:
                await msg.edit_text(f"Thank you for your feedback!\n\nYour vote: {vote}")
        except Exception:
            pass
    else:
        # Show live results in groups
        vote_stats = broadcast_manager.get_vote_stats(broadcast_id)
        keyboard = _vote_keyboard(broadcast_id)
        base = (msg.text or msg.caption or "").split("\n\n")[0]
        results = f"{base}\n\n👍 Yes: {vote_stats['yes']}\n👎 No: {vote_stats['no']}"
        try:
            if is_media:
                await msg.edit_caption(caption=results, reply_markup=keyboard)
            else:
                await msg.edit_text(results, reply_markup=keyboard)
        except Exception:
            pass


@router.message(Command("failures"))
async def show_failures(m: types.Message, command: CommandObject):
    """Show failed recipients for a broadcast. Usage: /failures [broadcast_id]"""
    if m.from_user.id != 1038468423:
        return

    await m.reply(
        "Failed recipients logging not yet implemented in this version.\nCheck console logs for error details."
    )


@router.message(Command("cleanvotes"))
async def clean_old_votes(m: types.Message):
    """Clean old vote data (keep last 5 broadcasts)"""
    if m.from_user.id != 1038468423:
        return

    broadcasts = list(broadcast_manager.data["broadcasts"].items())
    if len(broadcasts) <= 5:
        await m.reply("No old broadcasts to clean.")
        return

    # Sort by created_at and keep last 5
    sorted_broadcasts = sorted(broadcasts, key=lambda x: x[1]["created_at"], reverse=True)

    to_keep = {bid for bid, _ in sorted_broadcasts[:5]}

    # Remove old broadcasts
    broadcast_manager.data["broadcasts"] = {
        bid: b for bid, b in broadcast_manager.data["broadcasts"].items() if bid in to_keep
    }
    broadcast_manager.data["votes"] = {
        bid: v for bid, v in broadcast_manager.data["votes"].items() if bid in to_keep
    }

    broadcast_manager.save_data()
    removed = len(broadcasts) - 5
    await m.reply(f"✅ Cleaned {removed} old broadcast(s).")

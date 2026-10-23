GH_REPO: str = "https://github.com/damirTAG/YABot-git"
# -- IDS --
DAMIR_USER_ID = 1038468423
CACHE_CHAT = -1001911592881
IGNORE_CHAT_IDS = [-1001559555304, -1001919227306, -1001987624296, -1002050266275]
# -1001559555304, -1001919227306, -1001987624296

# -- UI TEXT --
SAVED = "🔥 This {} saved. Call @yerzhanakh_bot in inline to send it in any chat"
BASE_ERROR = "<i>Sorry, failed to proceed this request</i>"
UPDATE_NOTIFY = (
    "⚡ <b>Update: i finally fixed instagram downloader (reels and post)</b>\n"
    "and i also added inline support for inst and tiktok, so "
    "you can paste a link like this:\n"
    "<code>@yerzhanakh_bot your link here</code>\n\n"
    "<b>example:</b>\n"
    "<code>@yerzhanakh_bot https://www.instagram.com/reel/DZMvmT9s1w5/</code>\n\n"
    "enjoy downloading your brainrot content using my supa pupa bot"
)
HELP = """<b>Just send a link — I'll download it:</b>
<i>🔴 YouTube videos / Shorts
🔵 Instagram Reels / Posts
⚫️ TikTok videos / photos
🔵 VK Clips · 🟣 Twitch Clips
🟠 SoundCloud tracks
🟡 Yandex Music tracks</i>

<b>Commands:</b>
<code>/ym query</code> — search Yandex Music
<code>/sc query</code> — search SoundCloud
<code>/ask question</code> — ask AI (or reply to a message with /ask)
<code>/w city</code> or <code>.ц city</code> — weather + 5-day forecast
<code>/q</code> · <code>/qq</code> — reply to a message to make a quote sticker
<code>/roll</code> — random number 1–100
<code>/joke</code> — reply to a joke to start a 1–10 rating (groups)
<code>/jokestats</code> — joke stats and weekly leaderboard (groups)
<code>/saved</code> — your saved files (private chat)
<code>/settings</code> — turn features on/off for this chat (admins in groups)
<code>/info</code> — bot stats
<code>/help</code> — this message

<b>Inline:</b>
<code>@yerzhanakh_bot</code> — your saved files
<code>@yerzhanakh_bot ask ...</code> — ask AI
<code>@yerzhanakh_bot link</code> — send a TikTok/Instagram video inline

<b>Automatic:</b>
🎤 Voice and video messages are transcribed to text
🪙 Currency converter for fiat and crypto:
<code>100 USD KZT</code> · <code>50 eur to rub</code> · <code>1 SOL</code> · <code>usd kzt</code>
"""
INFO = (
    "📊 Hey there! Here are the current stats:\n\n"
    "🔥 {most_downloaded} is the most popular source with {most_downloaded_count:,} downloads\n\n"
    "Downloads from other platforms:\n"
    "{others}\n\n"
    "🤖 Delivered more than {ai_answers:,} answers from AI and recognized almost {speech_count:,} voice messages\n\n"
    "💫 Additional stats:\n"
    "• Processing about {avg_requests:,} requests daily\n"
    "• Performed {currency_conv:,} currency conversions\n"
    "• Total files delivered: {total_files:,}\n"
    "• Currently serving {total_users:,} users {chats_info}\n\n"
    "❤️ Thanks for using the bot! Any suggestions? Feel free to contact @damirtag"
    f"\n\n<i>Bot's source-code available on</i> <b><a href='{GH_REPO}'>GitHub</a></b>"
)
ARE_YOU_SURE_STICKER_ID = "CAACAgIAAxkBAAIH22geNVJr-3S_AjeP6c66NFrUu-5OAAI1dwAC7cXxSlIE1lAabmYFNgQ"

# -- VARS --
MAX_GPT_QUERY_LENGTH: int = 150
ADMIN_USERS_PER_PAGE: int = 10
CHATGPT_ROLE: str = """
Ты встроен в Ержан бота в Телеграме, твой создатель - Дамир. Ты помощник AI ассистент.\n
Можно обращаться на 'ты' и шутить но не всегда, если понимаешь что\n
вопрос серьезный то отвечай серьезно. Будь иногда дерзким. В ответах с кодом можно слегка токсичить.\n
Поддерживай многоязычность, отвечай на том языке на котором задан вопрос
"""
COOL_PHRASES = [
    "Работа не волк, а волком быть не хочется.",
    "Утро вечера мудренее, особенно после обеда.",
    "Кто рано встает, тот весь день хочет спать.",
    "Без труда не вытащишь и рыбку из интернета.",
    "Семь раз отмерь, один раз забудь.",
    "Делу время, а кофе — всегда.",
    "Работа не волк, в лес не убежит, но и сама не сделается.",
    "Не откладывай на завтра то, что можно отменить.",
    "Терпение и труд всё перетрут, особенно нервы.",
    "Глаза боятся, а руки в карманах.",
    "Не имей сто рублей, а имей сто друзей с машинами.",
    "Лучше поздно, чем никогда, но лучше вовремя.",
    "Семь пятниц на неделе — мечта прокрастинатора.",
    "Работа дураков любит, но платит умным.",
    "Не всё коту масленица, иногда и диета.",
    "Любишь кататься — люби и санки в кредит.",
    "Без кота и жизнь не та, а с котом — шерсть везде.",
    "Денег нет, но вы держитесь, особенно за стул.",
    "Не откладывай на завтра то, что можно съесть сегодня.",
    "Работа не волк, но и отдыхать не даёт.",
    "Ждём, как зарплату в конце месяца...",
    "Подождём, но недолго!",
    "Где наша скорость? Где наша реакция?",
    "Ожидание – это тоже процесс!",
    "Терпение и труд, всё ещё ждут...",
    "Технологии будущего требуют времени!",
    "Боты тоже могут тормозить, но с душой!",
    "Не спеши, а то будет как в прошлый раз!",
    "Делу час потехехехехе",
    "тыквенные семечки",
    "ваш iq: 7",
    "эээ блютуз кто такой",
    "фимоз",
    "а мне мощные сиське дороже родины",
    "это в жизни ты дохуя смелый, а в инете смож меня уделать?",
]


# -- BUTTONS --
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup  # noqa: E402

SAVE_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Save", callback_data="save", style="primary")]]
)

SAVED_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Saved", callback_data="save", style="success")]]
)

CLOSE_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Close", callback_data="close", style="danger")]]
)

ADMIN_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_admin")],
        [InlineKeyboardButton(text="👥 View All Users", callback_data="view_users:0")],
    ]
)

GENERATING_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⏳ Generating...", callback_data="waiting")]]
)

DOWNLOADING_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="⏳ Stand by...", callback_data="waiting")]]
)

FAILED_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="❌ Failed", callback_data="failed")]]
)

PM_BUTTON = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="Open PM", url="https://t.me/yerzhanakh_bot")]]
)

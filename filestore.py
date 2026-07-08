# ─── SINGLE FILE BOT (telebot) ──────────────────────────────────────────────
# All features: force-join, coins, referral, leaderboard, redeem, admin.
# Keyboards defined in JSON with "style" attributes and stylish button texts.
# All actions via buttons – no typing except redeem codes / file content.

import logging
import sqlite3
import random
import string
import re
import json
from datetime import datetime

import telebot
from telebot import types

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── STYLISH TEXT FUNCTION ─────────────────────────────────────────────────────
def to_stylish(text: str) -> str:
    small = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'ꜱ','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'}
    def w(word):
        if not word: return word
        first = word[0].upper() if word[0].isalpha() else word[0]
        return first + ''.join(small.get(ch.lower(), ch) for ch in word[1:])
    return '\n'.join(' '.join(w(wd) for wd in line.split(' ')) for line in text.split('\n'))

def style_text(text: str) -> str:
    parts = re.split(r'(<[^>]*>)', text)
    styled = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            styled.append(part)
        else:
            styled.append(to_stylish(part))
    return ''.join(styled)

# ─── NORMALIZE STYLISH TEXT ────────────────────────────────────────────────
# Reverse mapping of small caps → ASCII uppercase (from to_stylish dict)
SMALL_TO_ASCII = {
    'ᴀ': 'A', 'ʙ': 'B', 'ᴄ': 'C', 'ᴅ': 'D', 'ᴇ': 'E', 'ꜰ': 'F', 'ɢ': 'G',
    'ʜ': 'H', 'ɪ': 'I', 'ᴊ': 'J', 'ᴋ': 'K', 'ʟ': 'L', 'ᴍ': 'M', 'ɴ': 'N',
    'ᴏ': 'O', 'ᴘ': 'P', 'ǫ': 'Q', 'ʀ': 'R', 'ꜱ': 'S', 'ᴛ': 'T', 'ᴜ': 'U',
    'ᴠ': 'V', 'ᴡ': 'W', 'x': 'X', 'ʏ': 'Y', 'ᴢ': 'Z'
}

def normalize_code(raw: str) -> str:
    """Remove spaces, convert to uppercase, and map small‑caps to ASCII."""
    raw = raw.strip()
    for small, ascii_letter in SMALL_TO_ASCII.items():
        raw = raw.replace(small, ascii_letter)
    return raw.replace(" ", "").upper()

# ─── CONFIG ────────────────────────────────────────────────────────────────────
class Config:
    BOT_TOKEN = "8856009781:AAGljaPCR2OFXmP-ClwaNzSloM_5yeYrM5k"  # Replace with your token
    BOT_NAME  = "OS FILE STORE"
    ADMIN_IDS = ["8291767314"]
    OWNER_USERNAME = "khannhamzaa"
    REFERRAL_COINS     = 5
    NEW_USER_REF_COINS = 2
    FORCE_CHANNELS = ["os_codex", "os_codeex", "os_codexx", "os_coddex"]

# ─── DATABASE ─────────────────────────────────────────────────────────────────
DB_PATH = "filestore.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                coins       INTEGER DEFAULT 0,
                joined_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                price       INTEGER NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                file_id     INTEGER,
                purchased_at TEXT
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS redeem_codes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT UNIQUE,
                coins       INTEGER,
                max_uses    INTEGER,
                used_count  INTEGER DEFAULT 0,
                created_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS code_uses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id     INTEGER,
                user_id     INTEGER,
                used_at     TEXT
            );
        """)
        self.conn.commit()

    def add_user(self, user_id, username):
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone():
            return False
        c.execute(
            "INSERT INTO users (user_id, username, coins, joined_at) VALUES (?,?,?,?)",
            (user_id, username, 0, datetime.now().isoformat())
        )
        self.conn.commit()
        return True

    def user_exists(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        return c.fetchone() is not None

    def find_user(self, uid_or_name):
        c = self.conn.cursor()
        if str(uid_or_name).isdigit():
            c.execute("SELECT * FROM users WHERE user_id=?", (int(uid_or_name),))
        else:
            c.execute("SELECT * FROM users WHERE username=?", (uid_or_name,))
        row = c.fetchone()
        return dict(row) if row else None

    def get_all_users(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users ORDER BY coins DESC")
        return [dict(r) for r in c.fetchall()]

    def get_coins(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        return row['coins'] if row else 0

    def add_coins(self, user_id, amount):
        c = self.conn.cursor()
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, user_id))
        self.conn.commit()

    def deduct_coins(self, user_id, amount):
        c = self.conn.cursor()
        c.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amount, user_id))
        self.conn.commit()

    def add_file(self, name, price, content):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO files (name, price, content, created_at) VALUES (?,?,?,?)",
            (name, price, content, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_all_files(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM files ORDER BY id")
        return [dict(r) for r in c.fetchall()]

    def get_file(self, file_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM files WHERE id=?", (file_id,))
        row = c.fetchone()
        return dict(row) if row else None

    def remove_file(self, file_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM files WHERE id=?", (file_id,))
        self.conn.commit()

    def record_purchase(self, user_id, file_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO purchases (user_id, file_id, purchased_at) VALUES (?,?,?)",
            (user_id, file_id, datetime.now().isoformat())
        )
        self.conn.commit()

    def already_purchased(self, user_id, file_id):
        c = self.conn.cursor()
        c.execute(
            "SELECT id FROM purchases WHERE user_id=? AND file_id=?",
            (user_id, file_id)
        )
        return c.fetchone() is not None

    def get_purchase_count(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM purchases WHERE user_id=?", (user_id,))
        return c.fetchone()['cnt']

    def record_referral(self, referrer_id, referred_id):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO referrals (referrer_id, referred_id, created_at) VALUES (?,?,?)",
            (referrer_id, referred_id, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_referral_count(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id=?", (user_id,))
        return c.fetchone()['cnt']

    def create_redeem_code(self, coins, max_uses):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO redeem_codes (code, coins, max_uses, created_at) VALUES (?,?,?,?)",
            (code, coins, max_uses, datetime.now().isoformat())
        )
        self.conn.commit()
        return code

    def use_redeem_code(self, code, user_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM redeem_codes WHERE code=?", (code,))
        row = c.fetchone()
        if not row:
            return "not_found"
        row = dict(row)
        if row['used_count'] >= row['max_uses']:
            return "expired"
        c.execute(
            "SELECT id FROM code_uses WHERE code_id=? AND user_id=?",
            (row['id'], user_id)
        )
        if c.fetchone():
            return "already_used"
        c.execute(
            "UPDATE redeem_codes SET used_count = used_count + 1 WHERE id=?",
            (row['id'],)
        )
        c.execute(
            "INSERT INTO code_uses (code_id, user_id, used_at) VALUES (?,?,?)",
            (row['id'], user_id, datetime.now().isoformat())
        )
        self.conn.commit()
        self.add_coins(user_id, row['coins'])
        return row['coins']

    def get_leaderboard(self):
        c = self.conn.cursor()
        c.execute("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10")
        return [dict(r) for r in c.fetchall()]

    def get_stats(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users")
        users = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM files")
        files = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM purchases")
        purchases = c.fetchone()['cnt']
        c.execute("SELECT COUNT(*) as cnt FROM redeem_codes WHERE used_count < max_uses")
        codes = c.fetchone()['cnt']
        return {"users": users, "files": files, "purchases": purchases, "codes": codes}

# ─── INSTANTIATE ──────────────────────────────────────────────────────────────
db = Database()
config = Config()
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")

# ─── USER STATE MANAGEMENT ──────────────────────────────────────────────────
# Each user can have a state (string) and associated data (dict)
user_states = {}  # user_id -> {"state": str, "data": dict}

def set_state(user_id, state, data=None):
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id]["state"] = state
    user_states[user_id]["data"] = data or {}

def get_state(user_id):
    return user_states.get(user_id, {}).get("state")

def get_data(user_id):
    return user_states.get(user_id, {}).get("data", {})

def clear_state(user_id):
    if user_id in user_states:
        del user_states[user_id]

# ─── KEYBOARD DEFINITIONS (JSON) ──────────────────────────────────────────
MAIN_KEYBOARD_JSON = {
    "keyboard": [
        [
            {"text": "🗂️ Bᴜʏ Fɪʟᴇs", "style": "primary"},
            {"text": "🪙 Mʏ Cᴏɪɴs", "style": "success"}
        ],
        [
            {"text": "🔗 Rᴇғᴇʀʀᴀʟ Lɪɴᴋ", "style": "primary"},
            {"text": "🏆 Lᴇᴀᴅᴇʀʙᴏᴀʀᴅ", "style": "success"}
        ],
        [
            {"text": "🎁 Rᴇᴅᴇᴇᴍ Cᴏᴅᴇ", "style": "danger"},
            {"text": "📞 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ", "style": "primary"}
        ],
        [
            {"text": "❓ Hᴇʟᴘ", "style": "primary"},
            {"text": "❌ Cᴀɴᴄᴇʟ", "style": "danger"}
        ]
    ],
    "resize_keyboard": True
}

ADMIN_KEYBOARD_JSON = {
    "keyboard": [
        [
            {"text": "➕ Aᴅᴅ Fɪʟᴇ", "style": "success"},
            {"text": "🗑️ Rᴇᴍᴏᴠᴇ Fɪʟᴇ", "style": "danger"}
        ],
        [
            {"text": "🎫 Cʀᴇᴀᴛᴇ Rᴇᴅᴇᴇᴍ Cᴏᴅᴇ", "style": "primary"},
            {"text": "💰 Gɪᴠᴇ Cᴏɪɴs", "style": "success"}
        ],
        [
            {"text": "📢 Bʀᴏᴀᴅᴄᴀsᴛ", "style": "primary"},
            {"text": "📊 Bᴏᴛ Sᴛᴀᴛs", "style": "success"}
        ],
        [
            {"text": "👥 Aʟʟ Usᴇʀs", "style": "primary"},
            {"text": "🔙 Bᴀᴄᴋ Tᴏ Mᴀɪɴ", "style": "danger"}
        ],
        [
            {"text": "❓ Hᴇʟᴘ", "style": "primary"},
            {"text": "❌ Cᴀɴᴄᴇʟ", "style": "danger"}
        ]
    ],
    "resize_keyboard": True
}

FORCE_SUBSCRIBE_KEYBOARD_JSON = {
    "inline_keyboard": [
        [
            {"text": "💞 Click", "url": "https://t.me/os_codex", "style": "primary"},
            {"text": "💞 Click", "url": "https://t.me/os_codexx", "style": "primary"}
        ],
        [
            {"text": "💞 Click", "url": "https://t.me/os_codeex", "style": "primary"},
            {"text": "💞 Click", "url": "https://t.me/os_coddex", "style": "primary"}
        ],
        [
            {"text": "✔️ Verify", "callback_data": "verify_", "style": "success"}
        ]
    ]
}

# ─── KEYBOARD BUILDERS ────────────────────────────────────────────────────────
def build_reply_keyboard_from_json(json_data) -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=json_data.get('resize_keyboard', True))
    for row in json_data['keyboard']:
        keyboard.row(*[types.KeyboardButton(btn['text']) for btn in row])
    return keyboard

def build_inline_keyboard_from_json(json_data) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    for row in json_data['inline_keyboard']:
        buttons = []
        for btn in row:
            if 'url' in btn:
                buttons.append(types.InlineKeyboardButton(btn['text'], url=btn['url']))
            elif 'callback_data' in btn:
                buttons.append(types.InlineKeyboardButton(btn['text'], callback_data=btn['callback_data']))
        keyboard.row(*buttons)
    return keyboard

def build_dynamic_inline_keyboard(buttons, columns=1) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    for i in range(0, len(buttons), columns):
        row_buttons = []
        for btn in buttons[i:i+columns]:
            if 'url' in btn:
                row_buttons.append(types.InlineKeyboardButton(btn['text'], url=btn['url']))
            elif 'callback_data' in btn:
                row_buttons.append(types.InlineKeyboardButton(btn['text'], callback_data=btn['callback_data']))
        keyboard.row(*row_buttons)
    return keyboard

def get_main_keyboard(user_id) -> types.ReplyKeyboardMarkup:
    if str(user_id) in config.ADMIN_IDS:
        return build_reply_keyboard_from_json(ADMIN_KEYBOARD_JSON)
    else:
        return build_reply_keyboard_from_json(MAIN_KEYBOARD_JSON)

def get_force_subscribe_keyboard(ref_arg: str = "") -> types.InlineKeyboardMarkup:
    import copy
    data = copy.deepcopy(FORCE_SUBSCRIBE_KEYBOARD_JSON)
    for row in data['inline_keyboard']:
        for btn in row:
            if 'callback_data' in btn and btn['callback_data'].startswith('verify_'):
                btn['callback_data'] = f"verify_{ref_arg}" if ref_arg else "verify_"
    return build_inline_keyboard_from_json(data)

# ─── FORCE JOIN FUNCTIONS ─────────────────────────────────────────────────────
def is_user_joined(user_id: int) -> bool:
    for ch in config.FORCE_CHANNELS:
        try:
            chat = ch if ch.startswith("@") else f"@{ch}"
            member = bot.get_chat_member(chat, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def send_join_prompt(message, ref_arg: str = ""):
    user_id = message.from_user.id
    not_joined = []
    for ch in config.FORCE_CHANNELS:
        try:
            chat = ch if ch.startswith("@") else f"@{ch}"
            member = bot.get_chat_member(chat, user_id)
            if member.status in ["left", "kicked"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    if not not_joined:
        return True
    ch_text = "\n".join(f"• @{ch}" for ch in not_joined)
    text = (
        "⚠️ <b>Access Denied</b>\n\n"
        "❌ You must join these channels first:\n\n"
        f"{ch_text}\n\n"
        "✅ After joining, tap <b>Verify</b> below."
    )
    kb = get_force_subscribe_keyboard(ref_arg)
    bot.send_message(message.chat.id, style_text(text), reply_markup=kb)
    return False

def subscription_required(message) -> bool:
    user_id = message.from_user.id
    if not is_user_joined(user_id):
        send_join_prompt(message)
        return False
    return True

# ─── BOT HANDLERS ──────────────────────────────────────────────────────────

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    user_id = user.id
    ref_arg = ""
    if message.text and ' ' in message.text:
        ref_arg = message.text.split(' ', 1)[1]

    if not is_user_joined(user_id):
        send_join_prompt(message, ref_arg)
        return

    is_new = db.add_user(user_id, user.username or user.first_name)
    if is_new and ref_arg and ref_arg.isdigit():
        ref_uid = int(ref_arg)
        if ref_uid != user_id and db.user_exists(ref_uid):
            db.add_coins(ref_uid, config.REFERRAL_COINS)
            db.record_referral(ref_uid, user_id)
            db.add_coins(user_id, config.NEW_USER_REF_COINS)
            try:
                bot.send_message(
                    ref_uid,
                    style_text(
                        f"🎉 <b>New Referral!</b>\n\n"
                        f"✅ Someone joined via your link!\n"
                        f"🪙 You earned <b>{config.REFERRAL_COINS} Coin</b>!"
                    )
                )
            except:
                pass

    coins = db.get_coins(user_id)
    welcome = (
        f"╔══════════════════════╗\n"
        f"       🏪 <b>OS FILE STORE</b> 🏪\n"
        f"╚══════════════════════╝\n\n"
        f"👋 Hey <b>{user.first_name}</b>, Welcome!\n\n"
        f"🔥 The #1 place to grab\n"
        f"   premium files at low prices.\n\n"
        f"🪙 Balance  :  <b>{coins} Coins</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗂️ Buy Files  |  🔗 Refer & Earn\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    kb = get_main_keyboard(user_id)
    bot.send_message(message.chat.id, style_text(welcome), reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_"))
def verify_callback(call):
    user_id = call.from_user.id
    ref_arg = call.data.replace("verify_", "")

    if not is_user_joined(user_id):
        bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)
        send_join_prompt(call.message, ref_arg)
        return

    is_new = db.add_user(user_id, call.from_user.username or call.from_user.first_name)
    if is_new and ref_arg and ref_arg.isdigit():
        ref_uid = int(ref_arg)
        if ref_uid != user_id and db.user_exists(ref_uid):
            db.add_coins(ref_uid, config.REFERRAL_COINS)
            db.record_referral(ref_uid, user_id)
            db.add_coins(user_id, config.NEW_USER_REF_COINS)
            try:
                bot.send_message(
                    ref_uid,
                    style_text(
                        f"🎉 <b>New Referral!</b>\n\n"
                        f"✅ Someone joined via your link!\n"
                        f"🪙 You earned <b>{config.REFERRAL_COINS} Coin</b>!"
                    )
                )
            except:
                pass

    coins = db.get_coins(user_id)
    welcome = (
        f"╔══════════════════════╗\n"
        f"      🏪 <b>OS FILE STORE</b> 🏪\n"
        f"╚══════════════════════╝\n\n"
        f"👋 Hey <b>{call.from_user.first_name}</b>, Welcome!\n\n"
        f"🔥 The #1 place to grab\n"
        f"   premium files at low prices.\n\n"
        f"🪙 Balance  :  <b>{coins} Coins</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗂️ Buy Files  |  🔗 Refer & Earn\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    kb = get_main_keyboard(user_id)
    bot.edit_message_text(style_text(welcome), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    bot.answer_callback_query(call.id, "✅ Verified!")

# ─── BUY FILES ──────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🗂️ Bᴜʏ Fɪʟᴇs")
def buy_files(message):
    if not subscription_required(message):
        return
    files = db.get_all_files()
    if not files:
        bot.send_message(message.chat.id, style_text("😕 No files available right now. Check back later!"))
        return
    buttons = []
    for f in files:
        buttons.append({
            "text": f"📄 {f['name']}  ·  🪙 {f['price']} Coins",
            "callback_data": f"buy_file_{f['id']}",
            "style": "primary"
        })
    buttons.append({"text": "❌ Cancel", "callback_data": "cancel", "style": "danger"})
    kb = build_dynamic_inline_keyboard(buttons, columns=1)
    bot.send_message(
        message.chat.id,
        style_text("🗂️ <b>Select a file to buy:</b>\n\nTap a file to purchase it with your coins."),
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_file_") or call.data == "cancel")
def buy_file_callback(call):
    user_id = call.from_user.id
    if call.data == "cancel":
        bot.edit_message_text(style_text("❌ Cancelled."), chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    file_id = int(call.data.replace("buy_file_", ""))
    file = db.get_file(file_id)
    if not file:
        bot.edit_message_text(style_text("❌ File not found."), chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    user_coins = db.get_coins(user_id)
    if db.already_purchased(user_id, file['id']):
        bot.edit_message_text(
            style_text(f"✅ You already own <b>{file['name']}</b>!\n⬇️ Here is your file again:"),
            chat_id=call.message.chat.id, message_id=call.message.message_id
        )
        send_file_to_user(call.message.chat.id, file)
        bot.answer_callback_query(call.id)
        return
    if user_coins < file['price']:
        bot.edit_message_text(
            style_text(
                f"❌ <b>Not enough coins!</b>\n\n"
                f"🪙 Your coins  : <b>{user_coins}</b>\n"
                f"💰 Required    : <b>{file['price']}</b>\n"
                f"📉 Shortfall   : <b>{file['price'] - user_coins}</b>\n\n"
                f"💡 Share your 🔗 Referral Link or use a 🎁 Redeem Code to earn more!"
            ),
            chat_id=call.message.chat.id, message_id=call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    db.deduct_coins(user_id, file['price'])
    db.record_purchase(user_id, file['id'])
    remaining = db.get_coins(user_id)
    bot.edit_message_text(
        style_text(
            f"✅ <b>Purchase Successful!</b>\n\n"
            f"📦 File      : <b>{file['name']}</b>\n"
            f"💸 Paid      : <b>{file['price']} Coins</b>\n"
            f"🪙 Remaining : <b>{remaining} Coins</b>\n\n"
            f"⬇️ Your file is below:"
        ),
        chat_id=call.message.chat.id, message_id=call.message.message_id
    )
    send_file_to_user(call.message.chat.id, file)
    bot.answer_callback_query(call.id, "✅ Purchased!")

def send_file_to_user(chat_id, file):
    content = file['content']
    if content.startswith("FILE:"):
        bot.send_document(
            chat_id,
            document=content.replace("FILE:", ""),
            caption=style_text(f"📦 <b>{file['name']}</b>")
        )
    else:
        bot.send_message(
            chat_id,
            text=style_text(f"📦 <b>{file['name']}</b>\n\n{content}")
        )

# ─── MY COINS ──────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🪙 Mʏ Cᴏɪɴs")
def my_coins(message):
    if not subscription_required(message):
        return
    user_id = message.from_user.id
    coins = db.get_coins(user_id)
    refs = db.get_referral_count(user_id)
    purchases = db.get_purchase_count(user_id)
    bot.send_message(
        message.chat.id,
        style_text(
            f"🪙 <b>Your Coins Dashboard</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"💰 Current Coins   : <b>{coins}</b>\n"
            f"👥 Total Referrals : <b>{refs}</b>\n"
            f"🛒 Total Purchases : <b>{purchases}</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"💡 Each referral gives you <b>{config.REFERRAL_COINS} Coin</b>!\n"
            f"🎁 New users you refer get <b>{config.NEW_USER_REF_COINS} Coins</b> too!"
        )
    )

# ─── REFERRAL LINK ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🔗 Rᴇғᴇʀʀᴀʟ Lɪɴᴋ")
def referral_link(message):
    if not subscription_required(message):
        return
    user_id = message.from_user.id
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={user_id}"
    refs = db.get_referral_count(user_id)
    bot.send_message(
        message.chat.id,
        style_text(
            f"🔗 <b>Your Referral Link</b>\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"<a href='{link}'>{link}</a>\n\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Referrals    : <b>{refs}</b>\n"
            f"🪙 You earn per refer : <b>{config.REFERRAL_COINS} Coin</b>\n"
            f"🎁 New user gets      : <b>{config.NEW_USER_REF_COINS} Coins</b>\n\n"
            f"📢 Share your link and earn automatically!"
        )
    )

# ─── LEADERBOARD ────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🏆 Lᴇᴀᴅᴇʀʙᴏᴀʀᴅ")
def leaderboard(message):
    if not subscription_required(message):
        return
    top = db.get_leaderboard()
    if not top:
        bot.send_message(message.chat.id, style_text("😕 No data yet. Be the first on the leaderboard!"))
        return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text = "🏆 <b>Top 10 Leaderboard</b> (Most Coins)\n━━━━━━━━━━━━━━━━━\n\n"
    for i, row in enumerate(top[:10]):
        text += f"{medals[i]}  <b>{row['username']}</b>  —  🪙 {row['coins']}\n"
    bot.send_message(message.chat.id, style_text(text))

# ─── REDEEM CODE ────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🎁 Rᴇᴅᴇᴇᴍ Cᴏᴅᴇ")
def redeem_start(message):
    if not subscription_required(message):
        return
    set_state(message.from_user.id, "REDEEM_WAITING")
    bot.send_message(message.chat.id, style_text("🎁 <b>Enter Redeem Code</b>\n\nType your code below 👇"))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "REDEEM_WAITING")
def redeem_process(message):
    user_id = message.from_user.id
    raw_code = message.text.strip()
    code = normalize_code(raw_code)          # <-- Normalize here
    result = db.use_redeem_code(code, user_id)
    kb = get_main_keyboard(user_id)
    msgs = {
        "not_found":    "❌ Invalid code! Please check and try again.",
        "already_used": "⚠️ You have already used this code!",
        "expired":      "⌛ This code has expired or reached its usage limit.",
    }
    if result in msgs:
        bot.send_message(message.chat.id, style_text(msgs[result]), reply_markup=kb)
    else:
        bot.send_message(
            message.chat.id,
            style_text(
                f"✅ <b>Code Redeemed Successfully!</b>\n\n"
                f"🪙 <b>+{result} Coins</b> added to your account!"
            ),
            reply_markup=kb
        )
    clear_state(user_id)

# ─── CONTACT OWNER ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "📞 Cᴏɴᴛᴀᴄᴛ Oᴡɴᴇʀ")
def contact_owner(message):
    if not subscription_required(message):
        return
    if not config.OWNER_USERNAME:
        bot.send_message(message.chat.id, style_text("😕 Owner contact is not available right now."))
        return
    owner_link = f"https://t.me/{config.OWNER_USERNAME}"
    bot.send_message(
        message.chat.id,
        style_text(
            f"📞 <b>Contact Owner</b>\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <a href='{owner_link}'>@{config.OWNER_USERNAME}</a>\n\n"
            f"⏰ Expect a reply within 24 hours."
        )
    )

# ─── HELP ──────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "❓ Hᴇʟᴘ")
def help_command(message):
    if not subscription_required(message):
        return
    help_text = (
        "📖 <b>Bot Help</b>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
        "🗂️ <b>Buy Files</b> – Purchase files using your coins.\n"
        "🪙 <b>My Coins</b> – Check your balance, referrals & purchases.\n"
        "🔗 <b>Referral Link</b> – Get your unique link and earn coins.\n"
        "🏆 <b>Leaderboard</b> – See top users by coins.\n"
        "🎁 <b>Redeem Code</b> – Enter a code to get free coins.\n"
        "📞 <b>Contact Owner</b> – Reach the bot owner.\n\n"
        "💡 <b>Tip</b>: Refer friends to earn coins automatically!"
    )
    bot.send_message(message.chat.id, style_text(help_text))

# ─── CANCEL BUTTON ────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "❌ Cᴀɴᴄᴇʟ")
def cancel(message):
    user_id = message.from_user.id
    clear_state(user_id)
    kb = get_main_keyboard(user_id)
    bot.send_message(message.chat.id, style_text("❌ Action cancelled."), reply_markup=kb)

# ─── ADMIN: ADD FILE ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "➕ Aᴅᴅ Fɪʟᴇ")
def admin_add_file(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    set_state(message.from_user.id, "ADD_FILE_NAME")
    bot.send_message(message.chat.id, style_text("➕ <b>Add New File — Step 1/3</b>\n\n📝 Enter the <b>file name</b>:"))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "ADD_FILE_NAME")
def add_file_name(message):
    data = get_data(message.from_user.id)
    data['file_name'] = message.text.strip()
    set_state(message.from_user.id, "ADD_FILE_PRICE", data)
    bot.send_message(message.chat.id, style_text("➕ <b>Add New File — Step 2/3</b>\n\n💰 Enter the <b>price</b> in coins:"))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "ADD_FILE_PRICE")
def add_file_price(message):
    try:
        price = int(message.text.strip())
        data = get_data(message.from_user.id)
        data['file_price'] = price
        set_state(message.from_user.id, "ADD_FILE_CONTENT", data)
        bot.send_message(
            message.chat.id,
            style_text(
                "➕ <b>Add New File — Step 3/3</b>\n\n"
                "📤 Send the <b>file content</b>:\n\n"
                "• <b>Text / Link</b> → Type or paste it\n"
                "• <b>Document</b> → Upload it directly"
            )
        )
    except:
        bot.send_message(message.chat.id, style_text("❌ Invalid! Please enter a valid number."))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "ADD_FILE_CONTENT", content_types=['text', 'document'])
def add_file_content(message):
    data = get_data(message.from_user.id)
    name = data.get('file_name')
    price = data.get('file_price')
    if not name or price is None:
        bot.send_message(message.chat.id, style_text("❌ Something went wrong. Please start over."))
        clear_state(message.from_user.id)
        return
    if message.document:
        content = f"FILE:{message.document.file_id}"
    else:
        content = message.text.strip()
    db.add_file(name, price, content)
    kb = get_main_keyboard(message.from_user.id)
    bot.send_message(
        message.chat.id,
        style_text(f"✅ <b>File Added!</b>\n\n📄 Name  : <b>{name}</b>\n🪙 Price : <b>{price} Coins</b>"),
        reply_markup=kb
    )
    clear_state(message.from_user.id)

# ─── ADMIN: REMOVE FILE ─────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🗑️ Rᴇᴍᴏᴠᴇ Fɪʟᴇ")
def admin_remove_file(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    files = db.get_all_files()
    if not files:
        bot.send_message(message.chat.id, style_text("😕 No files to remove."))
        return
    buttons = []
    for f in files:
        buttons.append({
            "text": f"🗑️ {f['name']}  ·  🪙 {f['price']}",
            "callback_data": f"del_file_{f['id']}",
            "style": "danger"
        })
    buttons.append({"text": "❌ Cancel", "callback_data": "cancel", "style": "danger"})
    kb = build_dynamic_inline_keyboard(buttons, columns=1)
    bot.send_message(message.chat.id, style_text("🗑️ <b>Select a file to remove:</b>"), reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_file_") or call.data == "cancel")
def remove_file_callback(call):
    if str(call.from_user.id) not in config.ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Admin only!", show_alert=True)
        return
    if call.data == "cancel":
        bot.edit_message_text(style_text("❌ Cancelled."), chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    file_id = int(call.data.replace("del_file_", ""))
    file = db.get_file(file_id)
    db.remove_file(file_id)
    bot.edit_message_text(
        style_text(f"✅ <b>{file['name']}</b> removed successfully!"),
        chat_id=call.message.chat.id, message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id, "🗑️ Removed!")

# ─── ADMIN: CREATE REDEEM CODE ─────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🎫 Cʀᴇᴀᴛᴇ Rᴇᴅᴇᴇᴍ Cᴏᴅᴇ")
def admin_create_code(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    set_state(message.from_user.id, "CREATE_CODE_COINS")
    bot.send_message(message.chat.id, style_text("🎫 <b>Create Code — Step 1/2</b>\n\n🪙 How many <b>coins</b> should this code give?"))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "CREATE_CODE_COINS")
def create_code_coins(message):
    try:
        coins = int(message.text.strip())
        data = get_data(message.from_user.id)
        data['code_coins'] = coins
        set_state(message.from_user.id, "CREATE_CODE_USES", data)
        bot.send_message(message.chat.id, style_text("🎫 <b>Create Code — Step 2/2</b>\n\n🔢 How many times can it be used? (max uses)"))
    except:
        bot.send_message(message.chat.id, style_text("❌ Invalid! Enter a valid number."))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "CREATE_CODE_USES")
def create_code_uses(message):
    try:
        max_uses = int(message.text.strip())
        data = get_data(message.from_user.id)
        coins = data.get('code_coins')
        code = db.create_redeem_code(coins, max_uses)
        kb = get_main_keyboard(message.from_user.id)
        bot.send_message(
            message.chat.id,
            style_text(
                f"✅ <b>Redeem Code Created!</b>\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🎫 Code      : <code>{code}</code>\n"
                f"🪙 Coins     : <b>{coins}</b>\n"
                f"🔢 Max Uses  : <b>{max_uses}</b>"
            ),
            reply_markup=kb
        )
        clear_state(message.from_user.id)
    except:
        bot.send_message(message.chat.id, style_text("❌ Invalid! Enter a valid number."))

# ─── ADMIN: GIVE COINS ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "💰 Gɪᴠᴇ Cᴏɪɴs")
def admin_give_coins(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    set_state(message.from_user.id, "GIVE_COINS_USER")
    bot.send_message(message.chat.id, style_text("💰 <b>Give Coins — Step 1/2</b>\n\n👤 Enter user <b>ID or Username</b>:"))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "GIVE_COINS_USER")
def give_coins_user(message):
    user = db.find_user(message.text.strip().replace("@", ""))
    if not user:
        bot.send_message(message.chat.id, style_text("❌ User not found!"))
        clear_state(message.from_user.id)
        return
    data = get_data(message.from_user.id)
    data['target_user'] = user
    set_state(message.from_user.id, "GIVE_COINS_AMOUNT", data)
    bot.send_message(
        message.chat.id,
        style_text(
            f"✅ <b>User Found!</b>\n\n"
            f"👤 {user['username']}  |  🪙 {user['coins']} Coins\n\n"
            f"💰 <b>Step 2/2</b> — How many coins to give?"
        )
    )

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "GIVE_COINS_AMOUNT")
def give_coins_amount(message):
    try:
        amount = int(message.text.strip())
        data = get_data(message.from_user.id)
        user = data['target_user']
        db.add_coins(user['user_id'], amount)
        new_bal = db.get_coins(user['user_id'])
        kb = get_main_keyboard(message.from_user.id)
        bot.send_message(
            message.chat.id,
            style_text(
                f"✅ <b>Done!</b>  🪙 {amount} Coins → <b>{user['username']}</b>\n"
                f"New balance: <b>{new_bal} Coins</b>"
            ),
            reply_markup=kb
        )
        try:
            bot.send_message(
                user['user_id'],
                style_text(
                    f"🎉 Admin added <b>{amount} Coins</b> to your account!\n"
                    f"🪙 New balance: <b>{new_bal} Coins</b>"
                )
            )
        except:
            pass
        clear_state(message.from_user.id)
    except:
        bot.send_message(message.chat.id, style_text("❌ Invalid! Enter a valid number."))

# ─── ADMIN: BROADCAST ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "📢 Bʀᴏᴀᴅᴄᴀsᴛ")
def admin_broadcast(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    set_state(message.from_user.id, "BROADCAST_WAITING")
    bot.send_message(message.chat.id, style_text("📢 Type the message to broadcast to all users:"))

@bot.message_handler(func=lambda msg: get_state(msg.from_user.id) == "BROADCAST_WAITING")
def do_broadcast(message):
    msg_text = message.text.strip()
    users = db.get_all_users()
    success = fail = 0
    status_msg = bot.send_message(message.chat.id, style_text("⏳ Sending broadcast..."))
    for u in users:
        try:
            bot.send_message(u['user_id'], style_text(f"📢 <b>Announcement</b>\n\n{msg_text}"))
            success += 1
        except:
            fail += 1
    bot.edit_message_text(
        style_text(
            f"✅ <b>Broadcast Complete!</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"✔️ Sent   : <b>{success}</b>\n"
            f"❌ Failed : <b>{fail}</b>\n"
            f"👥 Total  : <b>{len(users)}</b>"
        ),
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id
    )
    clear_state(message.from_user.id)

# ─── ADMIN: STATS ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "📊 Bᴏᴛ Sᴛᴀᴛs")
def admin_stats(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    s = db.get_stats()
    bot.send_message(
        message.chat.id,
        style_text(
            f"📊 <b>Bot Statistics</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users     : <b>{s['users']}</b>\n"
            f"📁 Total Files     : <b>{s['files']}</b>\n"
            f"🛒 Total Purchases : <b>{s['purchases']}</b>\n"
            f"🎫 Active Codes    : <b>{s['codes']}</b>"
        )
    )

# ─── ADMIN: ALL USERS ──────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "👥 Aʟʟ Usᴇʀs")
def admin_all_users(message):
    if str(message.from_user.id) not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Admin only.")
        return
    users = db.get_all_users()
    text = f"👥 <b>All Users ({len(users)} total)</b>\n━━━━━━━━━━━━━━━━━\n\n"
    for u in users[:50]:
        text += f"• <code>{u['user_id']}</code>  @{u['username']}  🪙{u['coins']}\n"
    if len(users) > 50:
        text += f"\n... and {len(users)-50} more."
    bot.send_message(message.chat.id, style_text(text))

# ─── BACK TO MAIN ──────────────────────────────────────────────────────────
@bot.message_handler(func=lambda msg: msg.text == "🔙 Bᴀᴄᴋ Tᴏ Mᴀɪɴ")
def back_to_main(message):
    kb = get_main_keyboard(message.from_user.id)
    bot.send_message(message.chat.id, style_text("🏠 Back to main menu!"), reply_markup=kb)

# ─── CATCH ALL OTHER MESSAGES ─────────────────────────────────────────────
@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    # Ignore any other text
    pass

# ─── MAIN ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("✅ Bot is running with telebot and all commands as buttons.")
    bot.infinity_polling()

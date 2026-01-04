import os
import time
import secrets
import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_DB_URI")

ADMIN_ID = 6356015122
ADMIN_CONTACT = "@Kaito_3_2"

FREE_DAYS = 2
DEFAULT_LIMIT = 50

# ─────────────────────────────
# DATABASE
# ─────────────────────────────
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["MusicAPI_DB12"]
keys_col = db["api_users"]

# ─────────────────────────────
# BOT
# ─────────────────────────────
app = Client(
    "apikeybot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ─────────────────────────────
# HELPERS
# ─────────────────────────────
def generate_key():
    return "sud-" + secrets.token_hex(8)

def now_ts():
    return int(time.time())

def days_to_ts(days):
    return now_ts() + days * 86400

# ─────────────────────────────
# COMMANDS
# ─────────────────────────────
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "👋 **welcome to sudeep music api bot**\n\n"
        "• use `/getapi` to generate api key\n"
        f"• free access for {FREE_DAYS} days\n\n"
        f"support: {ADMIN_CONTACT}"
    )

@app.on_message(filters.command("getapi"))
async def get_api(_, m: Message):
    uid = m.from_user.id

    doc = await keys_col.find_one({"user_id": uid})
    if doc:
        exp = datetime.datetime.fromtimestamp(doc["expires_at"])
        await m.reply(
            f"🔑 **your api key**\n\n"
            f"`{doc['api_key']}`\n\n"
            f"expires: `{exp}`\n"
            f"daily limit: `{doc['daily_limit']}`"
        )
        return

    api_key = generate_key()
    doc = {
        "user_id": uid,
        "api_key": api_key,
        "expires_at": days_to_ts(FREE_DAYS),
        "daily_limit": DEFAULT_LIMIT,
        "used_today": 0,
        "last_reset": str(datetime.date.today()),
        "active": True
    }

    await keys_col.insert_one(doc)

    await m.reply(
        "✅ **api key generated**\n\n"
        f"`{api_key}`\n\n"
        f"valid for {FREE_DAYS} days\n"
        f"daily limit: {DEFAULT_LIMIT}"
    )

@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_panel(_, m: Message):
    await m.reply(
        "🛠 **admin panel**\n\n"
        "/setlimit user_id limit\n"
        "/extend user_id days\n"
        "/disable user_id"
    )

@app.on_message(filters.command("setlimit") & filters.user(ADMIN_ID))
async def setlimit(_, m: Message):
    try:
        _, uid, limit = m.text.split()
        await keys_col.update_one(
            {"user_id": int(uid)},
            {"$set": {"daily_limit": int(limit)}}
        )
        await m.reply("✅ limit updated")
    except:
        await m.reply("usage: /setlimit user_id limit")

@app.on_message(filters.command("extend") & filters.user(ADMIN_ID))
async def extend(_, m: Message):
    try:
        _, uid, days = m.text.split()
        uid = int(uid)
        days = int(days)

        doc = await keys_col.find_one({"user_id": uid})
        if not doc:
            return await m.reply("user not found")

        await keys_col.update_one(
            {"user_id": uid},
            {"$set": {"expires_at": doc["expires_at"] + days * 86400}}
        )
        await m.reply("✅ expiry extended")
    except:
        await m.reply("usage: /extend user_id days")

@app.on_message(filters.command("disable") & filters.user(ADMIN_ID))
async def disable(_, m: Message):
    try:
        _, uid = m.text.split()
        await keys_col.update_one(
            {"user_id": int(uid)},
            {"$set": {"active": False}}
        )
        await m.reply("🚫 api key disabled")
    except:
        await m.reply("usage: /disable user_id")

# ─────────────────────────────
# RUN (HEROKU SAFE)
# ─────────────────────────────
if __name__ == "__main__":
    app.start()
    print("🤖 bot started successfully")
    idle()

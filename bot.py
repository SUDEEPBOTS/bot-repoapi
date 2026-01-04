import os
import time
import secrets
import datetime
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient

# ─────────────────────────────
# config
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
# database
# ─────────────────────────────
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["MusicAPI_DB1"]
keys_col = db["api_users"]

# ─────────────────────────────
# bot
# ─────────────────────────────
app = Client(
    "apikeybot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1,
    in_memory=True
)

# ─────────────────────────────
# helpers
# ─────────────────────────────
def generate_key():
    return "SUD-" + secrets.token_hex(8)

def now_ts():
    return int(time.time())

def days_to_ts(days):
    return now_ts() + days * 86400

# ─────────────────────────────
# start
# ─────────────────────────────
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "👋 **welcome to sudeep music api bot**\n\n"
        "📌 use `/getapi` to generate your api key\n"
        "🆓 free access for 2 days\n\n"
        f"🆘 support: {ADMIN_CONTACT}"
    )

# ─────────────────────────────
# get api
# ─────────────────────────────
@app.on_message(filters.command("getapi"))
async def get_api(_, m: Message):
    uid = m.from_user.id
    doc = await keys_col.find_one({"user_id": uid})

    if doc:
        exp = datetime.datetime.fromtimestamp(doc["expires_at"])
        await m.reply(
            "🔑 **your api key**\n\n"
            f"`{doc['api_key']}`\n\n"
            f"📆 expires: `{exp}`\n"
            f"📊 daily limit: `{doc['daily_limit']}`"
        )
        return

    api_key = generate_key()

    await keys_col.insert_one({
        "user_id": uid,
        "api_key": api_key,
        "expires_at": days_to_ts(FREE_DAYS),
        "daily_limit": DEFAULT_LIMIT,
        "used_today": 0,
        "last_reset": str(datetime.date.today()),
        "active": True
    })

    await m.reply(
        "✅ **api key generated successfully**\n\n"
        f"🔑 key:\n`{api_key}`\n\n"
        f"⏳ valid for **{FREE_DAYS} days**\n"
        f"📊 daily limit: `{DEFAULT_LIMIT}`\n\n"
        "⚠️ do not share your key"
    )

# ─────────────────────────────
# admin panel
# ─────────────────────────────
@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_panel(_, m: Message):
    await m.reply(
        "🛠 **admin panel**\n\n"
        "/setlimit <user_id> <limit>\n"
        "/extend <user_id> <days>\n"
        "/disable <user_id>"
    )

# ─────────────────────────────
# set limit
# ─────────────────────────────
@app.on_message(filters.command("setlimit") & filters.user(ADMIN_ID))
async def set_limit(_, m: Message):
    try:
        _, uid, limit = m.text.split()
        await keys_col.update_one(
            {"user_id": int(uid)},
            {"$set": {"daily_limit": int(limit)}}
        )
        await m.reply(f"✅ limit updated for `{uid}` → `{limit}`")
    except:
        await m.reply("❌ usage: `/setlimit user_id limit`")

# ─────────────────────────────
# extend
# ─────────────────────────────
@app.on_message(filters.command("extend") & filters.user(ADMIN_ID))
async def extend_key(_, m: Message):
    try:
        _, uid, days = m.text.split()
        uid, days = int(uid), int(days)

        doc = await keys_col.find_one({"user_id": uid})
        if not doc:
            await m.reply("❌ user not found")
            return

        await keys_col.update_one(
            {"user_id": uid},
            {"$set": {"expires_at": doc["expires_at"] + days * 86400}}
        )

        await m.reply(f"✅ api extended by `{days}` days for `{uid}`")
    except:
        await m.reply("❌ usage: `/extend user_id days`")

# ─────────────────────────────
# disable
# ─────────────────────────────
@app.on_message(filters.command("disable") & filters.user(ADMIN_ID))
async def disable_key(_, m: Message):
    try:
        _, uid = m.text.split()
        await keys_col.update_one(
            {"user_id": int(uid)},
            {"$set": {"active": False}}
        )
        await m.reply(f"🚫 api key disabled for `{uid}`")
    except:
        await m.reply("❌ usage: `/disable user_id`")

# ─────────────────────────────
# run (stable)
# ─────────────────────────────
async def main():
    await app.start()
    print("🤖 bot started successfully")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())

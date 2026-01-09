import os
import time
import secrets
import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URL = os.getenv("MONGO_DB_URI", "")

ADMIN_ID = 6356015122
ADMIN_CONTACT = "@zyroo100"

FREE_DAYS = 2
DEFAULT_LIMIT = 50

# ─────────────────────────────
# DATABASE
# ─────────────────────────────
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["MusicAPI_DB12"]
keys_col = db["api_users"]
videos_col = db["videos_cacht"]

# ─────────────────────────────
# BOT SETUP
# ─────────────────────────────
app = Client(
    "apikeybot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ─────────────────────────────
# 🎨 HELPERS
# ─────────────────────────────
def smc(text):
    """Small Caps Font Converter"""
    mapping = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ',
        'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
        'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 'u': 'ᴜ',
        'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ',
        'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
        'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 'U': 'ᴜ',
        'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
    }
    return "".join(mapping.get(c, c) for c in text)

def generate_key(prefix="YUKI"):
    return f"{prefix}-" + secrets.token_hex(6).upper()

async def is_admin(_, __, update):
    user_id = update.from_user.id if update.from_user else 0
    return user_id == ADMIN_ID

admin_filter = filters.create(is_admin)

# ─────────────────────────────
# 🟢 USER START
# ─────────────────────────────
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    txt = (
        f"**{smc('welcome to sudeep music api')}**\n\n"
        f"**> {smc('click the button below to generate your unique api key.')}**\n"
        f"**> {smc('free access for')} {FREE_DAYS} {smc('days.')}**\n\n"
        f"👤 **{smc('support:')}** {ADMIN_CONTACT}"
    )
    btn = InlineKeyboardMarkup([[InlineKeyboardButton(smc("✨ generate api key"), callback_data="user_gen_key")]])
    await m.reply(txt, reply_markup=btn, quote=True)

# ─────────────────────────────
# 👑 ADMIN PANEL
# ─────────────────────────────
@app.on_message(filters.command("admin") & admin_filter)
async def admin_start(_, m: Message):
    total_keys = await keys_col.count_documents({})
    active_keys = await keys_col.count_documents({"active": True})
    total_songs = await videos_col.count_documents({})

    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_usage"}}}]
    cursor = keys_col.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    total_requests = result[0]["total"] if result else 0

    text = (
        f"**{smc('admin control panel')}**\n\n"
        f"👥 **{smc('users:')}** `{total_keys}` (🟢 `{active_keys}`)\n"
        f"🎵 **{smc('songs:')}** `{total_songs}`\n"
        f"🔥 **{smc('total hits:')}** `{total_requests}`\n"
    )
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(smc("🆓 gen free key"), callback_data="gen_manual_free"),
         InlineKeyboardButton(smc("💎 gen vip key"), callback_data="gen_menu_vip")],
        [InlineKeyboardButton(smc("📜 manage users"), callback_data="adm_list_0")],
        [InlineKeyboardButton(smc("❌ close"), callback_data="adm_close")]
    ])
    await m.reply(text, reply_markup=buttons)

# ─────────────────────────────
# 🔄 CALLBACK HANDLER (MAIN LOGIC)
# ─────────────────────────────
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # ---------------------------
    # USER KEY GENERATION
    # ---------------------------
    if data == "user_gen_key":
        doc = await keys_col.find_one({"user_id": user_id})
        if doc:
            exp_ts = doc.get("expires_at", 0)
            limit = doc.get("daily_limit")
            api_key = doc["api_key"]
            used = doc.get("used_today", 0)
            exp_date = "Lifetime ♾️" if exp_ts > 3000000000 else datetime.datetime.fromtimestamp(exp_ts).strftime('%Y-%m-%d')
            status = "ᴀᴄᴛɪᴠᴇ ✅" if doc.get("active") else "ʙʟᴏᴄᴋᴇᴅ 🚫"

            txt = (f"**{smc('your api key details')}**\n\n> 🔑 **{smc('key:')}** `{api_key}`\n> 📊 **{smc('status:')}** {status}\n> 📅 **{smc('expires:')}** `{exp_date}`\n> 📉 **{smc('limit:')}** `{used}/{limit}`")
            await callback_query.edit_message_text(txt)
            return

        api_key = generate_key("YUKI")
        expires = int(time.time()) + (FREE_DAYS * 86400)
        doc = {"user_id": user_id, "api_key": api_key, "plan": "Free", "expires_at": expires, "daily_limit": DEFAULT_LIMIT, "used_today": 0, "total_usage": 0, "last_reset": str(datetime.date.today()), "active": True, "created_at": datetime.datetime.now()}
        await keys_col.insert_one(doc)
        txt = (f"**{smc('api key generated successfully')}**\n\n> 🔑 **{smc('key:')}** `{api_key}`\n> 📅 **{smc('validity:')}** {FREE_DAYS} {smc('days')}\n> 📉 **{smc('limit:')}** {DEFAULT_LIMIT}/{smc('day')}")
        await callback_query.edit_message_text(txt)

    # ---------------------------
    # ADMIN NAVIGATION
    # ---------------------------
    elif data == "adm_close":
        await callback_query.message.delete()

    elif data == "adm_home":
        if user_id != ADMIN_ID: return
        # ... (Stats calculation code same as above) ...
        # For brevity, redirection to admin_start logic via text editing
        await admin_start(client, callback_query.message) # Re-use function or copy logic
        # (Better to copy logic here to avoid message type conflict, but pasting full logic for safety)
        total_keys = await keys_col.count_documents({})
        active_keys = await keys_col.count_documents({"active": True})
        total_songs = await videos_col.count_documents({})
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_usage"}}}]
        cursor = keys_col.aggregate(pipeline)
        result = await cursor.to_list(length=1)
        total_requests = result[0]["total"] if result else 0

        text = (f"**{smc('admin control panel')}**\n\n👥 **{smc('users:')}** `{total_keys}` (🟢 `{active_keys}`)\n🎵 **{smc('songs:')}** `{total_songs}`\n🔥 **{smc('total hits:')}** `{total_requests}`\n")
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton(smc("🆓 gen free key"), callback_data="gen_manual_free"), InlineKeyboardButton(smc("💎 gen vip key"), callback_data="gen_menu_vip")],
            [InlineKeyboardButton(smc("📜 manage users"), callback_data="adm_list_0")],
            [InlineKeyboardButton(smc("❌ close"), callback_data="adm_close")]
        ])
        await callback_query.edit_message_text(text, reply_markup=buttons)

    # ---------------------------
    # KEY GENERATION MENUS
    # ---------------------------
    elif data == "gen_manual_free":
        if user_id != ADMIN_ID: return
        key = generate_key("YUKI")
        expires = int(time.time()) + (30 * 86400)
        doc = {"api_key": key, "plan": "Free (Manual)", "active": True, "daily_limit": 50, "used_today": 0, "total_usage": 0, "expires_at": expires, "created_at": datetime.datetime.now()}
        await keys_col.insert_one(doc)
        text = f"**{smc('free key generated')}**\n\n`{key}`\n30 Days"
        await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(smc("🔙 back"), callback_data="adm_home")]]))

    elif data == "gen_menu_vip":
        if user_id != ADMIN_ID: return
        text = f"**{smc('select vip duration')}**"
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("1 Month", callback_data="gen_vip_30"), InlineKeyboardButton("6 Months", callback_data="gen_vip_180")],
            [InlineKeyboardButton("1 Year", callback_data="gen_vip_365"), InlineKeyboardButton("Lifetime", callback_data="gen_vip_9999")],
            [InlineKeyboardButton(smc("🔙 back"), callback_data="adm_home")]
        ])
        await callback_query.edit_message_text(text, reply_markup=buttons)

    elif data.startswith("gen_vip_"):
        if user_id != ADMIN_ID: return
        days = int(data.split("_")[-1])
        key = generate_key("YUKI")
        expires_ts = 9999999999 if days > 5000 else int(time.time()) + (days * 86400)
        doc = {"api_key": key, "plan": "VIP 💎", "active": True, "daily_limit": 999999, "used_today": 0, "total_usage": 0, "expires_at": expires_ts, "created_at": datetime.datetime.now()}
        await keys_col.insert_one(doc)
        text = f"**{smc('vip key generated')}**\n\n`{key}`"
        await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(smc("🔙 back"), callback_data="adm_home")]]))

    # ---------------------------
    # MANAGE USERS LIST
    # ---------------------------
    elif data.startswith("adm_list_"):
        if user_id != ADMIN_ID: return
        page = int(data.split("_")[-1])
        limit = 6
        skip = page * limit
        cursor = keys_col.find({}).sort("created_at", -1).skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)
        
        if not users and page > 0: return await callback_query.answer("No more users.", show_alert=True)

        btn_list = []
        for user in users:
            status = "🟢" if user.get("active") else "🔴"
            plan = "💎" if "VIP" in user.get("plan", "") else "🆓"
            key_full = user['api_key']
            key_short = key_full[:10] + ".." 
            btn_list.append([InlineKeyboardButton(f"{status} {plan} {key_short}", callback_data=f"adm_view_{key_full}")])
        
        nav_btns = []
        if page > 0: nav_btns.append(InlineKeyboardButton("⬅️", callback_data=f"adm_list_{page-1}"))
        if await keys_col.count_documents({}) > skip + limit: nav_btns.append(InlineKeyboardButton("➡️", callback_data=f"adm_list_{page+1}"))
        btn_list.append(nav_btns)
        btn_list.append([InlineKeyboardButton(smc("🔙 back"), callback_data="adm_home")])
        await callback_query.edit_message_text(f"**{smc('user list')} - {page+1}**", reply_markup=InlineKeyboardMarkup(btn_list))

    # ---------------------------
    # VIEW USER & EDIT MENU (UPDATED) 🛠️
    # ---------------------------
    elif data.startswith("adm_view_"):
        if user_id != ADMIN_ID: return
        key = data.split("adm_view_")[1]
        doc = await keys_col.find_one({"api_key": key})
        if not doc: return await callback_query.answer("Not found")

        status = "Active ✅" if doc.get("active") else "Blocked 🚫"
        used_today = doc.get("used_today", 0)
        total_usage = doc.get("total_usage", 0)
        limit = doc.get("daily_limit")
        exp_ts = doc.get("expires_at", 0)
        
        # Calculate remaining days
        if exp_ts > 3000000000:
            validity = "Lifetime"
        else:
            remaining = (exp_ts - int(time.time())) // 86400
            validity = f"{remaining} Days"

        text = (
            f"**{smc('key statistics')}**\n\n"
            f"`{key}`\n\n"
            f"> 🏷️ **{smc('plan:')}** {doc.get('plan')}\n"
            f"> 📊 **{smc('status:')}** {status}\n"
            f"> ⏳ **{smc('validity:')}** `{validity}`\n"
            f"> 📉 **{smc('limit:')}** `{used_today}/{limit}`\n"
            f"> 🔥 **{smc('total:')}** `{total_usage}`"
        )

        # BUTTONS ROW 1: Block/Delete
        row1 = []
        if doc.get("active"): row1.append(InlineKeyboardButton(smc("block"), callback_data=f"adm_act_block_{key}"))
        else: row1.append(InlineKeyboardButton(smc("unblock"), callback_data=f"adm_act_unblock_{key}"))
        row1.append(InlineKeyboardButton(smc("delete"), callback_data=f"adm_act_del_{key}"))

        # BUTTONS ROW 2: Edit Limit / Validity
        row2 = [
            InlineKeyboardButton(smc("⚡ edit limit"), callback_data=f"menu_limit_{key}"),
            InlineKeyboardButton(smc("📅 edit validity"), callback_data=f"menu_valid_{key}")
        ]

        buttons = InlineKeyboardMarkup([row1, row2, [InlineKeyboardButton(smc("🔙 back"), callback_data="adm_list_0")]])
        await callback_query.edit_message_text(text, reply_markup=buttons)

    # ---------------------------
    # ⚡ EDIT LIMIT MENU
    # ---------------------------
    elif data.startswith("menu_limit_"):
        key = data.split("_", 2)[2]
        text = f"**{smc('adjust daily limit')}**\nKey: `{key}`\nSelect amount to add/remove:"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("+10", callback_data=f"set_limit_10_{key}"), InlineKeyboardButton("+50", callback_data=f"set_limit_50_{key}"), InlineKeyboardButton("+100", callback_data=f"set_limit_100_{key}")],
            [InlineKeyboardButton("-10", callback_data=f"set_limit_-10_{key}"), InlineKeyboardButton("-50", callback_data=f"set_limit_-50_{key}"), InlineKeyboardButton("-100", callback_data=f"set_limit_-100_{key}")],
            [InlineKeyboardButton(smc("🔙 back"), callback_data=f"adm_view_{key}")]
        ])
        await callback_query.edit_message_text(text, reply_markup=buttons)

    # ---------------------------
    # 📅 EDIT VALIDITY MENU
    # ---------------------------
    elif data.startswith("menu_valid_"):
        key = data.split("_", 2)[2]
        text = f"**{smc('adjust validity')}**\nKey: `{key}`\nSelect duration to add/remove:"
        
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("+1 Day", callback_data=f"set_valid_1_{key}"), InlineKeyboardButton("+1 Week", callback_data=f"set_valid_7_{key}"), InlineKeyboardButton("+1 Month", callback_data=f"set_valid_30_{key}")],
            [InlineKeyboardButton("-1 Day", callback_data=f"set_valid_-1_{key}"), InlineKeyboardButton("-1 Week", callback_data=f"set_valid_-7_{key}"), InlineKeyboardButton("-1 Month", callback_data=f"set_valid_-30_{key}")],
            [InlineKeyboardButton(smc("🔙 back"), callback_data=f"adm_view_{key}")]
        ])
        await callback_query.edit_message_text(text, reply_markup=buttons)

    # ---------------------------
    # ⚙️ HANDLE LIMIT CHANGE
    # ---------------------------
    elif data.startswith("set_limit_"):
        # Format: set_limit_{amount}_{key}
        parts = data.split("_")
        amount = int(parts[2])
        key = parts[3]
        
        await keys_col.update_one({"api_key": key}, {"$inc": {"daily_limit": amount}})
        await callback_query.answer(f"Limit updated by {amount} ✅")
        # Go back to View
        callback_query.data = f"adm_view_{key}"
        await callback_handler(client, callback_query)

    # ---------------------------
    # ⚙️ HANDLE VALIDITY CHANGE
    # ---------------------------
    elif data.startswith("set_valid_"):
        # Format: set_valid_{days}_{key}
        parts = data.split("_")
        days = int(parts[2])
        key = parts[3]
        
        doc = await keys_col.find_one({"api_key": key})
        if doc:
            current_exp = doc.get("expires_at", int(time.time()))
            # If lifetime, don't change or reset to now
            if current_exp > 3000000000: current_exp = int(time.time())
            
            new_exp = current_exp + (days * 86400)
            await keys_col.update_one({"api_key": key}, {"$set": {"expires_at": new_exp}})
            await callback_query.answer(f"Validity updated by {days} days ✅")
        
        callback_query.data = f"adm_view_{key}"
        await callback_handler(client, callback_query)

    # ---------------------------
    # 🔴 BLOCK / DELETE ACTIONS
    # ---------------------------
    elif data.startswith("adm_act_"):
        if user_id != ADMIN_ID: return
        action, key = data.split("_")[2], data.split("_")[3]
        if action == "block": await keys_col.update_one({"api_key": key}, {"$set": {"active": False}})
        elif action == "unblock": await keys_col.update_one({"api_key": key}, {"$set": {"active": True}})
        elif action == "del":
            await keys_col.delete_one({"api_key": key})
            return await callback_handler(client, CallbackQuery(id="0", from_user=callback_query.from_user, data="adm_list_0", message=callback_query.message))
        
        callback_query.data = f"adm_view_{key}"
        await callback_handler(client, callback_query)

if __name__ == "__main__":
    print("🤖 Admin Bot Advanced Started...")
    app.start()
    idle()
        

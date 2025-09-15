import json
import logging
import os

TOKEN = os.getenv("TOKEN")

from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)


OWNER_ID = 8148661928
ADMINS_FILE = Path("admins.json")
MOVIES_FILE = Path("movies.json")
CHANNELS_FILE = Path("channels.json")
REQUIRED_CHANNELS = ["@edit_11k"]


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_json(file: Path, default: dict):
    if not file.exists():
        file.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(file.read_text(encoding="utf-8"))

def save_json(file: Path, data: dict):
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_admins():
    return load_json(ADMINS_FILE, {"admins": []})

def save_admins(data):
    save_json(ADMINS_FILE, data)

def load_movies():
    return load_json(MOVIES_FILE, {})

def save_movies(data):
    save_json(MOVIES_FILE, data)

def load_channels():
    return load_json(CHANNELS_FILE, [])

def save_channels(data):
    save_json(CHANNELS_FILE, data)


def is_admin(user_id: int) -> bool:
    admins = load_admins()
    return user_id == OWNER_ID or user_id in admins["admins"]


REQUIRED_CHANNELS = ["@movieuzfilm"]

def sub_buttons():

    channels = REQUIRED_CHANNELS + load_channels()
    buttons = [
        [InlineKeyboardButton("KANALGA QO‘SHILISH +", url=f"https://t.me/{ch.lstrip('@')}")]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


async def is_subscribed(bot, user_id: int):
    not_sub = []
    channels = REQUIRED_CHANNELS + load_channels()  
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_sub.append(ch)
        except:
            not_sub.append(ch)
    return (len(not_sub) == 0, not_sub)




async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = "📌 *Bot yordamchi komandalar* 📌\n\n"

    if is_admin(user_id):
        text += (
            "🎬 *Admin komandalar:*\n"
            "/addmovie - Kino qo‘shish\n"
            "/delmovie KOD - Kino o‘chirish\n"
            "/addadmin USER_ID - Yangi admin qo‘shish\n"
            "/deladmin USER_ID - Adminni olib tashlash\n"
            "/addchanel @kanal_username - Kanal qo‘shish\n"
            "/delchanel @kanal_username - Kanal o‘chirish\n"
            "/stats - Statistika ko‘rish\n"
            "/broadcast - Foydalanuvchilarga xabar yuborish\n\n"
        )

    text += (
        "👤 *Foydalanuvchi komandalar:*\n"
        "/start - Botni ishga tushirish\n"
        "Kino kodi yuborish - Kino ma’lumotini olish\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, not_sub = await is_subscribed(context.bot, update.effective_user.id)
    if not ok:
        await update.message.reply_text("❌ Avval kanalga obuna bo‘ling!", reply_markup=sub_buttons())
        return
    user_id = update.effective_user.id
    context.bot_data.setdefault("users", {})
    context.bot_data["users"][user_id] = str(datetime.now().date())
    await update.message.reply_text("✅ Xush kelibsiz! Kino kodini yuboring.")

async def check_subscription_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ok, not_sub = await is_subscribed(context.bot, query.from_user.id)
    if ok:
        await query.edit_message_text("✅ Obuna bo‘ldingiz, endi kod yuborishingiz mumkin 🎬")
    else:
        await query.edit_message_text("❌ Obuna bo‘lmadingiz!", reply_markup=sub_buttons())

WAIT_VIDEO, WAIT_CODE, WAIT_TITLE, WAIT_YEAR, WAIT_GENRE = range(5)

async def add_movie_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Sizda kino qo‘shish huquqi yo‘q.")
    await update.message.reply_text("🎬 Kino videosini yuboring:")
    return WAIT_VIDEO

async def add_movie_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        return await update.message.reply_text("❌ Faqat video yuboring!")
    context.user_data["file_id"] = update.message.video.file_id
    await update.message.reply_text("📌 Kino kodi (raqam)ni yuboring:")
    return WAIT_CODE

async def add_movie_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["code"] = update.message.text.strip()
    await update.message.reply_text("📌 Kino nomini yuboring:")
    return WAIT_TITLE

async def add_movie_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text("📌 Kino yilini yuboring:")
    return WAIT_YEAR

async def add_movie_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["year"] = update.message.text.strip()
    await update.message.reply_text("📌 Kino janrini yuboring:")
    return WAIT_GENRE

async def add_movie_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_movies()
    code = context.user_data["code"]
    data[code] = {
        "title": context.user_data["title"],
        "year": context.user_data["year"],
        "genre": update.message.text.strip(),
        "file_id": context.user_data["file_id"]
    }
    save_movies(data)
    await update.message.reply_text(
        f"✅ Kino saqlandi!\n\n"
        f"Kino kodi: {code}\n"
        f"Yili: {context.user_data['year']}\n"
        f"Nomi: {context.user_data['title']}\n"
        f"Janri: {update.message.text.strip()}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    data = load_movies()
    if code not in data:
        return await update.message.reply_text("❌ Bunday kodli kino topilmadi.")
    m = data[code]
    text = (
        f"🎬 Kino kodi: {code}\n"
        f"📅 Yili: {m.get('year')}\n"
        f"🏷 Nomi: {m.get('title')}\n"
        f"🎞 Janri: {m.get('genre')}"
    )
    await update.message.reply_video(m["file_id"], caption=text)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Siz admin qo‘shish huquqiga ega emassiz.")
    if not context.args:
        return await update.message.reply_text("❗ Foydalanish: /addadmin <user_id>")
    try:
        new_admin = int(context.args[0])
    except:
        return await update.message.reply_text("❌ ID faqat raqam bo‘lishi kerak.")
    admins = load_admins()
    if new_admin in admins["admins"]:
        return await update.message.reply_text("⚠️ Bu foydalanuvchi allaqachon admin.")
    admins["admins"].append(new_admin)
    save_admins(admins)
    await update.message.reply_text(f"✅ Admin qo‘shildi: {new_admin}")

async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("❌ Siz egasi emassiz.")
    if not context.args:
        return await update.message.reply_text("❌ Foydalanish: /deladmin <user_id>")
    try:
        remove_id = int(context.args[0])
    except:
        return await update.message.reply_text("❌ ID noto‘g‘ri.")
    admins = load_admins()
    if remove_id not in admins["admins"]:
        return await update.message.reply_text("❌ Bu user admin emas.")
    admins["admins"].remove(remove_id)
    save_admins(admins)
    await update.message.reply_text(f"🗑 Admin o‘chirildi: {remove_id}")


async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data.setdefault("users", {})
    context.bot_data["users"][update.effective_user.id] = str(datetime.now().date())

async def delmovie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Sizda kino o‘chirish huquqi yo‘q.")
    if not context.args:
        return await update.message.reply_text("❌ Foydalanish: /delmovie <kod>")
    code = context.args[0]
    data = load_movies()
    if code in data:
        data.pop(code)
        save_movies(data)
        await update.message.reply_text(f"🗑 O‘chirildi: {code}")
    else:
        await update.message.reply_text("❌ Topilmadi.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Siz admin emassiz.")
    movies = load_movies()
    admins = load_admins()
    users = context.bot_data.get("users", {})
    total_users = len(users)
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    today_users = sum(1 for d in users.values() if d == str(today))
    week_users = sum(1 for d in users.values() if week_ago <= datetime.fromisoformat(d).date() <= today)
    total_movies = len(movies)
    last_movie = None
    if total_movies > 0:
        code, m = list(movies.items())[-1]
        last_movie = f"{m['title']} ({m['year']}) | Kod: {code} | Janr: {m['genre']}"
    admin_list = "\n".join([f"• {a}" for a in admins["admins"]]) if admins["admins"] else "—"
    genres = {}
    for m in movies.values():
        g = m.get("genre", "Noma’lum").capitalize()
        genres[g] = genres.get(g, 0) + 1
    top_genre = max(genres, key=genres.get) if genres else "—"
    text = (
        f"📊 Statistika\n\n"
        f"👥 Umumiy foydalanuvchilar: {total_users}\n"
        f"🟢 Bugun qo‘shilganlar: {today_users}\n"
        f"📅 Oxirgi 7 kunda qo‘shilganlar: {week_users}\n\n"
        f"🎬 Kinolar soni: {total_movies}\n"
    )
    if last_movie:
        text += f"🆕 So‘nggi qo‘shilgan kino: {last_movie}\n"
    text += f"⭐️ Eng ko‘p janr: {top_genre}\n\n"
    text += f"🛠 Adminlar ({len(admins['admins'])} ta):\n{admin_list}\n\n"
    text += f"👑 OWNER: {OWNER_ID}"
    await update.message.reply_text(text, parse_mode="Markdown")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Siz admin emassiz.")
    users = context.bot_data.get("users", {})
    if not users:
        return await update.message.reply_text("❌ Foydalanuvchi yo‘q.")
    users = list(users.keys())
    success = failed = 0
    content = " ".join(context.args) if context.args else ""
    if update.message.text and content:
        for uid in users:
            try: await context.bot.send_message(uid, content); success += 1
            except: failed += 1
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption or ""
        for uid in users:
            try: await context.bot.send_photo(uid, file_id, caption=caption); success += 1
            except: failed += 1
    elif update.message.video:
        file_id = update.message.video.file_id
        caption = update.message.caption or ""
        for uid in users:
            try: await context.bot.send_video(uid, file_id, caption=caption); success += 1
            except: failed += 1
    elif update.message.document:
        file_id = update.message.document.file_id
        caption = update.message.caption or ""
        for uid in users:
            try: await context.bot.send_document(uid, file_id, caption=caption); success += 1
            except: failed += 1
    elif update.message.audio:
        file_id = update.message.audio.file_id
        caption = update.message.caption or ""
        for uid in users:
            try: await context.bot.send_audio(uid, file_id, caption=caption); success += 1
            except: failed += 1
    else:
        return await update.message.reply_text("❌ Faqat matn, foto, video, hujjat yoki audio yuborishingiz mumkin.")
    await update.message.reply_text(f"✅ Yuborildi: {success}\n❌ Yuborilmadi: {failed}")


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Siz admin emassiz!")
    if not context.args:
        return await update.message.reply_text("ℹ️ Foydalanish: /addchanel @kanal_username")
    channel = context.args[0]
    channels = load_channels()
    if channel in channels:
        return await update.message.reply_text("⚠️ Bu kanal allaqachon ro‘yxatda bor.")
    channels.append(channel)
    save_channels(channels)
    await update.message.reply_text(f"✅ {channel} kanal qo‘shildi!")

async def del_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Siz admin emassiz!")
    if not context.args:
        return await update.message.reply_text("ℹ️ Foydalanish: /delchanel @kanal_username")
    channel = context.args[0]
    channels = load_channels()
    if channel not in channels:
        return await update.message.reply_text("⚠️ Bu kanal ro‘yxatda yo‘q.")
    channels.remove(channel)
    save_channels(channels)
    await update.message.reply_text(f"🗑 {channel} kanal o‘chirildi!")

def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("addmovie", add_movie_start)],
        states={
            WAIT_VIDEO: [MessageHandler(filters.VIDEO, add_movie_video)],
            WAIT_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_code)],
            WAIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_title)],
            WAIT_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_year)],
            WAIT_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_movie_genre)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_subscription_cb, pattern="check_sub"))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("deladmin", del_admin))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("delmovie", delmovie))
    app.add_handler(CommandHandler("addchanel", add_channel))
    app.add_handler(CommandHandler("delchanel", del_channel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.ALL, track_users), group=1)


    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

import json
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
)

TOKEN = "8281932561:AAHpRfJKJHTCnlG0Ap5oFABMU9BFUCmllW0"  
ADMIN_ID = 8148661928
ADMIN_ID = 693252412
REQUIRED_CHANNELS = ["@edit_11k"] 
DB_PATH = Path("kino_baza.json")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_db():
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text(encoding="utf-8"))
    return {}

def save_db(db: dict):
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

kino_baza = load_db()

async def is_subscribed(bot, user_id: int) -> bool:
    """Foydalanuvchi REQUIRED_CHANNELS ga obuna bo‘lsa True"""
    for ch in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True

def valid_code(code: str) -> bool:
    return code.isdigit() and 1 <= int(code) <= 1000

def sub_buttons():
    """Obuna bo‘lish tugmalari"""
    buttons = []
    for ch in REQUIRED_CHANNELS:
        buttons.append([InlineKeyboardButton(f"Obuna bo‘lish: {ch}", url=f"https://t.me/{ch.lstrip('@')}")])
    buttons.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Kino botga xush kelibsiz.\n\n"
        "📌 Kanal(lar)ga obuna bo‘ling va tekshirish tugmasini bosing, so‘ng kod yozing:",
        reply_markup=sub_buttons()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔧 Foydalanish:\n\n"
        "Admin:\n"
        "• Video yubor va caption = kod yoz (masalan: 34)\n"
        "• /add <kod> <file_id>\n"
        "• /del <kod>\n"
        "• /list\n\n"
        "Foydalanuvchi:\n"
        "• Kanal(lar)ga obuna bo‘ling va Tekshirish tugmasini bosing\n"
        "• Kod yoz → video chiqadi"
    )
    await update.message.reply_text(text, reply_markup=sub_buttons())

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Bu buyruq faqat admin uchun.")
    if len(context.args) < 2:
        return await update.message.reply_text("❌ Foydalanish: /add <kod> <file_id>")
    kod, file_id = context.args[0], context.args[1]
    if not valid_code(kod):
        return await update.message.reply_text("❌ Kod noto‘g‘ri. Masalan: 34.")
    kino_baza[kod] = file_id
    save_db(kino_baza)
    await update.message.reply_text(f"✅ Qo‘shildi: kod={kod}")

async def del_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Bu buyruq faqat admin uchun.")
    if not context.args:
        return await update.message.reply_text("❌ Foydalanish: /del <kod>")
    kod = context.args[0]
    if kod in kino_baza:
        del kino_baza[kod]
        save_db(kino_baza)
        await update.message.reply_text(f"🗑️ O‘chirildi: kod={kod}")
    else:
        await update.message.reply_text("❌ Bunday kod topilmadi.")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Bu buyruq faqat admin uchun.")
    if not kino_baza:
        return await update.message.reply_text("📂 Baza bo‘sh.")
    lines = [f"{k} → {v[:30]}..." for k, v in kino_baza.items()]
    await update.message.reply_text("📚 Kino bazasi:\n" + "\n".join(lines))

async def handle_admin_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    if not msg.video:
        return
    caption = (msg.caption or "").strip()
    if not valid_code(caption):
        return await msg.reply_text("❌ Caption = kod (masalan: 34) bo‘lishi kerak.")
    kod = caption
    kino_baza[kod] = msg.video.file_id
    save_db(kino_baza)
    await msg.reply_text(f"✅ Video saqlandi. Kod: {kod}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_sub":
        subscribed = await is_subscribed(context.bot, query.from_user.id)
        if subscribed:
            await query.edit_message_text(
                "✅ Siz kanallarga obuna bo‘lgansiz! Endi kod yozing va video chiqadi.",
                reply_markup=None
            )
        else:
            await query.edit_message_text(
                "❌ Siz hali barcha kanallarga obuna bo‘lmadingiz.",
                reply_markup=sub_buttons()
            )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kod = update.message.text.strip()
    if not valid_code(kod):
        return await update.message.reply_text("❌ Noto‘g‘ri kod.", reply_markup=sub_buttons())
    subscribed = await is_subscribed(context.bot, update.effective_user.id)
    if not subscribed:
        return await update.message.reply_text(
            "❗ Kanal(lar)ga obuna bo‘lishingiz kerak:",
            reply_markup=sub_buttons()
        )
    if kod in kino_baza:
        await update.message.reply_video(video=kino_baza[kod], caption=f"🎬 Kod: {kod}")
    else:
        await update.message.reply_text("❌ Bunday kod topilmadi.", reply_markup=sub_buttons())

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("del", del_command))
    app.add_handler(CommandHandler("list", list_command))

    app.add_handler(MessageHandler(filters.VIDEO, handle_admin_video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
from waitress import serve
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. إعداد السرفر للبقاء حياً (Render) ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "⚡ 『 ＦＡＳＴ ＭＥＤＩＡ 』 Is Online!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    serve(app_web, host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. الإعدادات العامة ---
TOKEN = "8254937829:AAGgMOc0z68Rqm5MAoURNmZNslH60o2LDJw" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
BOT_NAME = "『 ＦＡＳＴ ＭＥＤＩＡ 』"
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net", "@Fast_Mediia"]
USERS_FILE = "users.txt"
COOKIES_FILE = "cookies.txt" # تم تعديل الاسم هنا ليطابق ملفك

# --- 3. وظائف المساعدة والاشتراك ---
def add_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f: pass
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

async def is_subscribed(context, user_id):
    if user_id == ADMIN_ID: return True
    for chan in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=chan, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء لمنع انهيار البوت عند حدوث NetworkError"""
    print(f"⚠️ خطأ في النظام: {context.error}")

# --- 4. أوامر الواجهة ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    context.user_data.clear()
    
    kb = [['🔄 بدء من جديد'], ['👨‍💻 المطور', '📢 القنوات']]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome_text = (
        f"👋 أهلاً بك يا {user.first_name}\n\n"
        f"⚡ <b>{BOT_NAME}</b>\n"
        "أرسل رابط فيديو (YouTube, Instagram, TikTok) وسأقوم بمعالجته.\n\n"
        "⚠️ تأكد أن المحساب عام وليس خاص."
    )
    
    if update.callback_query:
        await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 إحصائيات المشتركين: <code>{count}</code>", parse_mode=ParseMode.HTML)

# --- 5. معالج الرسائل ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔄 بدء من جديد': await start(update, context); return
    elif text == '👨‍💻 المطور': await update.message.reply_text(f"👑 المطور: {DEV_USER}"); return
    elif text == '📢 القنوات':
        links = "\n".join([f"🔗 {c}" for c in CHANNELS])
        await update.message.reply_text(f"📢 قنواتنا:\n{links}"); return

    if "http" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("<b>⚠️ عذراً! يجب الاشتراك في القنوات أولاً.</b>", parse_mode=ParseMode.HTML); return
        
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 فيديو (MP4)", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 صوت (MP3)", callback_data="dl_audio")]]
        await update.message.reply_text(f"📥 اختر الصيغة المطلوبة:", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)

# --- 6. عملية التحميل والرفع (القلب النابض للبوت) ---
async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    url = context.user_data.get('url')
    if not url: return

    action = query.data
    status = await context.bot.send_message(user_id, "⌛ <b>جاري التحميل والمعالجة...</b>", parse_mode=ParseMode.HTML)

    # إنشاء اسم فريد للملف
    file_prefix = f"file_{user_id}_{os.urandom(2).hex()}"
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        'outtmpl': f'{file_prefix}.%(ext)s',
        'noplaylist': True,
        # تحديد الحجم الأقصى ليتوافق مع تليجرام (أقل من 50 ميجا)
        'format': 'best[ext=mp4][filesize<48M]/best[filesize<48M]/best' if action == "dl_video" else 'bestaudio/best',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        # مرحلة التحميل من الشبكة
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        await status.edit_text("📤 <b>جاري الرفع إلى تليجرام...</b>", parse_mode=ParseMode.HTML)
        
        # مرحلة الرفع إلى تليجرام مع زيادة مهلة الانتظار لرفع الملفات الكبيرة
        with open(downloaded_file, 'rb') as f:
            if action == "dl_audio":
                await context.bot.send_audio(chat_id=user_id, audio=f, caption=f"✨ بواسطة {DEV_USER}", read_timeout=180, write_timeout=180)
            else:
                await context.bot.send_video(chat_id=user_id, video=f, caption=f"✨ بواسطة {DEV_USER}", read_timeout=180, write_timeout=180)
        
        await status.delete()

    except Exception as e:
        print(f"Detailed Error: {e}")
        await status.edit_text("❌ حدث خطأ! قد يكون الرابط محمياً، خاصاً، أو أن الفيديو يتجاوز حجمه 50MB.")
    
    finally:
        # تنظيف السيرفر من الملفات فور الانتهاء
        context.user_data.clear()
        if 'downloaded_file' in locals() and os.path.exists(downloaded_file):
            try: os.remove(downloaded_file)
            except: pass

# --- 7. تشغيل البوت ---
if __name__ == "__main__":
    keep_alive() # تشغيل سيرفر الويب في الخلفية
    app = ApplicationBuilder().token(TOKEN).build()
    
    # الروابط
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(process_download))
    
    # معالج الأخطاء لحل مشكلة NetworkError نهائياً
    app.add_error_handler(error_handler)
    
    print(f"✅ {BOT_NAME} يعمل الآن.")
    app.run_polling(drop_pending_updates=True)

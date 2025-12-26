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

# --- 1. إعداد السرفر (Render) لإبقاء البوت حياً ---
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

# --- 2. الإعدادات ---
TOKEN = "8254937829:AAGgMOc0z68Rqm5MAoURNmZNslH60o2LDJw" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
BOT_NAME = "『 ＦＡＳＴ ＭＥＤＩＡ 』"
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net", "@Fast_Mediia"]
USERS_FILE = "users.txt"

# --- 3. إدارة البيانات والاشتراك ---
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

# --- 4. معالج الأخطاء العالمي (حل مشكلة NetworkError) ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إدارة أخطاء الشبكة والطلبات لضمان عدم توقف البوت"""
    print(f"⚠️ تنبيه خطأ: {context.error}")

# --- 5. واجهة البداية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    context.user_data.clear()
    
    kb = [['🔄 بدء من جديد'], ['👨‍💻 المطور', '📢 القنوات']]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome_text = (
        f"👋 أهلاً بك يا {user.first_name}\n\n"
        f"⚡ <b>{BOT_NAME}</b>\n"
        "قم بإرسال رابط (تيك توك، إنستا، يوتيوب) وسأقوم بمعالجته فوراً.\n\n"
        "⚠️ تأكد من أن الحساب عام وليس خاص."
    )
    
    if update.callback_query:
        await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)

# --- 6. الإحصائيات (للأدمن) ---
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 <b>إحصائيات المشتركين:</b>\n\nعدد المستخدمين: <code>{count}</code>", parse_mode=ParseMode.HTML)

# --- 7. معالج الرسائل ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔄 بدء من جديد': await start(update, context); return
    elif text == '👨‍💻 المطور': await update.message.reply_text(f"👑 <b>مطور البوت:</b> {DEV_USER}", parse_mode=ParseMode.HTML); return
    elif text == '📢 القنوات':
        links = "\n".join([f"🔗 {c}" for c in CHANNELS])
        await update.message.reply_text(f"📢 <b>قنواتنا الرسمية:</b>\n{links}", parse_mode=ParseMode.HTML); return

    if "http" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("<b>⚠️ عذراً! يجب الاشتراك في القنوات أولاً لتتمكن من التحميل.</b>", parse_mode=ParseMode.HTML); return
        
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 فيديو (MP4)", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 صوت (Audio)", callback_data="dl_audio")]]
        await update.message.reply_text(f"📥 <b>اختر الصيغة المطلوبة:</b>", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)

# --- 8. التحميل والرفع (مع زيادة التوقيت Timeout) ---
async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "restart_bot": 
        await query.answer(); await start(update, context); return
    
    await query.answer()
    user_id = query.from_user.id
    url = context.user_data.get('url')
    if not url: return

    action = query.data
    status = await context.bot.send_message(user_id, "⌛ <b>جاري جلب بيانات الرابط...</b>", parse_mode=ParseMode.HTML)

    file_path = f"file_{user_id}"
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'outtmpl': f'{file_path}.%(ext)s',
        'format': 'best' if action == "dl_video" else 'bestaudio/best',
        'user_agent': 'Mozilla/5.0'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        await status.edit_text("📤 <b>جاري رفع الملف إلى تليجرام...</b>", parse_mode=ParseMode.HTML)
        
        with open(downloaded_file, 'rb') as f:
            # تم إضافة timeouts لضمان عدم حدوث NetworkError أثناء الرفع
            if action == "dl_audio":
                await context.bot.send_audio(chat_id=user_id, audio=f, caption=f"✨ بواسطة {DEV_USER}", connect_timeout=60, read_timeout=60)
            else:
                await context.bot.send_video(chat_id=user_id, video=f, caption=f"✨ بواسطة {DEV_USER}", connect_timeout=60, read_timeout=60)
        
        await status.delete()

    except Exception as e:
        print(f"Error logic: {e}")
        await status.edit_text("❌ حدث خطأ! قد يكون الرابط غير مدعوم أو الملف كبير جداً.", parse_mode=ParseMode.HTML)
    
    finally:
        context.user_data.clear()
        # تنظيف الملفات من السيرفر لتوفير المساحة
        if 'downloaded_file' in locals() and os.path.exists(downloaded_file):
            os.remove(downloaded_file)

# --- 9. التشغيل النهائي ---
if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    
    # إضافة المستقبلات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(process_download))
    
    # الحل السحري لمشكلة NetworkError
    app.add_error_handler(error_handler)

    print(f"✅ {BOT_NAME} يعمل الآن بثبات.")
    app.run_polling(drop_pending_updates=True)

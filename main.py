import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
from waitress import serve  # تم إضافة هذا السطر لحل التحذير
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. إعداد السرفر الاحترافي (Production Server) لـ Render ---
app_web = Flask('')

@app_web.route('/')
def home():
    return "⚡ 『 ＦＡＳＴ ＭＥＤＩＡ 』 Is Online!"

def run_flask():
    # جلب المنفذ من ريندر أو استخدام 8080 افتراضياً
    port = int(os.environ.get('PORT', 8080))
    # استخدام serve بدلاً من app.run لحل مشكلة التحذير
    serve(app_web, host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. الإعدادات والمعلومات ---
TOKEN = "8254937829:AAGgMOc0z68Rqm5MAoURNmZNslH60o2LDJw" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
BOT_NAME = "『 ＦＡＳＴ ＭＥＤＩＡ 』"
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net", "@Fast_Mediia"]
USERS_FILE = "users.txt"

# --- 3. إدارة قاعدة البيانات ---
def add_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f: pass
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

# --- 4. فحص الاشتراك الإجباري ---
async def is_subscribed(context, user_id):
    if user_id == ADMIN_ID: return True
    for chan in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=chan, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

# --- 5. واجهة البداية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    context.user_data.clear()
    
    kb = [['🔄 بدء من جديد', '📊 إحصائيات'], ['👨‍💻 المطور', '📢 القنوات']]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome_text = (
        f"👋 أهلاً بك يا {user.first_name}\n\n"
        f"⚡ <b>{BOT_NAME}</b>\n"
        "قم بإرسال رابط (تيك توك، إنستا، يوتيوب) وسأقوم بمعالجته فوراً."
    )
    
    if update.callback_query:
        await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)

# --- 6. وظيفة التقدم ---
def progress_hook(d, context, chat_id, message_id, loop):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        s = d.get('_speed_str', '0KB/s')
        text = (f"⏳ <b>جاري التحميل...</b> ⏳\n\n"
                f"<b>📊 التقدم:</b> <code>{p}</code>\n"
                f"<b>🚀 السرعة:</b> <code>{s}</code>")
        asyncio.run_coroutine_threadsafe(
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=ParseMode.HTML),
            loop
        )

# --- 7. معالج الرسائل ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔄 بدء من جديد': await start(update, context); return
    elif text == '📊 إحصائيات':
        count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 <b>مستخدمي البوت:</b> <code>{count}</code>", parse_mode=ParseMode.HTML); return
    elif text == '👨‍💻 المطور': await update.message.reply_text(f"👑 <b>المطور:</b> {DEV_USER}", parse_mode=ParseMode.HTML); return
    elif text == '📢 القنوات':
        links = "\n".join([f"🔗 {c}" for c in CHANNELS])
        await update.message.reply_text(f"📢 <b>قنواتنا:</b>\n{links}", parse_mode=ParseMode.HTML); return

    if "http" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("<b>⚠️ يجب الاشتراك في القنوات أولاً!</b>", parse_mode=ParseMode.HTML); return
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 فيديو", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 صوت", callback_data="dl_audio")]]
        await update.message.reply_text(f"📥 <b>اختر الصيغة المطلوبة:</b>", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)

# --- 8. التحميل والرفع ---
async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "restart_bot": await query.answer(); await start(update, context); return
    await query.answer()
    user_id = query.from_user.id
    url = context.user_data.get('url')
    if not url: return
    
    action = query.data
    loop = asyncio.get_event_loop()
    status = await context.bot.send_message(user_id, "⌛ <b>جاري معالجة الرابط...</b>", parse_mode=ParseMode.HTML)

    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'outtmpl': f'file_{user_id}.%(ext)s',
        'format': 'best' if action == "dl_video" else 'bestaudio/best',
        'progress_hooks': [lambda d: progress_hook(d, context, user_id, status.message_id, loop)],
        'user_agent': 'Mozilla/5.0'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            file_path = ydl.prepare_filename(info)

        await status.edit_text("📤 <b>جاري إرسال الملف...</b>", parse_mode=ParseMode.HTML)
        with open(file_path, 'rb') as f:
            if action == "dl_audio":
                await context.bot.send_audio(chat_id=user_id, audio=f, caption=f"✨ بواسطة {DEV_USER}", parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_video(chat_id=user_id, video=f, caption=f"✨ بواسطة {DEV_USER}", parse_mode=ParseMode.HTML)
        
        await status.delete()
        context.user_data.clear()
        restart_btn = [[InlineKeyboardButton("🔄 تحميل جديد", callback_data="restart_bot")]]
        await context.bot.send_message(user_id, f"✅ <b>تم التحميل بنجاح!</b>", reply_markup=InlineKeyboardMarkup(restart_btn), parse_mode=ParseMode.HTML)
        if os.path.exists(file_path): os.remove(file_path)
    except Exception:
        await status.edit_text("❌ <b>حدث خطأ!</b> تأكد من الرابط.", parse_mode=ParseMode.HTML)

# --- 9. التشغيل ---
if __name__ == "__main__":
    keep_alive() # تشغيل خادم Waitress
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(process_download))
    print(f"✅ {BOT_NAME} Online on Render!")
    app.run_polling(drop_pending_updates=True)

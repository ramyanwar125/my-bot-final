import os
import yt_dlp
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
USERS_FILE = "users.txt"
COOKIES_FILE = "cookies.txt" # تأكد أن الملف مرفوع بهذا الاسم تماماً

# --- 2. إدارة البيانات ---
def add_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "w").close()
    with open(USERS_FILE, "a+") as f:
        f.seek(0)
        if str(user_id) not in f.read().splitlines():
            f.write(f"{user_id}\n")

def format_size(bytes_val):
    if not bytes_val: return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024: return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} GB"

# --- 3. الدوال الأساسية للتحميل والتحليل ---
def get_ydl_opts(extra_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    # دمج الكوكيز التي أرسلتها بشكل إجباري
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    
    if extra_opts:
        opts.update(extra_opts)
    return opts

# --- 4. معالجة الرسائل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if update.effective_user.id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    await update.message.reply_text("✨ أهلاً بك! أرسل رابط الفيديو الآن.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`\n\nشكراً لتواصلك! ❤️")
        return

    if "إحصائياتي" in text:
        count = len(open(USERS_FILE).read().splitlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 عدد المشتركين: {count}")
        return

    if "http" in text:
        m = await update.message.reply_text("🔎 جاري تحليل الرابط باستخدام الكوكيز...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, text, download=False)
                formats = info.get('formats', [])
                
                res_sizes = {"720": "N/A", "480": "N/A", "360": "N/A"}
                for f in formats:
                    h = str(f.get('height'))
                    if h in res_sizes and f.get('filesize'):
                        res_sizes[h] = format_size(f['filesize'])

                keyboard = [
                    [InlineKeyboardButton(f"720p - {res_sizes['720']}", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton(f"480p - {res_sizes['480']}", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton(f"360p - {res_sizes['360']}", callback_data=f"dl|360|{text}")],
                    [InlineKeyboardButton("MP3 (صوت فقط)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:50]}...\n\nاختر الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            await m.edit_text(f"❌ فشل التحليل.\nتأكد أن ملف `{COOKIES_FILE}` موجود في السيرفر.", 
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new")]]))

# --- 5. تنفيذ التحميل ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "new":
        await q.message.reply_text("✨ أرسل رابطاً جديداً:"); await q.message.delete(); return

    if q.data.startswith("dl|"):
        _, quality, url = q.data.split("|")
        msg = await q.message.reply_text(f"⏳ جاري تحميل {quality}...")
        path = f"file_{q.from_user.id}.mp4"
        
        ydl_opts = get_ydl_opts({'outtmpl': path})
        if quality == 'mp3':
            path = path.replace('.mp4', '.mp3')
            ydl_opts.update({'format': 'bestaudio/best', 'outtmpl': path})
        else:
            ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
            
            with open(path, "rb") as f:
                if quality == 'mp3': await q.message.reply_audio(audio=f)
                else: await q.message.reply_video(video=f)
            
            await q.message.reply_text("✅ تم التحميل!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new")]]))
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ فشل التحميل.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new")]]))

# --- تشغيل ---
if __name__ == "__main__":
    def srv():
        HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()
    threading.Thread(target=srv, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

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
TOKEN = "8579186374:AAFsgJms9BdnL7Jih7DL3jNiyofWh-vpGTg"
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
COOKIES_FILE = "cookies.txt"

# --- 2. إعدادات التحميل بالكوكيز ---
def get_ydl_opts(custom=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    if custom:
        opts.update(custom)
    return opts

# --- 3. الأوامر والقائمة السفلية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        ['🔄 بدء من جديد', '❌ إلغاء'],
        ['📊 إحصائياتي', '👨‍💻 المطور']
    ]
    if update.effective_user.id == ADMIN_ID:
        kb.append(['🛠 لوحة التحكم'])
        
    await update.message.reply_text(
        "🚀 تم تشغيل CYBORG بنجاح!\nالكوكيز مدمجة والأزرار جاهزة.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '🔄 بدء من جديد':
        await update.message.reply_text("🔄 تم مسح العملية، أرسل رابطاً جديداً.")
        return
    if text == '❌ إلغاء':
        await update.message.reply_text("🚫 تم الإلغاء بنجاح.")
        return
    if text == '📊 إحصائياتي':
        await update.message.reply_text("📊 البوت يعمل بكفاءة مع الكوكيز المدمجة.")
        return
    if text == '👨‍💻 المطور':
        await update.message.reply_text(f"👤 المطور: {DEV_USER}")
        return

    if "http" in text:
        m = await update.message.reply_text("🔎 جاري فحص الرابط...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, text, download=False)
                btns = [
                    [InlineKeyboardButton("Video (High)", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton("Video (Medium)", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton("Audio (MP3)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:50]}...\n\nاختر الجودة:", reply_markup=InlineKeyboardMarkup(btns))
        except Exception:
            await m.edit_text("❌ خطأ في التحليل. تأكد من ملف cookies.txt")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("dl|"):
        _, quality, url = q.data.split("|")
        msg = await q.message.reply_text(f"⏳ جاري تحميل {quality}...")
        path = f"file_{q.from_user.id}.mp4"
        
        opts = get_ydl_opts({'outtmpl': path})
        if quality == 'mp3':
            path = path.replace('.mp4', '.mp3')
            opts.update({'format': 'bestaudio/best', 'outtmpl': path})
        else:
            opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best/best'

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
            with open(path, "rb") as f:
                if quality == 'mp3': await q.message.reply_audio(f)
                else: await q.message.reply_video(f)
            os.remove(path)
            await msg.delete()
        except Exception:
            await msg.edit_text("❌ حدث خطأ أثناء التحميل.")

# --- 4. سيرفر الويب وسيرفر الصحة ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_srv():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # حل مشكلة الـ Conflict: drop_pending_updates=True
    # يقوم بمسح الطلبات المتراكمة ويقطع الاتصال القديم
    app.run_polling(drop_pending_updates=True)

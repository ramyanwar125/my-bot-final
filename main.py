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

# --- الإعدادات ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0"
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
USERS_FILE = "users.txt"
COOKIES_FILE = "cookies.txt"

def get_list(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, "r") as f:
        return list(set(f.read().splitlines()))

# --- دالة التحليل والتحميل الموحدة بالكوكيز ---
def get_ydl_opts(custom=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE # دمج كوكيز يوتيوب وانستا
    if custom:
        opts.update(custom)
    return opts

# --- معالجة الأوامر والقائمة السفلية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [['🔄 بدء من جديد', '❌ إلغاء'], ['📊 إحصائياتي', '👨‍💻 المطور']]
    if update.effective_user.id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(
        "🚀 CYBORG جاهز للعمل!\nتم دمج الكوكيز وتحديث الأزرار السفلية.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '🔄 بدء من جديد':
        await update.message.reply_text("🔄 تم البدء من جديد، أرسل الرابط.")
        return
    if text == '❌ إلغاء':
        await update.message.reply_text("🚫 تم إلغاء العملية.")
        return
    if "http" in text:
        m = await update.message.reply_text("🔎 جاري التحليل بالكوكيز...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, text, download=False)
                btns = [
                    [InlineKeyboardButton("720p", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton("480p", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton("MP3", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:50]}\n\nاختر الجودة:", reply_markup=InlineKeyboardMarkup(btns))
        except:
            await m.edit_text("❌ فشل التحليل. تأكد من ملف cookies.txt")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data.startswith("dl|"):
        _, quality, url = q.data.split("|")
        msg = await q.message.reply_text(f"⏳ جاري التحميل...")
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
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ فشل التحميل.")

# --- التشغيل السحابي ---
def srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # الحل البرمجي لتعليق الـ Conflict
    print("🤖 CYBORG HD Is Running...")
    app.run_polling(drop_pending_updates=True, close_loop=False)

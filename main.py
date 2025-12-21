import os
import json
import asyncio
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. إعداد السيرفر لإرضاء منصة Render ---
class HealthCheckServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckServer)
    server.serve_forever()

# --- 2. الإعدادات ---
TOKEN = "8579186374:AAG2d1kDTfgFDKrRIdGxtK3DIWlE252hWpM"
COOKIE_FILE = "cookies.txt"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# قائمة الكوكيز التي أرسلتها سابقاً
MY_COOKIES = [
    {"domain": ".youtube.com", "expirationDate": 1800856531, "name": "__Secure-1PAPISID", "path": "/", "value": "5i84Die2RJBNC2ce/AT2hauHxI6F92xPj_", "secure": True},
    {"domain": ".youtube.com", "expirationDate": 1800856531, "name": "Secure-1PSID", "path": "/", "value": "g.a0004giEiFc2xdrGVpg52KCe5iEggWIlfVJTzLdmIY_shjAgvHHZJClOksy_V1shnK_eMU2QACgYKAWISARYSFQHGX2MiSRiVPtw6IQMxGYvEmCdH4RoVAUF8yKozwvkHQM09piFqm1tD3qSe0076", "secure": True},
    # ... أضف بقية القائمة هنا ...
]

def save_cookies():
    with open(COOKIE_FILE, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in MY_COOKIES:
            domain = c.get('domain', '')
            flag = "TRUE" if domain.startswith('.') else "FALSE"
            path = c.get('path', '/')
            secure = "TRUE" if c.get('secure', False) else "FALSE"
            expires = int(c.get('expirationDate', 0))
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{c['name']}\t{c['value']}\n")

# --- 3. وظائف البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت يعمل الآن على Render 24/7! أرسل رابط الفيديو.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status = await update.message.reply_text("🔍 فحص الرابط باستخدام الكوكيز المحدثة...")
    
    ydl_opts = {'quiet': True, 'cookiefile': COOKIE_FILE, 'user_agent': USER_AGENT}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        qualities = {f.get("height"): f["format_id"] for f in info.get("formats", []) 
                     if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("height")}
        
        context.user_data.update({"url": url, "qualities": qualities})
        keyboard = [[InlineKeyboardButton(f"{h}p", callback_data=str(h))] for h in sorted(qualities.keys(), reverse=True)]
        await status.edit_text("🎚️ اختر الجودة للتحميل:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await status.edit_text(f"❌ فشل الفحص. قد تكون الكوكيز منتهية.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    height = int(query.data)
    file_path = f"video_{query.from_user.id}.mp4"
    
    await query.edit_message_text("⏳ جاري التحميل والرفع...")
    
    opts = {
        'format': context.user_data["qualities"][height],
        'outtmpl': file_path,
        'cookiefile': COOKIE_FILE,
        'user_agent': USER_AGENT
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([context.user_data["url"]])
        with open(file_path, "rb") as v:
            await query.message.reply_video(video=v, caption=f"✅ جودة {height}p")
    except Exception as e:
        await query.message.reply_text("❌ حدث خطأ أثناء التحميل.")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

# --- 4. تشغيل البوت ---
async def run_bot():
    save_cookies()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(download))
    
    # تشغيل السيرفر في خلفية البرنامج
    threading.Thread(target=run_health_server, daemon=True).start()
    
    print("🚀 البوت بدأ العمل...")
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    # إبقاء البوت نشطاً
    while True:
        await asyncio.sleep(3600)

if name == "main":
    asyncio.run(run_bot())

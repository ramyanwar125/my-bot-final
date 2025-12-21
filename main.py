import os
import asyncio
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات ---
TOKEN = "8579186374:AAEoosCslSUJY7XKxx8Jlzw-Fh5_o7WvjTs"
ADMIN_ID = 7349033289  # 👈 ضع الآيدي الخاص بك هنا
USERS_FILE = "users.txt"
YT_COOKIE_FILE = "youtube_cookies.txt"
IG_COOKIE_FILE = "instagram_cookies.txt"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# --- 2. إدارة المستخدمين ---
def add_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r+") as f:
        users = f.read().splitlines()
        if str(user_id) not in users: f.write(f"{user_id}\n")

# --- 3. وظيفة عرض الجودة بشكل جميل ---
def get_quality_label(h):
    if h >= 2160: return f"💎 {h}p (4K Ultra HD)"
    elif h >= 1080: return f"🎬 {h}p (Full HD)"
    elif h >= 720: return f"🎥 {h}p (HD)"
    return f"📱 {h}p"

# --- 4. منطق البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text("👋 أهلاً بك! أرسل رابط فيديو من يوتيوب، إنستجرام، أو فيسبوك للتحميل.")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" not in url: return
    
    msg = await update.message.reply_text("🔍 جاري الفحص...")
    c_file = YT_COOKIE_FILE if "youtu" in url else (IG_COOKIE_FILE if "instagr" in url else None)

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': c_file}) as ydl:
            info = ydl.extract_info(url, download=False)
        
        if "youtu" in url:
            context.user_data['url'] = url
            qs = {}
            for f in info.get("formats", []):
                h = f.get("height")
                if h and f.get("vcodec") != "none" and h not in qs: qs[h] = f["format_id"]
            
            btns = [[InlineKeyboardButton(get_quality_label(h), callback_data=f"yt_{h}")] for h in sorted(qs.keys(), reverse=True)[:5]]
            await msg.edit_text("✨ اختر الجودة المطلوبة:", reply_markup=InlineKeyboardMarkup(btns))
        else:
            await msg.edit_text("📥 جاري تحميل الفيديو...")
            path = f"vid_{update.effective_user.id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'cookiefile': c_file}) as ydl: ydl.download([url])
            await update.message.reply_video(video=open(path, "rb"), caption="✅ تم التحميل بنجاح")
            os.remove(path); await msg.delete()
    except: await msg.edit_text("❌ خطأ: الرابط غير مدعوم أو المحتوى خاص.")

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data.startswith("yt_"):
        h = q.data.split("_")[1]; path = f"yt_{q.from_user.id}.mp4"
        await q.edit_message_text(f"⏳ جاري تحميل جودة {h}p...")
        opts = {'format': f'bestvideo[height<={h}]+bestaudio/best', 'outtmpl': path, 'cookiefile': YT_COOKIE_FILE}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([context.user_data['url']])
            await q.message.reply_video(video=open(path, "rb"))
        finally: 
            if os.path.exists(path): os.remove(path)

# --- 5. تشغيل السيرفر (Render Health Check) ---
def run_srv():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

# --- السطر الذي تسبب في الخطأ (تم إصلاحه هنا) ---
if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("🚀 البوت بدأ العمل!")
    app.run_polling()

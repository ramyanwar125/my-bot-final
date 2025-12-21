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

# --- 1. الإعدادات الأساسية ---
TOKEN = "8579186374:AAG2d1kDTfgFDKrRIdGxtK3DIWlE252hWpM"
ADMIN_ID = 7349033289  # 👈 ضع الآيدي الخاص بك هنا (مهم جداً للوحة التحكم)
YT_COOKIE_FILE = "youtube_cookies.txt"
IG_COOKIE_FILE = "instagram_cookies.txt"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
USERS_FILE = "users.txt" # لتخزين المشتركين

# --- 2. إدارة المستخدمين (Database) ---
def add_user(user_id):
    users = get_users()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

def get_users():
    if not os.path.exists(USERS_FILE): return []
    with open(USERS_FILE, "r") as f:
        return [line.strip() for line in f.readlines()]

# --- 3. بيانات الكوكيز (التي أرسلتها أنت) ---
YT_COOKIES_DATA = [
    {"domain": ".youtube.com", "expirationDate": 1800856531, "name": "__Secure-1PAPISID", "path": "/", "value": "5i84Die2RJBNC2ce/AT2hauHxI6F92xPj_", "secure": True},
    {"domain": ".youtube.com", "expirationDate": 1800856531, "name": "Secure-1PSID", "path": "/", "value": "g.a0004giEiFc2xdrGVpg52KCe5iEggWIlfVJTzLdmIY_shjAgvHHZJClOksy_V1shnK_eMU2QACgYKAWISARYSFQHGX2MiSRiVPtw6IQMxGYvEmCdH4RoVAUF8yKozwvkHQM09piFqm1tD3qSe0076", "secure": True},
    {"domain": ".youtube.com", "expirationDate": 1800856532, "name": "LOGIN_INFO", "path": "/", "value": "AFmmF2swRQIhAJr_X_MAu1PKtQ7YbEoBme3ow5NsWSDax1gAtpwPVsLsAiA7viGmF4Tmg5dEWSZDbAGU_wD1X0KD0dyQCM_i8udTOg:QUQ3MjNmd1paTG9Rdm8tekRXSWxDb292WEQwZVBpbEVwYWNDUlNfVGppVUJxQ1JWYzNoMGRsbFY3cHU1MjRfX0Zwb1J3SmhwU2xrekF4Q3lQY19RTWFvZ01qeDFmVHVScS04WVFOV29nQk5TOTdpUWhTa1VPd3hQSDBENThBUjYwbUlYMUNuNlZQaGFMZVJEajJHU21OZklkV2tKS1FTTFJR", "secure": True}
]

IG_COOKIES_DATA = [
    {"domain": ".instagram.com", "expirationDate": 1800862866, "name": "csrftoken", "path": "/", "value": "DnO3jSuY3e0dtImAtjAL6ZfwHAa8HcDN", "secure": True},
    {"domain": ".instagram.com", "expirationDate": 1800862514, "name": "datr", "path": "/", "value": "MqNHaUVvnID_s39nxxjJ1R1T", "secure": True},
    {"domain": ".instagram.com", "expirationDate": 1797838817, "name": "sessionid", "path": "/", "value": "24107301450%3AA4b390q4BRGcOW%3A22%3AAYiDmIJ0Cgv3FUZj5v58jeAR7PtoiXgGCEYT-5lAyA", "secure": True}
]

def create_cookie_file(filename, data):
    with open(filename, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in data:
            domain = c['domain']; flag = "TRUE" if domain.startswith('.') else "FALSE"
            path = c['path']; secure = "TRUE" if c.get('secure', False) else "FALSE"
            expires = int(c.get('expirationDate', 0))
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{c['name']}\t{c['value']}\n")

# --- 4. أوامر البوت ولوحة التحكم ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text(
        f"👋 أهلاً بك {update.effective_user.first_name} في بوت التحميل الذكي!\n\n"
        "🚀 أرسل رابط فيديو من يوتيوب، إنستجرام، أو فيسبوك وسأقوم بتحميله لك فوراً."
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users_count = len(get_users())
    keyboard = [
        [InlineKeyboardButton(f"📊 عدد المشتركين: {users_count}", callback_data="stats")],
        [InlineKeyboardButton("📢 إرسال رسالة للجميع", callback_data="broadcast")]
    ]
    await update.message.reply_text("🛠️ لوحة تحكم المطور:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        users_count = len(get_users())
        await query.edit_message_text(f"📊 إجمالي مستخدمي البوت: {users_count}")
    
    elif query.data == "broadcast":
        await query.edit_message_text("📝 من فضلك قم بإرسال نص الرسالة التي تريد إذاعتها للجميع.")
        context.user_data['waiting_for_broadcast'] = True

# --- 5. منطق التحميل ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ميزة الإذاعة (Broadcast)
    if context.user_data.get('waiting_for_broadcast'):
        if update.effective_user.id == ADMIN_ID:
            users = get_users()
            count = 0
            for u_id in users:
                try:
                    await context.bot.send_message(chat_id=u_id, text=update.message.text)
                    count += 1
                except: pass
            await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم.")
            context.user_data['waiting_for_broadcast'] = False
            return

    url = update.message.text
    if not url.startswith("http"): return

    status = await update.message.reply_text("🔄 جاري معالجة الرابط، انتظر قليلاً...")
    
    cookie_file = None
    if "youtube" in url or "youtu.be" in url: cookie_file = YT_COOKIE_FILE
    elif "instagram" in url: cookie_file = IG_COOKIE_FILE

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'cookiefile': cookie_file, 'user_agent': USER_AGENT}) as ydl:
            info = ydl.extract_info(url, download=False)
        
        if "youtube" in url or "youtu.be" in url:
            qualities = {f.get("height"): f["format_id"] for f in info.get("formats", []) if f.get("vcodec") != "none" and f.get("height")}
            context.user_data.update({"url": url, "qualities": qualities})
            keyboard = [[InlineKeyboardButton(f"🎬 {h}p", callback_data=f"dl_{h}")] for h in sorted(qualities.keys(), reverse=True)[:5]]
            await status.edit_text("✨ اختر الجودة المطلوبة ليوتيوب:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await status.edit_text("📥 جاري التحميل من إنستجرام/فيسبوك...")
            file_path = f"vid_{update.effective_user.id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': file_path, 'cookiefile': cookie_file, 'user_agent': USER_AGENT}) as ydl:
                ydl.download([url])
            await update.message.reply_video(video=open(file_path, "rb"), caption="✅ تم التحميل بواسطة بوتك!")
            os.remove(file_path)
            await status.delete()
    except:
        await status.edit_text("❌ عذراً، هذا الرابط غير مدعوم حالياً أو المحتوى خاص.")

async def youtube_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith("dl_"): return
    await query.answer()
    
    height = query.data.split("_")[1]
    file_path = f"yt_{query.from_user.id}.mp4"
    await query.edit_message_text(f"⏳ جاري تحميل فيديو يوتيوب بجودة {height}p...")
    
    opts = {'format': f'bestvideo[height<={height}]+bestaudio/best', 'outtmpl': file_path, 'cookiefile': YT_COOKIE_FILE}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([context.user_data["url"]])
        await query.message.reply_video(video=open(file_path, "rb"))
    finally:
        if os.path.exists(file_path): os.remove(file_path)

# --- 6. تشغيل السيرفر (لـ Render) ---
class HealthServer(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"Bot Active")

def run_health_server():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), HealthServer).serve_forever()

if name == "main":
    create_cookie_file(YT_COOKIE_FILE, YT_COOKIES_DATA)
    create_cookie_file(IG_COOKIE_FILE, IG_COOKIES_DATA)
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(stats|broadcast)$"))
    app.add_handler(CallbackQueryHandler(youtube_download, pattern="^dl_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 البوت واللوحة قيد التشغيل...")
    app.run_polling()

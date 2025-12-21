import os
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0" 
ADMIN_ID = 7349033289 
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"
DEV_USER = "@TOP_1UP"

# --- 2. إدارة البيانات ---
def get_list(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, "r") as f:
        return list(set(f.read().splitlines()))

def add_to_file(file_path, item_id):
    items = get_list(file_path)
    if str(item_id) not in items:
        with open(file_path, "a") as f:
            f.write(f"{item_id}\n")

# --- 3. معالجة الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return
    
    add_to_file(USERS_FILE, user_id)
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(
        "✨ أهلاً بك في CYBORG!\nأرسل رابط الفيديو الآن للبدء.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return
    
    text = update.message.text
    state = context.user_data.get('state')

    # إحصائيات ومطور
    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`\n\nشكراً لتواصلك! ❤️")
        return
    if "إحصائياتي" in text:
        await update.message.reply_text(f"📊 عدد المشتركين: {len(get_list(USERS_FILE))}\n✅ حالتك: مستخدم نشط.")
        return

    # لوحة التحكم والعمليات الإدارية
    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        btns = [
            [InlineKeyboardButton("📢 إذاعة للكل", callback_data="start_bc")],
            [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="start_ban")]
        ]
        await update.message.reply_text("🛠 لوحة الإدارة:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if state == 'waiting_broadcast':
        users = get_list(USERS_FILE)
        for u in users:
            try: await context.bot.send_message(chat_id=u, text=f"📢 **إشعار:**\n\n{text}", parse_mode="Markdown")
            except: continue
        await update.message.reply_text("✅ تم الإرسال."); context.user_data['state'] = None; return

    if state == 'waiting_ban':
        add_to_file(BAN_FILE, text)
        await update.message.reply_text(f"✅ تم حظر الآيدي: {text}"); context.user_data['state'] = None; return

    # استخراج الرابط
    if "http" in text:
        m = await update.message.reply_text("🔎 جاري تحليل الرابط...")
        ydl_opts = {'quiet': True, 'user_agent': 'Mozilla/5.0'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=False)
                keyboard = [
                    [InlineKeyboardButton("720p (عالية)", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton("480p (متوسطة)", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton("MP3 (صوت)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:40]}...\n\nاختر الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            btn_new = [[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new_proc")]]
            await m.edit_text("❌ خطأ في التحليل.", reply_markup=InlineKeyboardMarkup(btn_new))

# --- 4. معالج الأزرار ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == "new_proc":
        await q.message.reply_text("✨ أرسل رابطاً جديداً الآن:")
        await q.message.delete(); return

    if q.data == "start_bc":
        await q.message.reply_text("📝 أرسل رسالة الإذاعة:"); context.user_data['state'] = 'waiting_broadcast'; return

    if q.data == "start_ban":
        await q.message.reply_text("🆔 أرسل آيدي المستخدم لحظره:"); context.user_data['state'] = 'waiting_ban'; return

    data = q.data.split("|")
    if data[0] == "dl":
        quality, url = data[1], data[2]
        msg = await q.message.reply_text(f"⏳ جاري التحميل...")
        path = f"file_{q.from_user.id}.mp4"
        
        ydl_opts = {'outtmpl': path, 'quiet': True, 'format': f'bestvideo[height<={quality}]+bestaudio/best' if quality != 'mp3' else 'bestaudio/best'}
        if quality == 'mp3': path = path.replace('.mp4', '.mp3'); ydl_opts['outtmpl'] = path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            with open(path, "rb") as f:
                if quality == 'mp3': await q.message.reply_audio(audio=f)
                else: await q.message.reply_video(video=f)
            
            btn_new = [[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new_proc")]]
            await q.message.reply_text("✅ تم التحميل!", reply_markup=InlineKeyboardMarkup(btn_new))
            os.remove(path); await msg.delete()
        except:
            btn_new = [[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new_proc")]]
            await msg.edit_text("❌ فشل التحميل.", reply_markup=InlineKeyboardMarkup(btn_new))

# --- 5. التشغيل ---
if __name__ == "__main__":
    def run_srv():
        HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()
    threading.Thread(target=run_srv, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

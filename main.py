import os
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات الأساسية ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0"
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"   
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net"]
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"

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

def format_size(bytes):
    if not bytes: return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024: return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} GB"

# --- 3. التحقق من الاشتراك ---
async def check_access(update, context):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return "banned"
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ['left', 'kicked']: return "not_subbed"
        except: continue
    return "ok"

# --- 4. أوامر البوت الرئيسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    add_to_file(USERS_FILE, user_id)
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(
        "✨ أهلاً بك في بوت CYBORG!\nأرسل رابط الفيديو الآن وسأعرض لك خيارات الجودة.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    text = update.message.text

    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`\n\nشكراً لتواصلك معنا! نحن نقدر دعمك. ❤️")
        return

    if "إحصائياتي" in text:
        count = len(get_list(USERS_FILE))
        await update.message.reply_text(f"📊 إحصائيات البوت:\n👥 عدد المشتركين: {count}\n✅ حالتك: مستخدم نشط.")
        return

    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        btns = [[InlineKeyboardButton("📢 إذاعة", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 لوحة الإدارة:", reply_markup=InlineKeyboardMarkup(btns))
        return

    if "http" in text:
        if status == "not_subbed":
            await update.message.reply_text("❌ اشترك في القنوات أولاً!")
            return
        
        m = await update.message.reply_text("🔎 جاري تحليل الرابط وحساب الأحجام...")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=False)
                formats = info.get('formats', [])
                
                # حساب أحجام تقريبية
                sizes = {"720": "N/A", "480": "N/A", "360": "N/A"}
                for f in formats:
                    h = str(f.get('height'))
                    if h in sizes and f.get('filesize'):
                        sizes[h] = format_size(f['filesize'])

                keyboard = [
                    [InlineKeyboardButton(f"High (720p) - {sizes['720']}", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton(f"Medium (480p) - {sizes['480']}", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton(f"Low (360p) - {sizes['360']}", callback_data=f"dl|360|{text}")],
                    [InlineKeyboardButton("MP3 (صوت فقط)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:40]}...\n\nاختر الجودة المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await m.edit_text("❌ فشل تحليل الرابط. تأكد أنه فيديو عام.")

# --- 5. معالجة التحميل الفعلي ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == "bc":
        await q.message.reply_text("📝 أرسل رسالة الإذاعة الآن:"); context.user_data['state'] = 'bc'; return
    if q.data == "ban":
        await q.message.reply_text("🆔 أرسل آيدي المستخدم:"); context.user_data['state'] = 'ban'; return

    data = q.data.split("|")
    if data[0] == "dl":
        quality, url = data[1], data[2]
        msg = await q.message.reply_text(f"⏳ جاري تحميل ({quality})... يرجى الانتظار")
        
        path = f"file_{q.from_user.id}.mp4"
        ydl_opts = {
            'outtmpl': path,
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        
        if quality == 'mp3':
            path = path.replace('.mp4', '.mp3')
            ydl_opts.update({'format': 'bestaudio/best', 'outtmpl': path})
        else:
            ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            with open(path, "rb") as f:
                if quality == 'mp3': await q.message.reply_audio(audio=f)
                else: await q.message.reply_video(video=f)
            
            btn_new = [[InlineKeyboardButton("🔄 عملية جديدة", callback_data="start_new")]]
            await q.message.reply_text("✅ تم التحميل بنجاح!", reply_markup=InlineKeyboardMarkup(btn_new))
            os.remove(path); await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ خطأ أثناء التحميل. قد يكون الحجم كبيراً جداً.")

    if q.data == "start_new":
        await q.message.reply_text("✨ أرسل رابطاً جديداً الآن:"); await q.message.delete()

# --- 6. التشغيل والسيرفر ---
def srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=srv, daemon=True).start()
    print("🚀 CYBORG IS ONLINE")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

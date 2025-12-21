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
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net"]
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"

# --- 2. وظائف إدارة البيانات ---
def get_list(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, "r") as f:
        return list(set(f.read().splitlines()))

def add_to_file(file_path, item_id):
    items = get_list(file_path)
    if str(item_id) not in items:
        with open(file_path, "a") as f:
            f.write(f"{item_id}\n")

def format_size(bytes_val):
    if not bytes_val: return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024: return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} GB"

# --- 3. التحقق من الصلاحيات ---
async def check_access(update, context):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return "banned"
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ['left', 'kicked']: return "not_subbed"
        except: continue
    return "ok"

# --- 4. الأوامر الرئيسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    add_to_file(USERS_FILE, user_id)
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    await update.message.reply_text("✨ أهلاً بك في بوت CYBORG!\nأرسل رابط الفيديو للبدء.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    text = update.message.text
    state = context.user_data.get('state')

    # لوحة التحكم والمهام الإدارية
    if state == 'bc' and user_id == ADMIN_ID:
        for u in get_list(USERS_FILE):
            try: await context.bot.send_message(u, f"📢 إشعار إداري:\n\n{text}")
            except: continue
        await update.message.reply_text("✅ تم الإرسال للجميع."); context.user_data['state'] = None; return
    
    if state == 'ban' and user_id == ADMIN_ID:
        add_to_file(BAN_FILE, text); await update.message.reply_text(f"🚫 تم حظر {text}"); context.user_data['state'] = None; return

    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`\n\nشكراً لتواصلك! ❤️")
        return
    if "إحصائياتي" in text:
        await update.message.reply_text(f"📊 المشتركين: {len(get_list(USERS_FILE))}\n✅ أنت مستخدم نشط.")
        return
    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        btns = [[InlineKeyboardButton("📢 إذاعة", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 لوحة الإدارة:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # معالجة الرابط
    if "http" in text:
        if status == "not_subbed":
            await update.message.reply_text("❌ اشترك في القنوات أولاً!"); return
        
        m = await update.message.reply_text("🔎 جاري تحليل الرابط...")
        ydl_opts = {'quiet': True, 'no_warnings': True, 'user_agent': 'Mozilla/5.0'}
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=False)
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
                await m.edit_text(f"🎬 {info.get('title')[:40]}...\n\nاختر الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await m.edit_text("❌ خطأ في التحليل. تأكد من الرابط.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new")]]))

# --- 5. معالج الأزرار ---
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "bc": await q.message.reply_text("📝 أرسل رسالة الإذاعة:"); context.user_data['state'] = 'bc'; return
    if q.data == "ban": await q.message.reply_text("🆔 أرسل الآيدي:"); context.user_data['state'] = 'ban'; return
    if q.data == "new": await q.message.reply_text("✨ أرسل رابطاً جديداً:"); await q.message.delete(); return

    if q.data.startswith("dl|"):
        _, quality, url = q.data.split("|")
        msg = await q.message.reply_text(f"⏳ جاري تحميل {quality}...")
        path = f"file_{q.from_user.id}.mp4"
        ydl_opts = {'outtmpl': path, 'quiet': True}
        if quality == 'mp3':
            path = path.replace('.mp4', '.mp3'); ydl_opts.update({'format': 'bestaudio/best', 'outtmpl': path})
        else:
            ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
            with open(path, "rb") as f:
                if quality == 'mp3': await q.message.reply_audio(audio=f)
                else: await q.message.reply_video(video=f)
            await q.message.reply_text("✅ تم التحميل!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new")]]))
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ فشل التحميل.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 عملية جديدة", callback_data="new")]]))

# --- 6. التشغيل ---
def run_srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

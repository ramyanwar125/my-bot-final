import os
import yt_dlp
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0"
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"
COOKIES_FILE = "cookies.txt" # الملف الذي يحتوي على كوكيز يوتيوب وانستجرام

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

def format_size(bytes_val):
    if not bytes_val: return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024: return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} GB"

# --- 3. إعدادات التحميل المدمجة بالكوكيز ---
def get_common_opts(custom_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    # دمج الكوكيز المرفوعة (يوتيوب وانستجرام) بشكل إجباري
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    
    if custom_opts:
        opts.update(custom_opts)
    return opts

# --- 4. معالجة الرسائل والقائمة السفلية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return
    add_user_id = update.effective_user.id
    add_to_file(USERS_FILE, add_user_id)
    
    # القائمة السفلية المطلوبة (بدء من جديد، الغاء، إحصائيات، مطور)
    kb = [
        ['🔄 بدء من جديد', '❌ إلغاء'],
        ['📊 إحصائياتي', '👨‍💻 المطور']
    ]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(
        "✨ أهلاً بك في CYBORG!\nتم دمج الكوكيز بنجاح. أرسل الرابط الآن للبدء.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if str(user_id) in get_list(BAN_FILE): return

    # أزرار التحكم الجديدة
    if text == '🔄 بدء من جديد':
        await update.message.reply_text("✨ تم تصفير العملية. أرسل رابطاً جديداً الآن.")
        context.user_data.clear()
        return

    if text == '❌ إلغاء':
        await update.message.reply_text("🚫 تم إلغاء العملية الحالية.")
        context.user_data.clear()
        return

    # الأزرار التقليدية
    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`")
        return
    if "إحصائياتي" in text:
        await update.message.reply_text(f"📊 عدد المشتركين: {len(get_list(USERS_FILE))}")
        return
    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        btns = [[InlineKeyboardButton("📢 إذاعة", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 إدارة النظام:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # تحليل الرابط
    if "http" in text:
        m = await update.message.reply_text("🔎 جاري فحص الرابط باستخدام الكوكيز المدمجة...")
        try:
            with yt_dlp.YoutubeDL(get_common_opts()) as ydl:
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
                    [InlineKeyboardButton("MP3 (صوت فقط)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:40]}...\n\nاختر الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await m.edit_text("❌ فشل التحليل. تأكد من أن ملف `cookies.txt` يحتوي على بيانات صحيحة.")

# --- 5. التحميل ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    
    if q.data.startswith("dl|"):
        _, quality, url = q.data.split("|")
        msg = await q.message.reply_text(f"⏳ جاري تحميل {quality}...")
        path = f"file_{q.from_user.id}.mp4"
        
        ydl_opts = get_common_opts({'outtmpl': path})
        if quality == 'mp3':
            path = path.replace('.mp4', '.mp3'); ydl_opts.update({'format': 'bestaudio/best', 'outtmpl': path})
        else:
            ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best/best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
            with open(path, "rb") as f:
                if quality == 'mp3': await q.message.reply_audio(audio=f)
                else: await q.message.reply_video(video=f)
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ فشل التحميل.")

# --- 6. التشغيل ---
def srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

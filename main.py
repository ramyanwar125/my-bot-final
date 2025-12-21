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
BAN_FILE = "banned.txt"
COOKIES_FILE = "cookies.txt" # تأكد من رفع الملف بهذا الاسم تماماً

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

# --- 3. إعدادات استخراج البيانات (الدمج القوي) ---
def get_ydl_options(quality=None, path=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # دمج الكوكيز بشكل إلزامي إذا وجد الملف
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    
    if path:
        opts['outtmpl'] = path
        
    if quality:
        if quality == 'mp3':
            opts.update({'format': 'bestaudio/best'})
        else:
            opts.update({'format': f'bestvideo[height<={quality}]+bestaudio/best/best'})
            
    return opts

# --- 4. أوامر القائمة السفلية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return
    add_to_file(USERS_FILE, user_id)
    
    # القائمة السفلية المطلوبة
    kb = [
        ['🔄 بدء من جديد', '❌ إلغاء'],
        ['📊 إحصائياتي', '👨‍💻 المطور']
    ]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(
        "✨ أهلاً بك في CYBORG!\nتم دمج كوكيز يوتيوب وانستجرام بنجاح.\n\nأرسل رابط الفيديو للبدء 👇",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if str(user_id) in get_list(BAN_FILE): return

    # تنفيذ أوامر الأزرار السفلية
    if text == '🔄 بدء من جديد':
        await update.message.reply_text("🔄 تم تصفير الجلسة. أنا بانتظار رابط جديد منك.")
        return
    if text == '❌ إلغاء':
        await update.message.reply_text("🚫 تم إلغاء المهمة الحالية.")
        return
    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`")
        return
    if "إحصائياتي" in text:
        await update.message.reply_text(f"📊 عدد المشتركين: {len(get_list(USERS_FILE))}")
        return

    # معالجة الرابط
    if "http" in text:
        m = await update.message.reply_text("🔎 جاري تحليل الرابط باستخدام الكوكيز المدمجة...")
        try:
            with yt_dlp.YoutubeDL(get_ydl_options()) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, text, download=False)
                
                keyboard = [
                    [InlineKeyboardButton("720p (High)", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton("480p (Medium)", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton("MP3 (Audio Only)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 {info.get('title')[:50]}...\n\nاختر الجودة للتحميل:", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"Error: {e}")
            await m.edit_text("❌ فشل التحليل.\nتأكد من صحة الكوكيز أو أن الفيديو غير محجوب.")

# --- 5. التحميل ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data.startswith("dl|"):
        _, quality, url = q.data.split("|")
        msg = await q.message.reply_text(f"⏳ جاري تحميل جودة {quality}...")
        
        ext = "mp3" if quality == "mp3" else "mp4"
        path = f"vid_{q.from_user.id}.{ext}"
        
        try:
            with yt_dlp.YoutubeDL(get_ydl_options(quality, path)) as ydl:
                await asyncio.to_thread(ydl.download, [url])
            
            with open(path, "rb") as f:
                if quality == "mp3": await q.message.reply_audio(f)
                else: await q.message.reply_video(f)
            
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ حدث خطأ أثناء التحميل.")

# --- 6. التشغيل السحابي ---
def srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

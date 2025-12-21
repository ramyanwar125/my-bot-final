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
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0" # تأكد من وضع التوكن الخاص بك
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"   
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net"]
USERS_FILE = "users.txt"

# --- 2. دالة تحويل الحجم إلى صيغة مقروءة ---
def format_size(bytes):
    if bytes is None: return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024: return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} GB"

# --- 3. إدارة البيانات ---
def get_users_count():
    if not os.path.exists(USERS_FILE): return 0
    with open(USERS_FILE, "r") as f:
        return len(set(f.read().splitlines()))

def add_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "w").close()
    with open(USERS_FILE, "a+") as f:
        f.seek(0)
        if str(user_id) not in f.read().splitlines():
            f.write(f"{user_id}\n")

# --- 4. معالجة الأوامر الرئيسية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if update.effective_user.id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    await update.message.reply_text(
        "✨ أهلاً بك في CYBORG HD!\nأرسل رابط الفيديو وسأعرض لك الجودات المتاحة مع حجم كل منها.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`\n\nشكراً لتواصلك معنا! ❤️")
        return

    if "إحصائياتي" in text:
        await update.message.reply_text(f"📊 إجمالي مستخدمي البوت: {get_users_count()}\n✅ أنت عضو نشط في النظام.")
        return

    if "http" in text:
        m = await update.message.reply_text("🔎 جاري فحص الرابط وحساب الأحجام...")
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(text, download=False)
                formats = info.get('formats', [])
                
                # البحث عن أحجام تقريبية للجودات المختلفة
                res = {"1080": "N/A", "720": "N/A", "480": "N/A", "360": "N/f"}
                for f in formats:
                    h = str(f.get('height'))
                    if h in res and f.get('filesize'):
                        res[h] = format_size(f['filesize'])

                keyboard = [
                    [InlineKeyboardButton(f"High (720p) - {res['720']}", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton(f"Medium (480p) - {res['480']}", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton(f"Low (360p) - {res['360']}", callback_data=f"dl|360|{text}")],
                    [InlineKeyboardButton("MP3 (صوت فقط)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 عنوان الفيديو: {info.get('title')[:50]}...\n\nاختر الجودة المناسبة لك:", 
                                  reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await m.edit_text("❌ حدث خطأ في استخراج البيانات. الرابط قد يكون غير مدعوم.")

# --- 5. تنفيذ التحميل المختار ---
async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split("|")
    quality, url = data[1], data[2]
    
    await q.edit_message_text(f"⏳ جاري تحميل الجودة ({quality})... يرجى الانتظار")
    
    path = f"vid_{q.from_user.id}_{quality}.mp4"
    ydl_opts = {'outtmpl': path, 'quiet': True}
    
    if quality == "mp3":
        ydl_opts.update({'format': 'bestaudio/best', 'outtmpl': path.replace(".mp4", ".mp3")})
        path = path.replace(".mp4", ".mp3")
    else:
        ydl_opts['format'] = f'bestvideo[height<={quality}]+bestaudio/best/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if quality == "mp3": await q.message.reply_audio(audio=open(path, "rb"))
        else: await q.message.reply_video(video=open(path, "rb"))
        
        await q.message.reply_text("✅ تم التحميل بنجاح!\nشكراً لاستخدامك CYBORG.")
        os.remove(path)
        await q.message.delete()
    except:
        await q.message.reply_text("❌ فشل التحميل. قد يكون الحجم كبيراً جداً على تلجرام.")

# --- 6. التشغيل ---
if __name__ == "__main__":
    # تشغيل سيرفر ويب بسيط للبقاء حياً على Render
    def srv():
        HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()
    threading.Thread(target=srv, daemon=True).start()

    print("🚀 CYBORG HD READY!")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

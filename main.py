import os
import asyncio
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import BadRequest

# --- 1. الإعدادات الأساسية ---
TOKEN = "8579186374:AAEUzOGQ8y6jIjYWRkOKM_x7QhB1xaiyZSA"
ADMIN_ID = 7349033289  # ID المطور الخاص بك
DEV_USER = "@TOP_1UP"   # يوزر المطور
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net"] # معرفات القنوات للاشتراك الإجباري
USERS_FILE = "users.txt"

# --- 2. إدارة المستخدمين ---
def add_user(user_id):
    if not os.path.exists(USERS_FILE): open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r+") as f:
        users = f.read().splitlines()
        if str(user_id) not in users: f.write(f"{user_id}\n")

# --- 3. التحقق من الاشتراك الإجباري ---
async def check_sub(context, user_id):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False # في حال لم يكن البوت مشرفاً أو القناة غير موجودة
    return True

# --- 4. واجهة البوت والأزرار ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    
    # رسالة ترحيبية جميلة
    welcome_text = (
        f"✨ أهلاً بك يا {user.first_name} في بوت التحميل الشامل!\n\n"
        "🚀 يمكنك من خلالي تحميل الفيديوهات من:\n"
        "• يوتيوب (YouTube)\n• إنستجرام (Instagram)\n• فيسبوك (Facebook)\n\n"
        "📢 يرجى الاشتراك في قنواتنا أولاً لاستخدام البوت."
    )
    
    # القائمة السفلية (Reply Keyboard)
    reply_kb = [['📥 تحميل فيديو', '📊 إحصائيات'], ['👨‍💻 المطور', '📢 القنوات']]
    markup = ReplyKeyboardMarkup(reply_kb, resize_keyboard=True)
    
    # أزرار الاشتراك الإجباري
    inline_kb = [
        [InlineKeyboardButton("قناة 1 📢", url="https://t.me/T_U_H1"),
         InlineKeyboardButton("قناة 2 📢", url="https://t.me/T_U_H2")],
        [InlineKeyboardButton("قناة 3 📢", url="https://t.me/Mega0Net")],
        [InlineKeyboardButton("✅ تم الاشتراك (تفعيل)", callback_data="check_sub")]
    ]
    
    await update.message.reply_text(welcome_text, reply_markup=markup)
    if not await check_sub(context, user.id):
        await update.message.reply_text("⚠️ يجب عليك الاشتراك في القنوات لتتمكن من استخدام البوت:", 
                                       reply_markup=InlineKeyboardMarkup(inline_kb))

# --- 5. معالجة الرسائل والتحميل ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == '👨‍💻 المطور':
        await update.message.reply_text(f"👤 مطور البوت: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`", parse_mode="Markdown")
        return
    elif text == '📊 إحصائيات' and user_id == ADMIN_ID:
        count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 عدد مستخدمي البوت: {count}")
        return

    # التحقق من الاشتراك قبل أي عملية تحميل
    if not await check_sub(context, user_id):
        await update.message.reply_text("❌ عذراً، يجب عليك الاشتراك في القنوات أولاً!")
        return

    if "http" in text:
        msg = await update.message.reply_text("🔍 جاري معالجة الرابط، انتظر قليلاً...")
        try:
            path = f"video_{user_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([text])
            await update.message.reply_video(video=open(path, "rb"), caption="✅ تم التحميل بواسطة @TOP_1UP")
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ حدث خطأ! تأكد من الرابط أو حاول لاحقاً.")

# --- 6. معالجة ضغطات الأزرار ---
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "check_sub":
        if await check_sub(context, q.from_user.id):
            await q.edit_message_text("✅ شكراً لك! تم تفعيل البوت بنجاح. أرسل الآن أي رابط للتحميل.")
        else:
            await q.answer("❌ لم تشترك في جميع القنوات بعد!", show_alert=True)

# --- 7. تشغيل السيرفر والبوت ---
def run_srv():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("🚀 البوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)

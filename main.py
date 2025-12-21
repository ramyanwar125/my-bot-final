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

# --- 1. الإعدادات ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0"
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"   
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net"]
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"

# --- 2. إدارة البيانات ---
def manage_list(file_path, item_id, action="add"):
    if not os.path.exists(file_path): open(file_path, "w").close()
    with open(file_path, "r+") as f:
        items = f.read().splitlines()
        if action == "add" and str(item_id) not in items:
            f.seek(0, 2); f.write(f"{item_id}\n")
            return items
        return items

# --- 3. التحقق من الوصول ---
async def check_access(update, context):
    user_id = update.effective_user.id
    if str(user_id) in manage_list(BAN_FILE, user_id, "get"): return "banned"
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ['left', 'kicked']: return "not_subbed"
        except: continue
    return "ok"

# --- 4. أوامر البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    manage_list(USERS_FILE, user_id, "add")
    
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    welcome = f"✨ أهلاً بك في بوت CYBORG!\nفقط أرسل رابط الفيديو وسأقوم بحفظه لك فوراً."
    await update.message.reply_text(welcome, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    text = update.message.text

    # --- 1. إصلاح تواصل مع المطور ---
    if "المطور" in text:
        dev_msg = (
            f"👤 **المطور:** {DEV_USER}\n"
            f"🆔 **الآيدي:** `{ADMIN_ID}`\n\n"
            "شكراً جزيلاً لك على تواصلك واستخدامك لبوتنا! نحن ممتنون جداً لدعمك. ❤️"
        )
        await update.message.reply_text(dev_msg, parse_mode="Markdown")
        return 

    # --- 2. إصلاح الإحصائيات (إظهار عدد المستخدمين الكلي) ---
    if "إحصائياتي" in text:
        all_users = len(manage_list(USERS_FILE, 0, "get"))
        msg = (
            f"📊 **إحصائيات البوت:**\n\n"
            f"👥 عدد مستخدمي البوت: {all_users}\n"
            f"✅ حالتك: مستخدم نشط\n\n"
            f"شكراً لكونك جزءاً من عائلة CYBORG! 🤖"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # --- 3. لوحة التحكم (للأدمن) ---
    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        users = len(manage_list(USERS_FILE, 0, "get"))
        btns = [[InlineKeyboardButton(f"👥 مستخدمين: {users}", callback_data="n")],
                [InlineKeyboardButton("📢 إذاعة", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 لوحة الإدارة:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # --- 4. التحميل + رسالة الانهاء ---
    if "http" in text:
        if status == "not_subbed":
            await update.message.reply_text("❌ اشترك في القنوات أولاً!")
            return
        
        m = await update.message.reply_text("⏳ جاري التحميل... يرجى الانتظار")
        try:
            path = f"vid_{user_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([text])
            
            # إرسال الفيديو
            await update.message.reply_video(video=open(path, "rb"))
            
            # رسالة الانهاء (تظهر بعد الفيديو)
            await update.message.reply_text("✅ تم تحميل الفيديو بنجاح!\nشكراً لاستخدامك بوت CYBORG. ❤️")
            
            os.remove(path)
            await m.delete()
        except:
            await m.edit_text("❌ عذراً، حدث خطأ أثناء التحميل. تأكد من جودة الرابط.")
        return

# --- 5. التشغيل والسيرفر ---
def run_srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    print("\n🚀 CYBORG BOT STARTED SUCCESSFULLY!\n")
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer()))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

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
    
    # القائمة السفلية (بدون كلمة تحميل)
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    welcome = "✨ أهلاً بك في بوت CYBORG!\nفقط أرسل رابط الفيديو وسأقوم بحفظه لك فوراً."
    await update.message.reply_text(welcome, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    text = update.message.text

    # --- إصلاح تواصل مع المطور (شرط دقيق لمنع التكرار) ---
    if "المطور" in text:
        dev_msg = (
            f"👤 **المطور:** {DEV_USER}\n"
            f"🆔 **الآيدي:** `{ADMIN_ID}`\n\n"
            "شكراً جزيلاً لك على تواصلك واستخدامك لبوت CYBORG. نحن ممتنون جداً لدعمك ونقدر ثقتك بنا! ❤️"
        )
        await update.message.reply_text(dev_msg, parse_mode="Markdown")
        return 

    if "إحصائياتي" in text:
        await update.message.reply_text("📊 أهلاً بك! أنت عضو نشط في عائلة CYBORG.")
        return

    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        users = len(manage_list(USERS_FILE, 0, "get"))
        btns = [[InlineKeyboardButton(f"👥 مستخدمين: {users}", callback_data="n")],
                [InlineKeyboardButton("📢 إذاعة", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 لوحة الإدارة:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # --- التحميل المباشر ---
    if "http" in text:
        if status == "not_subbed":
            await update.message.reply_text("❌ اشترك في القنوات أولاً!")
            return
        
        m = await update.message.reply_text("⏳ جاري التحميل...")
        try:
            path = f"vid_{user_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([text])
            
            # إرسال الفيديو بدون أي نصوص (No Caption)
            await update.message.reply_video(video=open(path, "rb"))
            os.remove(path)
            await m.delete()
        except:
            await m.edit_text("❌ عذراً، لم أتمكن من تحميل هذا الرابط.")
        return

# --- 5. التشغيل والسيرفر ---
def run_srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    # رسالة الترحيب في بداية التشغيل لتجنب خطأ NameError
    print("\n" + "="*30)
    print("🚀 CYBORG BOT STARTED SUCCESSFULLY!")
    print(f"👨‍💻 DEV: {DEV_USER}")
    print("="*30 + "\n")
    
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer()))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

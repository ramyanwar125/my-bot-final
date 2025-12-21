import os
import asyncio
import yt_dlp
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات الأساسية ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0"
ADMIN_ID = 7349033289  # آيديك الخاص
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
        elif action == "remove" and str(item_id) in items:
            items.remove(str(item_id))
            f.seek(0); f.truncate(); f.write("\n".join(items) + ("\n" if items else ""))
        return items

# --- 3. التحقق من الحظر والاشتراك ---
async def check_access(update, context):
    user_id = update.effective_user.id
    if str(user_id) in manage_list(BAN_FILE, user_id, "get"): return "banned"
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ['left', 'kicked']: return "not_subbed"
        except: continue
    return "ok"

# --- 4. واجهة البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    status = await check_access(update, context)
    if status == "banned": return
    
    manage_list(USERS_FILE, user.id, "add")
    
    # القائمة السفلية مع زر الإلغاء
    kb = [['📥 تحميل', '📊 إحصائياتي'], ['👨‍💻 المطور']]
    if user.id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    await update.message.reply_text(f"✨ أهلاً بك {user.first_name} في بوت CYBORG!\nأرسل الرابط أو اختر من القائمة:", reply_markup=markup)
    
    if status == "not_subbed":
        btns = [[InlineKeyboardButton(f"قناة {i+1} 📢", url=f"https://t.me/{c.replace('@','')}")] for i, c in enumerate(CHANNELS)]
        btns.append([InlineKeyboardButton("✅ تم الاشتراك", callback_data="verify")])
        await update.message.reply_text("⚠️ اشترك أولاً لتفعيل البوت:", reply_markup=InlineKeyboardMarkup(btns))

# --- 5. معالجة الرسائل والتحميل ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    text = update.message.text

    # معالجة زر الإلغاء
    if text == '❌ إلغاء':
        context.user_data.clear()
        kb = [['📥 تحميل', '📊 إحصائياتي'], ['👨‍💻 المطور']]
        if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
        await update.message.reply_text("📥 تم إلغاء العملية والعودة للقائمة.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    if text == '📥 تحميل':
        # إظهار زر الإلغاء للمستخدم عند طلب الرابط
        await update.message.reply_text("🔗 من فضلك أرسل رابط الفيديو الآن:", 
                                       reply_markup=ReplyKeyboardMarkup([['❌ إلغاء']], resize_keyboard=True))
        return

    if text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        users = len(manage_list(USERS_FILE, 0, "get"))
        btns = [[InlineKeyboardButton(f"👥 مستخدمين: {users}", callback_data="n")],
                [InlineKeyboardButton("📢 إذاعة للكل", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 إعدادات المسؤول:", reply_markup=InlineKeyboardMarkup(btns))
        return

    # منطق تحميل الفيديو
    if "http" in text:
        if status == "not_subbed":
            await update.message.reply_text("❌ يجب الاشتراك في القنوات أولاً!")
            return
        
        m = await update.message.reply_text("⏳ جاري التحميل...")
        try:
            path = f"vid_{user_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([text])
            await update.message.reply_video(video=open(path, "rb"), caption=f"✅ تم التحميل بواسطة {DEV_USER}")
            os.remove(path); await m.delete()
        except:
            await m.edit_text("❌ خطأ! الرابط غير مدعوم أو المحتوى خاص.")

# --- 6. التشغيل ---
def run_srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer())) # معالج بسيط للكولباك
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("🚀 البوت يعمل مع زر الإلغاء...")
    app.run_polling(drop_pending_updates=True)

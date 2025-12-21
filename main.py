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

# --- 1. الإعدادات الأساسية ---
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
        elif action == "get": return items
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

# --- 4. واجهة القوائم (تم حذف كلمة تحميل) ---
def get_main_kb(user_id):
    kb = [['📊 إحصائياتي', '👨‍💻 المطور']]
    if user_id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# --- 5. أوامر البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    status = await check_access(update, context)
    if status == "banned": return
    
    manage_list(USERS_FILE, user.id, "add")
    welcome = f"✨ أهلاً بك {user.first_name} في بوت CYBORG!\nفقط أرسل رابط الفيديو وسأقوم بحفظه لك فوراً."
    await update.message.reply_text(welcome, reply_markup=get_main_kb(user.id))
    
    if status == "not_subbed":
        btns = [[InlineKeyboardButton(f"قناة {i+1} 📢", url=f"https://t.me/{c.replace('@','')}")] for i, c in enumerate(CHANNELS)]
        btns.append([InlineKeyboardButton("✅ تم الاشتراك", callback_data="verify")])
        await update.message.reply_text("⚠️ اشترك أولاً لتفعيل البوت:", reply_markup=InlineKeyboardMarkup(btns))

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    text = update.message.text

    # معالجة الأزرار (تواصل مع المطور)
    if text == '👨‍💻 المطور':
        dev_msg = (
            f"👤 **مطور البوت:** {DEV_USER}\n"
            f"🆔 **الآيدي:** `{ADMIN_ID}`\n\n"
            "شكراً لتواصلك معنا! نحن نقدر استخدامك للبوت ونسعى دائماً لتطويره لخدمتك بأفضل شكل ممكن. ❤️"
        )
        await update.message.reply_text(dev_msg, parse_mode="Markdown")
        
    elif text == '📊 إحصائياتي':
        await update.message.reply_text(f"📊 أهلاً {update.effective_user.first_name}\nأنت عضو مميز في عائلة CYBORG.")
        
    elif text == '🛠 لوحة التحكم' and user_id == ADMIN_ID:
        users = len(manage_list(USERS_FILE, 0, "get"))
        btns = [[InlineKeyboardButton(f"👥 مستخدمين: {users}", callback_data="none")],
                [InlineKeyboardButton("📢 إذاعة", callback_data="bc"), InlineKeyboardButton("🚫 حظر", callback_data="ban")]]
        await update.message.reply_text("🛠 لوحة الإدارة:", reply_markup=InlineKeyboardMarkup(btns))
    
    # تنفيذ الإذاعة والحظر
    elif context.user_data.get('state') == 'bc' and user_id == ADMIN_ID:
        for u in manage_list(USERS_FILE, 0, "get"):
            try: await context.bot.send_message(chat_id=u, text=text)
            except: pass
        await update.message.reply_text("✅ تم الإرسال."); context.user_data['state'] = None
    elif context.user_data.get('state') == 'ban' and user_id == ADMIN_ID:
        manage_list(BAN_FILE, text, "add")
        await update.message.reply_text(f"🚫 تم حظر {text}"); context.user_data['state'] = None

    # التحميل (تم حذف المعرف من الكابشن)
    elif "http" in text:
        if status == "not_subbed":
            await update.message.reply_text("❌ اشترك في القنوات أولاً!")
            return
        m = await update.message.reply_text("⏳ جاري المعالجة...")
        try:
            path = f"vid_{user_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([text])
            # تم إزالة caption المعرف هنا
            await update.message.reply_video(video=open(path, "rb"))
            os.remove(path); await m.delete()
        except:
            await m.edit_text("❌ عذراً، لم أتمكن من تحميل هذا الرابط.")

# --- 6. تفاعل الأزرار ---
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "verify":
        if await check_access(update, context) == "ok":
            await q.edit_message_text("✅ تم التفعيل! أرسل أي رابط الآن.")
        else:
            await q.answer("❌ لم تشترك في كل القنوات!", show_alert=True)
    elif q.data == "bc":
        await q.message.reply_text("📝 أرسل الرسالة:"); context.user_data['state'] = 'bc'
    elif q.data == "ban":
        await q.message.reply_text("🆔 أرسل الآيدي:"); context.user_data['state'] = 'ban'

# --- 7. تشغيل السيرفر ---
def run_srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    # رسالة ترحيبية عند بداية تشغيل السكريبت
    print("---------------------------------------")
    print("🚀 CYBORG BOT IS STARTING...")
    print("✅ DEVELOPER: @TOP_1UP")
    print("✅ STATUS: ACTIVE & SECURE")
    print("---------------------------------------")
    
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling(drop_pending_updates=True)

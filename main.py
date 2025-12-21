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
TOKEN = "8579186374:AAEUzOGQ8y6jIjYWRkOKM_x7QhB1xaiyZSA"
ADMIN_ID = 7349033289  # آيديك الخاص
DEV_USER = "@TOP_1UP"   # يوزر المطور
# قنوات الاشتراك الإجباري
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
    # التحقق من الحظر
    if str(user_id) in manage_list(BAN_FILE, user_id, "get"):
        return "banned"
    # التحقق من الاشتراك
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
    
    # رسالة ترحيبية احترافية
    welcome = (
        f"✨ أهلاً بك يا {user.first_name} في بوت CYBORG!\n\n"
        "📥 أرسل لي أي رابط من (يوتيوب، إنستجرام، فيسبوك) وسأقوم بتحميله لك فوراً بأعلى جودة.\n\n"
        "📢 ملاحظة: يجب أن تكون مشتركاً في قنوات البوت ليعمل معك."
    )
    
    # القائمة السفلية
    kb = [['📥 تحميل', '📊 إحصائياتي'], ['👨‍💻 المطور']]
    if user.id == ADMIN_ID: kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(welcome, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    
    if status == "not_subbed":
        btns = [[InlineKeyboardButton(f"قناة {i+1} 📢", url=f"https://t.me/{c.replace('@','')}")] for i, c in enumerate(CHANNELS)]
        btns.append([InlineKeyboardButton("✅ تم الاشتراك (تفعيل)", callback_data="verify")])
        await update.message.reply_text("⚠️ يرجى الاشتراك في القنوات أدناه لتفعيل البوت:", reply_markup=InlineKeyboardMarkup(btns))

# --- 5. لوحة التحكم (للمطور فقط) ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users = len(manage_list(USERS_FILE, 0, "get"))
    bans = len(manage_list(BAN_FILE, 0, "get"))
    
    btns = [
        [InlineKeyboardButton(f"👥 مستخدمين: {users}", callback_data="n"), InlineKeyboardButton(f"🚫 محظورين: {bans}", callback_data="n")],
        [InlineKeyboardButton("📢 إذاعة للكل", callback_data="bc"), InlineKeyboardButton("📄 نسخة احتياطية", callback_data="bak")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban"), InlineKeyboardButton("✅ فك حظر", callback_data="unban")]
    ]
    await update.message.reply_text("🛠 **إعدادات المسؤول**", reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")

# --- 6. معالجة الرسائل ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    status = await check_access(update, context)
    if status == "banned": return
    
    text = update.message.text
    if text == '🛠 لوحة التحكم': await admin_panel(update, context); return
    if text == '👨‍💻 المطور': 
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`", parse_mode="Markdown"); return

    # عمليات الأدمن
    if user_id == ADMIN_ID:
        if context.user_data.get('state') == 'bc':
            for u in manage_list(USERS_FILE, 0, "get"):
                try: await context.bot.send_message(chat_id=u, text=text)
                except: pass
            await update.message.reply_text("✅ تم الإرسال للجميع."); context.user_data['state'] = None; return
        elif context.user_data.get('state') == 'ban':
            manage_list(BAN_FILE, text, "add")
            await update.message.reply_text(f"🚫 تم حظر {text}"); context.user_data['state'] = None; return
        elif context.user_data.get('state') == 'unban':
            manage_list(BAN_FILE, text, "remove")
            await update.message.reply_text(f"✅ فك حظر {text}"); context.user_data['state'] = None; return

    # التحميل
    if "http" in text:
        if status == "not_subbed": await update.message.reply_text("❌ اشترك أولاً!"); return
        m = await update.message.reply_text("⏳ جاري التحميل...")
        try:
            path = f"vid_{user_id}.mp4"
            with yt_dlp.YoutubeDL({'format': 'best', 'outtmpl': path, 'quiet': True}) as ydl:
                ydl.download([text])
            await update.message.reply_video(video=open(path, "rb"), caption=f"✅ تم بواسطة {DEV_USER}")
            os.remove(path); await m.delete()
        except: await m.edit_text("❌ حدث خطأ في الرابط!")

# --- 7. الأزرار التفاعلية ---
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "verify":
        if await check_access(update, context) == "ok": await q.edit_message_text("✅ تم التفعيل بنجاح!")
        else: await q.answer("❌ لم تشترك في كل القنوات بعد!", show_alert=True)
    elif q.data == "bc": await q.message.reply_text("📝 أرسل رسالة الإذاعة:"); context.user_data['state'] = 'bc'
    elif q.data == "ban": await q.message.reply_text("🆔 أرسل آيدي المستخدم:"); context.user_data['state'] = 'ban'
    elif q.data == "unban": await q.message.reply_text("🆔 أرسل الآيدي لفك الحظر:"); context.user_data['state'] = 'unban'
    elif q.data == "bak": await context.bot.send_document(chat_id=ADMIN_ID, document=open(USERS_FILE, "rb"))

# --- 8. التشغيل ---
def run_srv():
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling(drop_pending_updates=True)

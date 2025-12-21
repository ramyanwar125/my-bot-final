import os
import asyncio
import yt_dlp
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات الأساسية ---
TOKEN = "8579186374:AAHOKfRnSWG0zctzxff5YfMkEhtw8kD38G0"
ADMIN_ID = 7349033289  # آيدي المطور
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"

# --- 2. إدارة البيانات ---
def manage_data(file, user_id, action="add"):
    if not os.path.exists(file): open(file, "w").close()
    with open(file, "r+") as f:
        data = f.read().splitlines()
        if action == "add" and str(user_id) not in data:
            f.seek(0, 2); f.write(f"{user_id}\n")
        elif action == "remove" and str(user_id) in data:
            data.remove(str(user_id))
            f.seek(0); f.truncate(); f.write("\n".join(data) + "\n")
        return data

# --- 3. التحقق من الحظر والاشتراك ---
async def is_banned(user_id):
    banned_list = manage_data(BAN_FILE, user_id, action="get")
    return str(user_id) in banned_list

# --- 4. لوحة التحكم المطورة ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_banned(user_id): return # تجاهل المحظورين
    
    manage_data(USERS_FILE, user_id, "add")
    
    # قائمة الأزرار السفلية
    main_kb = [['📥 تحميل', '📊 إحصائياتي'], ['👨‍💻 المطور']]
    if user_id == ADMIN_ID: main_kb.append(['🛠 لوحة التحكم'])
    
    await update.message.reply_text(
        f"✨ أهلاً {update.effective_user.first_name}!\nأرسل رابط الفيديو للبدء.",
        reply_markup=ReplyKeyboardMarkup(main_kb, resize_keyboard=True)
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    users_count = len(manage_data(USERS_FILE, 0, "get"))
    banned_count = len(manage_data(BAN_FILE, 0, "get"))
    
    keyboard = [
        [InlineKeyboardButton(f"👥 مستخدمين: {users_count}", callback_data="none"),
         InlineKeyboardButton(f"🚫 محظورين: {banned_count}", callback_data="none")],
        [InlineKeyboardButton("📢 إذاعة (Broadcast)", callback_data="broadcast")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="ban_user"),
         InlineKeyboardButton("✅ فك حظر", callback_data="unban_user")],
        [InlineKeyboardButton("📄 نسخة احتياطية", callback_data="backup")]
    ]
    await update.message.reply_text("🛠 **إعدادات المسؤول**", reply_markup=InlineKeyboardMarkup(keyboard))

# --- 5. معالجة الرسائل ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_banned(user_id): return
    
    text = update.message.text

    if text == '🛠 لوحة التحكم':
        await admin_panel(update, context); return

    # تنفيذ الإذاعة
    if context.user_data.get('waiting_broadcast'):
        users = manage_data(USERS_FILE, 0, "get")
        for u in users:
            try: await context.bot.send_message(chat_id=u, text=text)
            except: pass
        await update.message.reply_text("✅ تم إرسال الإذاعة للجميع."); context.user_data['waiting_broadcast'] = False; return

    # تنفيذ الحظر
    if context.user_data.get('waiting_ban'):
        manage_data(BAN_FILE, text, "add")
        await update.message.reply_text(f"🚫 تم حظر المستخدم {text}"); context.user_data['waiting_ban'] = False; return

    # تنفيذ فك الحظر
    if context.user_data.get('waiting_unban'):
        manage_data(BAN_FILE, text, "remove")
        await update.message.reply_text(f"✅ تم فك الحظر عن {text}"); context.user_data['waiting_unban'] = False; return

    # منطق التحميل
    if "http" in text:
        msg = await update.message.reply_text("⏳ جاري المعالجة...")
        # (هنا يوضع كود yt-dlp للتحميل كما في المثال السابق)
        await msg.edit_text("✅ رابط مستلم، جاري التحميل...")

# --- 6. تفاعل الأزرار ---
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "broadcast":
        await q.message.reply_text("📝 أرسل رسالة الإذاعة:")
        context.user_data['waiting_broadcast'] = True
    elif q.data == "ban_user":
        await q.message.reply_text("🆔 أرسل آيدي (ID) المستخدم لحظره:")
        context.user_data['waiting_ban'] = True
    elif q.data == "unban_user":
        await q.message.reply_text("🆔 أرسل آيدي (ID) المستخدم لفك حظره:")
        context.user_data['waiting_unban'] = True
    elif q.data == "backup":
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(USERS_FILE, "rb"))

# --- التشغيل ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
app.run_polling()

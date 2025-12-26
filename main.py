import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
from waitress import serve
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- 1. سرفر الويب للبقاء حياً ---
app_web = Flask('')
@app_web.route('/')
def home(): return "⚡ FAST MEDIA Is Online!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    serve(app_web, host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. الإعدادات ---
TOKEN = "8254937829:AAGgMOc0z68Rqm5MAoURNmZNslH60o2LDJw" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
BOT_NAME = "『 ＦＡＳＴ ＭＥＤＩＡ 』"
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net", "@Fast_Mediia"]
USERS_FILE = "users.txt"
COOKIES_FILE = "cookies.txt"

# --- 3. وظائف الإدارة والبيانات ---
def get_users_list():
    if not os.path.exists(USERS_FILE): return []
    with open(USERS_FILE, "r") as f:
        return f.read().splitlines()

def add_user(user_id):
    users = get_users_list()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

async def is_subscribed(context, user_id):
    if user_id == ADMIN_ID: return True
    for chan in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=chan, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

# --- 4. واجهة الترحيب المطلوبة ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    
    kb = [['🔄 بدء من جديد'], ['📢 القنوات']]
    if user.id == ADMIN_ID:
        kb.append(['📊 الإحصائيات', '📣 إذاعة'])
    kb.append(['👨‍💻 المطور'])
    
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome_text = (
        f"✨━━━━━━━━━━━━━✨\n"
        f"  🙋‍♂️ أهلاً بك يا <b>{user.first_name}</b>\n"
        f"  🌟 في عالم {BOT_NAME}\n"
        f"✨━━━━━━━━━━━━━✨\n\n"
        f"🚀 أنا بوت سريع جداً لتحميل الفيديوهات\n"
        f"📱 من المنصات التالية بأعلى جودة:\n\n"
        f"📸 Instagram | 🎵 TikTok\n"
        f"👻 Snapchat  | 🔵 Facebook\n\n"
        f"👇 فقط أرسل الرابط واترك الباقي عليّ!"
    )
    await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)

# --- 5. معالج الرسائل والإدارة ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔄 بدء من جديد':
        await start(update, context)
        return
    elif text == '👨‍💻 المطور':
        await update.message.reply_text(f"👑 <b>المطور المسؤول:</b> {DEV_USER}", parse_mode=ParseMode.HTML)
        return
    elif text == '📢 القنوات':
        links = "\n".join([f"🔗 {c}" for c in CHANNELS])
        await update.message.reply_text(f"📢 <b>قنوات الاشتراك الإجباري:</b>\n\n{links}", parse_mode=ParseMode.HTML)
        return

    # أزرار المطور (الإذاعة والإحصائيات)
    if user_id == ADMIN_ID:
        if text == '📊 الإحصائيات':
            count = len(get_users_list())
            await update.message.reply_text(f"📊 <b>إحصائيات البوت الثابتة:</b>\n\n👤 عدد المشتركين: <code>{count}</code>", parse_mode=ParseMode.HTML)
            return
        elif text == '📣 إذاعة':
            await update.message.reply_text("📥 <b>أرسل الآن الرسالة التي تريد إذاعتها (نص، صورة، فيديو):</b>", parse_mode=ParseMode.HTML)
            context.user_data['waiting_for_broadcast'] = True
            return
        elif context.user_data.get('waiting_for_broadcast'):
            users = get_users_list()
            success, fail = 0, 0
            broadcast_msg = await update.message.reply_text(f"🚀 جاري الإذاعة لـ {len(users)} مستخدم...")
            for uid in users:
                try:
                    await context.bot.copy_message(chat_id=uid, from_chat_id=user_id, message_id=update.message.message_id)
                    success += 1
                except: fail += 1
            await broadcast_msg.edit_text(f"✅ <b>تمت الإذاعة بنجاح!</b>\n\n🟢 نجاح: {success}\n🔴 فشل: {fail}", parse_mode=ParseMode.HTML)
            context.user_data['waiting_for_broadcast'] = False
            return

    # معالجة الروابط (التحميل)
    if "http" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("⚠️ <b>يجب الاشتراك في القنوات أولاً!</b>\nاضغط على زر 📢 القنوات للاشتراك.", parse_mode=ParseMode.HTML)
            return

        status = await update.message.reply_text("⌛", parse_mode=ParseMode.HTML)
        ydl_opts = {
            'quiet': True, 
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None, 
            'format': 'best[ext=mp4]/best'
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # استخراج المعلومات وفحص الحجم
                info = await asyncio.to_thread(ydl.extract_info, text, download=False)
                size_mb = (info.get('filesize') or info.get('filesize_approx') or 0) / (1024*1024)
                
                if size_mb > 50:
                    await status.edit_text(f"⚠️ <b>الحجم كبير جداً ({size_mb:.1f}MB)!</b>\nتليجرام يمنع الرفع أكثر من 50MB.", parse_mode=ParseMode.HTML)
                    return
                
                await status.edit_text("⏳")
                caption = f"✅ <b>تم التحميل بنجاح!</b>\n✨ <b>بواسطة:</b> {BOT_NAME}"
                
                # إرسال الفيديو مباشرة
                await context.bot.send_video(chat_id=user_id, video=info.get('url'), caption=caption, parse_mode=ParseMode.HTML)
            
            await status.delete()
            # رسالة الشكر النهائية
            await context.bot.send_message(user_id, "✨━━━━━━━━━━━━━✨\n🙏 <b>شكراً لاستخدامك خدمتنا!</b>\n✨━━━━━━━━━━━━━✨", parse_mode=ParseMode.HTML)

        except:
            await status.edit_text("❌ <b>حدث خطأ! تأكد من أن الرابط عام وصحيح.</b>")

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🚀 FAST MEDIA IS LIVE AND READY!")
    app.run_polling(drop_pending_updates=True)

import os
import asyncio
import yt_dlp
from flask import Flask
from threading import Thread
from waitress import serve
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- 1. سرفر الويب (لضمان بقاء البوت حياً) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "⚡ FAST MEDIA Is Online!"

def run_flask():
    try: serve(app_web, host='0.0.0.0', port=8080)
    except: pass

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- 2. الإعدادات الأساسية ---
TOKEN = "8254937829:AAGgMOc0z68Rqm5MAoURNmZNslH60o2LDJw" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
BOT_NAME = "『 ＦＡＳＴ ＭＥＤＩＡ 』"
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net", "@Fast_Mediia"]
USERS_FILE = "users.txt"
COOKIES_FILE = "cookies.txt" # تأكد من وجود الملف بجانب الكود

# --- 3. وظائف الإدارة والبيانات ---
def get_users_list():
    if not os.path.exists(USERS_FILE): return []
    with open(USERS_FILE, "r") as f: return f.read().splitlines()

def add_user(user_id):
    users = get_users_list()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f: f.write(f"{user_id}\n")

async def is_subscribed(context, user_id):
    if user_id == ADMIN_ID: return True
    for chan in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=chan, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: continue
    return True

# --- 4. واجهة الترحيب ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    kb = [['🔄 بدء من جديد'], ['📢 القنوات']]
    if user.id == ADMIN_ID: kb.append(['📊 الإحصائيات', '📣 إذاعة'])
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

# --- 5. معالج الرسائل والتحميل ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔄 بدء من جديد': await start(update, context); return
    elif text == '👨‍💻 المطور': await update.message.reply_text(f"👑 <b>المطور المسؤول:</b> {DEV_USER}", parse_mode=ParseMode.HTML); return
    elif text == '📢 القنوات':
        links = "\n".join([f"🔗 {c}" for c in CHANNELS])
        await update.message.reply_text(f"📢 <b>قنوات الاشتراك الإجباري:</b>\n\n{links}", parse_mode=ParseMode.HTML); return

    # أزرار الإدارة
    if user_id == ADMIN_ID:
        if text == '📊 الإحصائيات':
            count = len(get_users_list())
            await update.message.reply_text(f"📊 <b>عدد المشتركين:</b> {count}"); return
        elif text == '📣 إذاعة':
            await update.message.reply_text("📥 أرسل الرسالة للإذاعة:"); context.user_data['broadcast'] = True; return
        elif context.user_data.get('broadcast'):
            for uid in get_users_list():
                try: await context.bot.copy_message(chat_id=uid, from_chat_id=user_id, message_id=update.message.message_id)
                except: pass
            await update.message.reply_text("✅ تمت الإذاعة بنجاح!"); context.user_data['broadcast'] = False; return

    # التحميل عند استلام رابط
    if "http" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("⚠️ <b>يجب الاشتراك في القنوات أولاً!</b>", parse_mode=ParseMode.HTML); return

        status = await update.message.reply_text("⌛", parse_mode=ParseMode.HTML)
        temp_file = f"video_{user_id}.mp4"
        
        ydl_opts = {
            'quiet': True,
            'format': 'best',
            'outtmpl': temp_file,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        # تفعيل الكوكيز إذا كان الملف موجوداً
        if os.path.exists(COOKIES_FILE):
            ydl_opts['cookiefile'] = COOKIES_FILE

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [text])
                
                if os.path.exists(temp_file):
                    # إرسال الفيديو
                    await context.bot.send_video(
                        chat_id=user_id, 
                        video=open(temp_file, 'rb'), 
                        caption=f"✅ <b>تم التحميل بنجاح!</b>\n✨ <b>بواسطة:</b> {BOT_NAME}", 
                        parse_mode=ParseMode.HTML
                    )
                    
                    # إرسال رسالة الشكر (بدون حذف الساعة الرملية)
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text="✨━━━━━━━━━━━━━✨\n🙏 <b>شكراً لاستخدامك خدمتنا!</b>\n✨━━━━━━━━━━━━━✨", 
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await status.edit_text("❌ لم يتم العثور على الفيديو.")
        except Exception as e:
            print(f"Error: {e}")
            await status.edit_text("❌ فشل التحميل. تأكد من الرابط أو الكوكيز.")
        finally:
            if os.path.exists(temp_file): os.remove(temp_file)

if __name__ == "__main__":
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🚀 FAST MEDIA IS LIVE AND READY!")
    app.run_polling(drop_pending_updates=True)

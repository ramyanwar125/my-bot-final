import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

# --- 1. الإعدادات والمعلومات ---
TOKEN = "8254937829:AAGgMOc0z68Rqm5MAoURNmZNslH60o2LDJw" 
ADMIN_ID = 7349033289 
DEV_USER = "@TOP_1UP"
BOT_NAME = "『 ＦＡＳＴ ＭＥＤＩＡ 』"

# القنوات المطلوبة للاشتراك الإجباري (تم تحديثها)
CHANNELS = ["@T_U_H1", "@T_U_H2", "@Mega0Net", "@Fast_Mediia"]
USERS_FILE = "users.txt"

# --- 2. إدارة قاعدة البيانات ---
def add_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f: pass
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

# --- 3. فحص الاشتراك الإجباري ---
async def is_subscribed(context, user_id):
    if user_id == ADMIN_ID: return True
    for chan in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=chan, user_id=user_id)
            if member.status in ['left', 'kicked']: return False
        except: return False
    return True

# --- 4. واجهة البداية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    context.user_data.clear() # تنظيف البيانات عند البدء
    
    kb = [['🔄 بدء من جديد', '📊 إحصائيات'], ['👨‍💻 المطور', '📢 القنوات']]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome_text = (
        f"👋 أهلاً بك يا {user.first_name}\n\n"
        f"⚡ <b>{BOT_NAME}</b>\n"
        "قم بإرسال رابط (تيك توك، إنستا، يوتيوب) وسأقوم بمعالجته فوراً.\n\n"
        "⚠️ تأكد من أن الحساب عام وليس خاص."
    )
    
    if update.callback_query:
        await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode=ParseMode.HTML)

# --- 5. وظيفة عداد النسبة المئوية ---
def progress_hook(d, context, chat_id, message_id, loop):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        s = d.get('_speed_str', '0KB/s')
        text = (f"⏳ <b>جاري التحميل... يرجى الانتظار</b> ⏳\n\n"
                f"<b>📊 التقدم:</b> <code>{p}</code>\n"
                f"<b>🚀 السرعة:</b> <code>{s}</code>")
        asyncio.run_coroutine_threadsafe(
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=ParseMode.HTML),
            loop
        )

# --- 6. معالج النصوص والأزرار الثابتة ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔄 بدء من جديد':
        await start(update, context); return
    elif text == '📊 إحصائيات':
        count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 <b>إحصائيات البوت:</b> <code>{count}</code>", parse_mode=ParseMode.HTML); return
    elif text == '👨‍💻 المطور':
        await update.message.reply_text(f"👑 <b>مطور البوت:</b> {DEV_USER}", parse_mode=ParseMode.HTML); return
    elif text == '📢 القنوات':
        links = "\n".join([f"🔗 {c}" for c in CHANNELS])
        await update.message.reply_text(f"📢 <b>قنواتنا الرسمية:</b>\n{links}", parse_mode=ParseMode.HTML); return

    if "http" in text:
        if not await is_subscribed(context, user_id):
            await update.message.reply_text("<b>⚠️ عذراً! يجب الاشتراك في القنوات أولاً لتتمكن من التحميل.</b>", parse_mode=ParseMode.HTML); return
        
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 فيديو (MP4)", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 صوت (Audio)", callback_data="dl_audio")]]
        await update.message.reply_text(f"📥 <b>{BOT_NAME}\nاختر الصيغة المطلوبة:</b>", reply_markup=InlineKeyboardMarkup(btns), parse_mode=ParseMode.HTML)

# --- 7. محرك التحميل ومعالجة الأزرار الشفافة ---
async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "restart_bot":
        await query.answer(); await start(update, context); return

    await query.answer()
    user_id = query.from_user.id
    url = context.user_data.get('url')
    
    if not url: return # حماية من التكرار

    action = query.data
    loop = asyncio.get_event_loop()
    status = await context.bot.send_message(user_id, "⌛ <b>جاري بدء المعالجة...</b>", parse_mode=ParseMode.HTML)

    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'outtmpl': f'file_{user_id}.%(ext)s',
        'format': 'best' if action == "dl_video" else 'bestaudio/best',
        'progress_hooks': [lambda d: progress_hook(d, context, user_id, status.message_id, loop)],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            file_path = ydl.prepare_filename(info)

        await status.edit_text("📤 <b>جاري الرفع الآن...</b>", parse_mode=ParseMode.HTML)
        caption_text = f"✨ <b>تم التحميل بواسطة:</b> {DEV_USER}"
        
        with open(file_path, 'rb') as f:
            if action == "dl_audio":
                await context.bot.send_audio(chat_id=user_id, audio=f, caption=caption_text, parse_mode=ParseMode.HTML)
            else:
                await context.bot.send_video(chat_id=user_id, video=f, caption=caption_text, parse_mode=ParseMode.HTML)
        
        await status.delete()
        context.user_data.clear() # تصفير البيانات بعد النجاح

        restart_btn = [[InlineKeyboardButton("🔄 بدء تحميل جديد", callback_data="restart_bot")]]
        await context.bot.send_message(
            chat_id=user_id, 
            text=(f"✨ <b>اكتملت العملية بنجاح!</b> ✨\n\n"
                  f"📦 <b>تم تسليم الملف بأعلى جودة متاحة.</b>\n"
                  f"🙏 <b>شكراً لاستخدامك {BOT_NAME}</b>\n\n"
                  f"💡 <i>يمكنك الآن إرسال رابط آخر مباشرة.</i>"), 
            reply_markup=InlineKeyboardMarkup(restart_btn),
            parse_mode=ParseMode.HTML
        )
        
        if os.path.exists(file_path): os.remove(file_path)

    except Exception:
        await status.edit_text("❌ <b>حدث خطأ!</b>\nتأكد من أن الرابط عام أو حاول مرة أخرى.", parse_mode=ParseMode.HTML)
        context.user_data.clear()

# --- 8. التشغيل ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(process_download))
    
    print(f"✅ {BOT_NAME} يعمل الآن بكفاءة.")
    app.run_polling(drop_pending_updates=True)
    user = update.effective_user
    add_user(user.id)
    
    # القائمة السفلية المحدثة
    reply_kb = [
        ['🔄 بدء من جديد', '❌ إلغاء'],
        ['📊 إحصائيات', '👨‍💻 المطور'],
        ['📢 القنوات']
    ]
    markup = ReplyKeyboardMarkup(reply_kb, resize_keyboard=True)
    
    # نص الترحيب (تم حذف اليوتيوب)
    welcome_text = (
        f"✨ أهلاً بك يا {user.first_name} في بوت التحميل الشامل!\n\n"
        "🚀 يمكنك من خلالي تحميل الفيديوهات من:\n"
        "• إنستجرام (Instagram)\n• فيسبوك (Facebook)\n• تيك توك ومواقع أخرى...\n\n"
        "📢 يرجى الاشتراك في القنوات أولاً لاستخدام البوت."
    )
    
    inline_kb = [
        [InlineKeyboardButton("قناة 1 📢", url="https://t.me/T_U_H1"),
         InlineKeyboardButton("قناة 2 📢", url="https://t.me/T_U_H2")],
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

    # معالجة الأزرار الجديدة
    if text == '🔄 بدء من جديد':
        await update.message.reply_text("🔄 تم تصفير الجلسة، أنا بانتظار رابط جديد للتحميل.")
        return
    elif text == '❌ إلغاء':
        await update.message.reply_text("🚫 تم إلغاء العملية الحالية بنجاح.")
        return
    elif text == '👨‍💻 المطور':
        await update.message.reply_text(f"👤 مطور البوت: {DEV_USER}")
        return
    elif text == '📊 إحصائيات' and user_id == ADMIN_ID:
        count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
        await update.message.reply_text(f"📊 عدد المستخدمين الحاليين: {count}")
        return

    # فحص الروابط (مع استبعاد يوتيوب برمجياً)
    if "http" in text:
        if "youtube.com" in text or "youtu.be" in text:
            await update.message.reply_text("❌ عذراً، تحميل فيديوهات يوتيوب غير مدعوم في هذه النسخة.")
            return

        if not await check_sub(context, user_id):
            await update.message.reply_text("❌ عذراً، يجب عليك الاشتراك في القنوات أولاً!")
            return

        msg = await update.message.reply_text("🔍 جاري معالجة الرابط، انتظر قليلاً...")
        try:
            path = f"video_{user_id}.mp4"
            # إعدادات التحميل (بدون كوكيز يوتيوب)
            ydl_opts = {
                'format': 'best',
                'outtmpl': path,
                'quiet': True,
                'nocheckcertificate': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [text])
                
            await update.message.reply_video(video=open(path, "rb"), caption="✅ تم التحميل بواسطة @TOP_1UP")
            os.remove(path); await msg.delete()
        except:
            await msg.edit_text("❌ حدث خطأ! الرابط قد يكون غير مدعوم أو خاص.")

# --- 6. معالجة الأزرار ---
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "check_sub":
        if await check_sub(context, q.from_user.id):
            await q.edit_message_text("✅ شكراً لك! تم تفعيل البوت. أرسل الآن رابط إنستا أو فيسبوك.")
        else:
            await q.answer("❌ لم تشترك في جميع القنوات بعد!", show_alert=True)

# --- 7. تشغيل السيرفر والبوت ---
def run_srv():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), type('S', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"OK"))})).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    print("🚀 البوت يعمل الآن (بدون يوتيوب)...")
    app.run_polling(drop_pending_updates=True)

import os
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
USERS_FILE = "users.txt"
BAN_FILE = "banned.txt"
DEV_USER = "@TOP_1UP"

# --- 2. إدارة البيانات ---
def get_list(file_path):
    if not os.path.exists(file_path): return []
    with open(file_path, "r") as f:
        return list(set(f.read().splitlines()))

def add_to_file(file_path, item_id):
    items = get_list(file_path)
    if str(item_id) not in items:
        with open(file_path, "a") as f:
            f.write(f"{item_id}\n")

# --- 3. معالجة الرسائل ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) in get_list(BAN_FILE): return
    
    text = update.message.text
    
    # أوامر القائمة الرئيسية
    if "المطور" in text:
        await update.message.reply_text(f"👤 المطور: {DEV_USER}\n🆔 الآيدي: `{ADMIN_ID}`\n\nشكراً لتواصلك! ❤️")
        return
    if "إحصائياتي" in text:
        await update.message.reply_text(f"📊 عدد المشتركين: {len(get_list(USERS_FILE))}\n✅ حالتك: مستخدم نشط.")
        return

    # تحليل الرابط (الجزء المحدث)
    if "http" in text:
        m = await update.message.reply_text("🔎 جاري تحليل الرابط بأحدث التقنيات...")
        
        # إعدادات قوية جداً لتجاوز الحظر والتحليل
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'extract_flat': False,
            'nocheckcertificate': True,
            'geo_bypass': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # محاولة جلب المعلومات
                info = ydl.extract_info(text, download=False)
                
                # إنشاء خيارات الجودة
                keyboard = [
                    [InlineKeyboardButton("720p (عالية)", callback_data=f"dl|720|{text}")],
                    [InlineKeyboardButton("480p (متوسطة)", callback_data=f"dl|480|{text}")],
                    [InlineKeyboardButton("MP3 (صوت فقط)", callback_data=f"dl|mp3|{text}")]
                ]
                await m.edit_text(f"🎬 تم التحليل: {info.get('title')[:30]}...\n\nاختر الجودة المطلوبة:", 
                                  reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"Extraction Error: {e}")
            btn_new = [[InlineKeyboardButton("🔄 محاولة برابط آخر", callback_data="new_proc")]]
            await m.edit_text("❌ عذراً، هذا الرابط محمي أو غير مدعوم حالياً.\nتأكد أن الفيديو عام (Public).", 
                              reply_markup=InlineKeyboardMarkup(btn_new))

# --- 4. معالج الأزرار (تكملة الكود السابق) ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == "new_proc":
        await q.message.reply_text("✨ أرسل رابطاً جديداً الآن:")
        await q.message.delete(); return

    # ... باقي منطق التحميل dl من الكود السابق ...
    # (تأكد من استخدام نفس متغيرات ydl_opts المحدثة هنا أيضاً عند التحميل الفعلي)

# --- 5. التشغيل ---
if __name__ == "__main__":
    # (كود تشغيل السيرفر والـ App كما في الرد السابق)
    pass

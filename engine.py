import yt_dlp
import os

def get_all_formats(url):
    """
    يقوم باستخراج الروابط والجودات المتاحة.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
    }
    
    formats_dict = {}
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # 1. إضافة خيار الصوت دائماً
            formats_dict["🎵 Audio | صوت"] = "bestaudio/best"
            
            # 2. استخراج جودات الفيديو المتاحة
            # نبحث عن الصيغ التي تحتوي على فيديو وصوت معاً أو أفضل فيديو
            all_formats = info.get('formats', [])
            
            # جودات محددة نريد عرضها للمستخدم
            target_res = [144, 240, 360, 480, 720, 1080]
            found_res = set()

            for f in all_formats:
                height = f.get('height')
                if height in target_res and height not in found_res:
                    # نختار format_id الذي يضمن أفضل جودة مع دمج الصوت
                    # 'bestvideo[height=720]+bestaudio' كمثال
                    fid = f"bestvideo[height={height}]+bestaudio/best[height={height}]/best"
                    formats_dict[f"🎬 {height}p"] = fid
                    found_res.add(height)
            
            # إذا لم يجد جودات محددة (مثل إنستغرام)، نضيق الخيار لأفضل فيديو
            if len(formats_dict) <= 1:
                formats_dict["🎬 Best Quality | أفضل جودة"] = "bestvideo+bestaudio/best"

            return formats_dict
            
        except Exception as e:
            print(f"Error in extraction: {e}")
            raise e

def run_download(url, format_id, output_path):
    """
    يقوم بتحميل الفيديو أو الصوت بناءً على الخيار المختار.
    """
    ydl_opts = {
        'format': format_id,
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        # تحسينات لضمان أفضل دمج وسرعة
        'merge_output_format': 'mp4', 
        'postprocessors': []
    }

    # إذا كان المطلوب صوتاً فقط، نقوم بتحويله لـ mp3 أو m4a
    if format_id == "bestaudio/best":
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


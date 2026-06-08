import os
from glob import glob

import yt_dlp
from django.conf import settings
import time

def cleanup_old_files():
    """Remove files from media directory that are older than 2 hours."""
    now = time.time()
    media_path = settings.MEDIA_ROOT
    if not os.path.exists(media_path):
        return
        
    for f in os.listdir(media_path):
        file_path = os.path.join(media_path, f)
        # Skip directories and files that aren't MP4 or JPG (to be safe)
        if os.path.isfile(file_path):
            # If item is older than 2 hours (7200 seconds)
            if os.stat(file_path).st_mtime < now - 7200:
                try:
                    os.remove(file_path)
                except:
                    pass

def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'skip_download': True,
            'js_runtimes': ['node'],
            'remote_components': ['ejs:github'],
        }

        cookies_file = os.getenv('YTDLP_COOKIES_FILE')
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        resolutions = sorted(
            {
                f"{f['height']}p"
                for f in info.get('formats', [])
                if f.get('height') and f.get('vcodec') != 'none'
            },
            key=lambda x: int(x[:-1]) if x[:-1].isdigit() else 0,
            reverse=True,
        )

        return {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'author': info.get('uploader') or info.get('channel'),
            'length': info.get('duration'),
            'resolutions': resolutions,
            'url': url
        }
    except Exception as e:
        print(f"Error getting info: {e}")
        return None

def download_and_merge(url, resolution='1080p'):
    try:
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        cleanup_old_files()

        height = int(resolution.rstrip('p')) if resolution.endswith('p') and resolution[:-1].isdigit() else 1080
        ffmpeg_bin = os.path.join(settings.BASE_DIR, 'bin', 'ffmpeg.exe')
        if not os.path.exists(ffmpeg_bin):
            ffmpeg_bin = 'ffmpeg'

        ydl_opts = {
            'format': f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(settings.MEDIA_ROOT, '%(title).50s_%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_bin,
            'quiet': True,
            'noplaylist': True,
            'js_runtimes': ['node'],
            'remote_components': ['ejs:github'],
        }

        cookies_file = os.getenv('YTDLP_COOKIES_FILE')
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        video_id = info.get('id')
        matches = sorted(glob(os.path.join(settings.MEDIA_ROOT, f'*_{video_id}.mp4')), key=os.path.getmtime, reverse=True)
        if not matches:
            return None

        output_path = matches[0]
        output_filename = os.path.basename(output_path)

        return {
            'filename': output_filename,
            'url': settings.MEDIA_URL + output_filename,
            'title': info.get('title')
        }
        
    except Exception as e:
        print(f"Error downloading: {e}")
        return None

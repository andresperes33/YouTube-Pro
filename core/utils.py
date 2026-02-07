import os
import subprocess
from pytubefix import YouTube
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
        yt = YouTube(url)
        streams = yt.streams.filter(progressive=False, file_extension='mp4')
        
        # Get available resolutions
        resolutions = sorted(list(set([s.resolution for s in streams if s.resolution])), key=lambda x: int(x[:-1]) if x[:-1].isdigit() else 0, reverse=True)
        
        return {
            'title': yt.title,
            'thumbnail': yt.thumbnail_url,
            'author': yt.author,
            'length': yt.length,
            'resolutions': resolutions,
            'url': url
        }
    except Exception as e:
        print(f"Error getting info: {e}")
        return None

def download_and_merge(url, resolution='1080p'):
    cleanup_old_files()
    try:
        yt = YouTube(url)
        
        # Filter video and audio
        video_stream = yt.streams.filter(res=resolution, file_extension="mp4", only_video=True).first()
        if not video_stream:
            # Fallback to highest available if requested not found
            video_stream = yt.streams.filter(file_extension="mp4", only_video=True).order_by('resolution').desc().first()
        
        # Filter audio streams and pick the best one (preferring Portuguese or native)
        audio_streams = yt.streams.filter(only_audio=True, file_extension="mp4")
        
        def audio_sort_key(s):
            lang = getattr(s, 'audio_track_language_id', None)
            # Score logic: 
            # 2: explicitly Portuguese
            # 1: None (usually the native/original track)
            # 0: other languages (like 'en')
            lang_score = 0
            if lang and (str(lang).lower().startswith('pt') or str(lang).lower().startswith('por')):
                lang_score = 2
            elif lang is None:
                lang_score = 1
            
            # Use ABR (Average Bitrate) as secondary sort key
            try:
                abr_val = int(s.abr.replace('kbps', ''))
            except:
                abr_val = 0
            
            return (lang_score, abr_val)
            
        audio_stream = sorted(audio_streams, key=audio_sort_key, reverse=True)[0] if audio_streams else None
        
        if not video_stream or not audio_stream:
            return None

        # Temp paths
        video_temp = os.path.join(settings.MEDIA_ROOT, "video_temp.mp4")
        audio_temp = os.path.join(settings.MEDIA_ROOT, "audio_temp.mp4")
        
        # Safe title
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        output_filename = f"{safe_title}_{video_stream.resolution}.mp4"
        output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

        # Download
        video_stream.download(output_path=settings.MEDIA_ROOT, filename="video_temp.mp4")
        audio_stream.download(output_path=settings.MEDIA_ROOT, filename="audio_temp.mp4")
        
        # Path to local FFmpeg
        # On Windows it's ffmpeg.exe, on Linux it's usually just ffmpeg
        ffmpeg_bin = os.path.join(settings.BASE_DIR, 'bin', 'ffmpeg.exe')
        
        # If it doesn't exist (e.g. on Linux server), fallback to global 'ffmpeg'
        if not os.path.exists(ffmpeg_bin):
            ffmpeg_bin = 'ffmpeg'

        # Merge using FFmpeg
        subprocess.run([
            ffmpeg_bin, "-i", video_temp, "-i", audio_temp,
            "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", "-y", output_path
        ], capture_output=True, text=True, check=True)
        
        # Cleanup
        if os.path.exists(video_temp): os.remove(video_temp)
        if os.path.exists(audio_temp): os.remove(audio_temp)
        
        return {
            'filename': output_filename,
            'url': settings.MEDIA_URL + output_filename,
            'title': yt.title
        }
        
    except Exception as e:
        print(f"Error downloading: {e}")
        return None

from django.shortcuts import render
from django.http import JsonResponse
from .utils import get_video_info, download_and_merge
import json

def index(request):
    return render(request, 'core/index.html')

def download_video_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        url = data.get('url', '').strip()
        action = data.get('action') # 'info' or 'download'
        resolution = data.get('resolution', '1080p')

        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)

        if action == 'info':
            info = get_video_info(url)
            if info:
                return JsonResponse(info)
            else:
                return JsonResponse({
                    'error': '❌ Não foi possível obter informações do vídeo. Verifique se o link está correto e se o vídeo é público.'
                }, status=400)
        
        elif action == 'download':
            result = download_and_merge(url, resolution)
            if result:
                return JsonResponse(result)
            else:
                return JsonResponse({
                    'error': '❌ Falha no download. Verifique sua conexão e tente novamente.'
                }, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

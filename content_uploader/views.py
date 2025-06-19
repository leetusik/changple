from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from .models import NotionContent
import os

# Create your views here.
def view_html_content(request, content_id):
    """
    NotionContent 객체에 연결된 HTML 파일을 읽어 웹에 표시합니다.
    """
    content = get_object_or_404(NotionContent, pk=content_id)
    
    # html_path가 비어있는 경우 처리
    if not content.html_path:
        return HttpResponse("HTML 파일 경로가 설정되지 않았습니다.", status=404)

    file_path = os.path.join(settings.MEDIA_ROOT, content.html_path)

    if not os.path.exists(file_path):
        return HttpResponse("파일을 찾을 수 없습니다.", status=404)

    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    return HttpResponse(html_content)

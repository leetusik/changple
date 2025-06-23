from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from .models import NotionContent
import os
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.urls import reverse
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

# Create your views here.
@xframe_options_exempt
def view_html_content(request, content_id):
    """
    NotionContent 객체에 연결된 HTML 파일을 읽어 파싱하고,
    이미지 경로를 절대 경로로 수정한 후 웹에 표시합니다.
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

    soup = BeautifulSoup(html_content, 'html.parser')
    html_dir = os.path.dirname(content.html_path)

    for img in soup.find_all('img'):
        src = img.get('src')
        if src and not src.startswith(('http://', 'https://', '/')):
            # URL 디코딩 후 파일 시스템 경로에 맞게 조합
            decoded_src = unquote(src)
            # os.path.join이 슬래시로 시작하는 경로를 올바르게 처리하지 못할 수 있으므로, lstrip으로 제거
            image_path_in_media = os.path.join(html_dir, decoded_src.lstrip('/'))
            
            # 웹 URL로 사용하기 위해 다시 인코딩 (슬래시는 인코딩하지 않음)
            img['src'] = quote(f'{settings.MEDIA_URL}{image_path_in_media}', safe=':/')

    return HttpResponse(str(soup))

def notion_content_list(request):
    page = request.GET.get('page', 1)
    content_list = NotionContent.objects.order_by('-updated_at')
    paginator = Paginator(content_list, 20)  # Show 20 contacts per page.

    page_obj = paginator.get_page(page)
    
    data = {
        'contents': [],
        'has_next': page_obj.has_next(),
    }

    for content in page_obj.object_list:
        item = {
            'id': content.id,
            'title': content.title,
            'thumbnail_url': content.thumbnail_img_path.url if content.thumbnail_img_path else '',
            'view_url': reverse('content_uploader:view_html_content', args=[content.id]),
        }
        data['contents'].append(item)

    return JsonResponse(data)

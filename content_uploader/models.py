from django.db import models
import os
import zipfile
from django.conf import settings
from bs4 import BeautifulSoup
from urllib.parse import unquote
import shutil

# Create your models here.

class NotionContent(models.Model):
    title = models.CharField(max_length=200, help_text="웹페이지에 표시될 제목을 입력하세요.")
    description = models.TextField(blank=True, help_text="웹페이지에 표시될 짧은 설명을 입력하세요. (비워둘 경우, 본문 앞부분 일부가 표시됩니다.)")
    thumbnail_img_path = models.ImageField(upload_to='', blank=True, null=True, help_text="썸네일 이미지를 업로드하세요. (비워둘 경우, 본문 가장 첫 이미지가 썸네일이 됩니다.)")
    zip_file = models.FileField(upload_to='', blank=True, null=True, help_text="노션에서 HTML 형식으로 내보내기 하고, ZIP 파일 형태 그대로 업로드하세요.")
    html_path = models.CharField(max_length=255, blank=True, editable=False)
    contents_img_path = models.CharField(max_length=255, blank=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # 1. 객체 업데이트 시, 기존 썸네일 파일 교체를 대비해 삭제 처리
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if old_instance.thumbnail_img_path and self.thumbnail_img_path != old_instance.thumbnail_img_path:
                    old_instance.thumbnail_img_path.delete(save=False)
            except self.__class__.DoesNotExist:
                pass

        # 2. 부모 save()를 호출하여 ID를 받고, 파일들을 임시 경로에 저장
        super().save(*args, **kwargs)

        # 3. ZIP 파일 관련 로직을 먼저 처리
        if self.zip_file:
            unzip_dir = os.path.join(settings.MEDIA_ROOT, 'html_content', str(self.id))
            
            if os.path.isdir(unzip_dir):
                shutil.rmtree(unzip_dir)
            os.makedirs(unzip_dir, exist_ok=True)

            with zipfile.ZipFile(self.zip_file.path, 'r') as zip_ref:
                zip_ref.extractall(unzip_dir)

            html_file_path = None
            for root, _, files in os.walk(unzip_dir):
                for file in files:
                    if file.endswith('.html'):
                        html_file_path = os.path.join(root, file)
                        self._rewrite_image_paths(html_file_path)
                        relative_path = os.path.relpath(html_file_path, settings.MEDIA_ROOT)
                        self.html_path = relative_path.replace(os.path.sep, '/')

                        # HTML 파일명과 동일한 이름의 이미지 폴더 경로를 찾아 저장
                        html_file_name_root = os.path.splitext(os.path.basename(html_file_path))[0]
                        found_img_dir = False
                        for r, dirs, _ in os.walk(unzip_dir):
                            for d in dirs:
                                if d == html_file_name_root:
                                    img_dir_path_abs = os.path.join(r, d)
                                    relative_img_dir_path = os.path.relpath(img_dir_path_abs, settings.MEDIA_ROOT)
                                    self.contents_img_path = relative_img_dir_path.replace(os.path.sep, '/')
                                    found_img_dir = True
                                    break
                            if found_img_dir:
                                break
                        break
                if html_file_path:
                    break
            
            if self.zip_file and os.path.exists(self.zip_file.path):
                self.zip_file.delete(save=False)
            self.zip_file = None
            super().save(update_fields=['html_path', 'zip_file', 'contents_img_path'])

        # 4. 썸네일 파일을 최종 목적지로 이동 (ZIP 처리가 끝난 후)
        if self.thumbnail_img_path and not self.thumbnail_img_path.name.startswith('thumbnail_img/'):
            old_path = self.thumbnail_img_path.path
            new_name = f'thumbnail_img/{self.id}/{os.path.basename(self.thumbnail_img_path.name)}'
            new_path = os.path.join(settings.MEDIA_ROOT, new_name)

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(old_path, new_path)
            
            self.thumbnail_img_path.name = new_name
            super().save(update_fields=['thumbnail_img_path'])

    def _rewrite_image_paths(self, html_file_path):
        """HTML 파일 내의 상대 이미지 경로를 올바른 절대 미디어 경로로 변경합니다."""
        html_dir = os.path.dirname(html_file_path)
        
        with open(html_file_path, 'r+', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            
            # img 태그뿐만 아니라 a 태그의 href도 이미지일 수 있으므로 함께 처리
            for tag in soup.find_all(['img', 'a']):
                attr = 'src' if tag.name == 'img' else 'href'
                original_path = tag.get(attr)

                if not original_path or original_path.startswith(('http', '/', '#', 'data:')):
                    continue

                # URL 인코딩된 경로를 디코딩 (예: %20 -> ' ')
                decoded_path = unquote(original_path)

                # HTML 파일 위치를 기준으로 상대 경로의 절대 파일 시스템 경로 계산
                # os.path.normpath를 사용하여 ../ 같은 경로를 단순화
                abs_fs_path = os.path.normpath(os.path.join(html_dir, decoded_path))

                # MEDIA_ROOT를 기준으로 다시 상대적인 URL 경로 생성
                if os.path.exists(abs_fs_path):
                    relative_url_path = os.path.relpath(abs_fs_path, settings.MEDIA_ROOT)
                    # Windows 경로(\)를 URL 경로(/)로 변경
                    final_url = os.path.join(settings.MEDIA_URL, relative_url_path).replace('\\', '/')
                    tag[attr] = final_url

            f.seek(0)
            f.write(str(soup))
            f.truncate()

    def get_html_url(self):
        """사용자가 접근할 최종 HTML URL을 반환합니다."""
        if self.html_path:
            return f"{settings.MEDIA_URL}{self.html_path}"
        return None

    def delete(self, *args, **kwargs):
        # 객체와 연결된 html_content/<id> 디렉토리 경로를 확인
        content_dir = os.path.join(settings.MEDIA_ROOT, 'html_content', str(self.id))
        
        # 디렉토리가 존재하면 재귀적으로 삭제
        if os.path.isdir(content_dir):
            shutil.rmtree(content_dir)
            
        # 썸네일 이미지 디렉토리도 확인 후 삭제
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnail_img', str(self.id))
        if os.path.isdir(thumbnail_dir):
            shutil.rmtree(thumbnail_dir)

        # 부모 클래스의 delete 메소드를 호출하여 DB에서 객체 삭제
        super().delete(*args, **kwargs)

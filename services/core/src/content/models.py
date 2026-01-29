"""
Content models for Changple Core service.
"""

import hashlib
import os
import shutil
import zipfile

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import models
from urllib.parse import unquote

from src.content.utils import convert_images_in_directory


class NotionContent(models.Model):
    """
    Notion에서 'HTML로 내보내기' 기능을 통해 생성된 .zip 파일을 업로드하여
    웹 콘텐츠를 생성하고 관리하는 모델입니다.
    """

    title = models.CharField(
        max_length=200,
        verbose_name="제목",
        help_text="웹페이지에 표시될 제목을 입력하세요.",
    )
    description = models.TextField(
        blank=True,
        verbose_name="설명",
        help_text="웹페이지에 표시될 짧은 설명을 입력하세요. (2 ~ 4 문장 정도)",
    )
    thumbnail_img_path = models.ImageField(
        upload_to="",
        blank=True,
        null=True,
        verbose_name="썸네일 이미지",
        help_text="썸네일 이미지를 업로드하세요.",
    )
    zip_file = models.FileField(
        upload_to="",
        blank=True,
        null=True,
        verbose_name=".zip 파일",
        help_text="노션에서 HTML 형식으로 내보내기 한 뒤, 얻어지는 .zip 파일을 그대로 업로드하세요.",
    )
    is_preferred = models.BooleanField(
        default=False,
        verbose_name="인기 칼럼",
        help_text="체크시 컨텐츠 목록에서 [인기칼럼] 섹션에 상위 노출됩니다.",
    )

    # Auto-populated fields
    html_path = models.CharField(
        max_length=255,
        blank=True,
        editable=False,
        help_text="처리된 HTML 파일의 상대 경로입니다.",
    )
    contents_img_path = models.CharField(
        max_length=255,
        blank=True,
        editable=False,
        help_text="콘텐츠에 포함된 이미지들이 저장된 디렉토리의 상대 경로입니다.",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "창플 컨텐츠 관리"
        verbose_name_plural = "창플 컨텐츠 관리"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save to process uploaded zip files."""
        # Handle thumbnail replacement
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                if (
                    old_instance.thumbnail_img_path
                    and self.thumbnail_img_path != old_instance.thumbnail_img_path
                ):
                    old_instance.thumbnail_img_path.delete(save=False)
            except self.__class__.DoesNotExist:
                pass

        # First save to get an ID
        super().save(*args, **kwargs)

        # Process ZIP file
        if self.zip_file:
            unzip_dir = os.path.join(
                settings.MEDIA_ROOT, "html_content", str(self.id)
            )

            # Clean existing directory
            if os.path.isdir(unzip_dir):
                shutil.rmtree(unzip_dir)
            os.makedirs(unzip_dir, exist_ok=True)

            # Extract zip file
            with zipfile.ZipFile(self.zip_file.path, "r") as zip_ref:
                filename_mapping = self._safe_extract_zip(zip_ref, unzip_dir)

            html_file_path = None
            # Find and process HTML file
            for root, _, files in os.walk(unzip_dir):
                for file in files:
                    if file.endswith(".html"):
                        html_file_path = os.path.join(root, file)
                        self._rewrite_image_paths(html_file_path, filename_mapping)
                        self._add_custom_styles(html_file_path)

                        relative_path = os.path.relpath(
                            html_file_path, settings.MEDIA_ROOT
                        )
                        self.html_path = relative_path.replace(os.path.sep, "/")

                        # Find corresponding image directory
                        html_file_name_root = os.path.splitext(
                            os.path.basename(html_file_path)
                        )[0]
                        for r, dirs, _ in os.walk(unzip_dir):
                            for d in dirs:
                                if d == html_file_name_root:
                                    img_dir_path_abs = os.path.join(r, d)
                                    relative_img_dir_path = os.path.relpath(
                                        img_dir_path_abs, settings.MEDIA_ROOT
                                    )
                                    self.contents_img_path = (
                                        relative_img_dir_path.replace(os.path.sep, "/")
                                    )
                                    break
                        break
                if html_file_path:
                    break

            # Delete original zip file
            if self.zip_file and os.path.exists(self.zip_file.path):
                self.zip_file.delete(save=False)

            self.zip_file = None
            super().save(update_fields=["html_path", "zip_file", "contents_img_path"])

        # Move thumbnail to final location
        if self.thumbnail_img_path and not self.thumbnail_img_path.name.startswith(
            "thumbnail_img/"
        ):
            old_path = self.thumbnail_img_path.path
            new_name = f"thumbnail_img/{self.id}/{os.path.basename(self.thumbnail_img_path.name)}"
            new_path = os.path.join(settings.MEDIA_ROOT, new_name)

            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            shutil.move(old_path, new_path)

            self.thumbnail_img_path.name = new_name
            super().save(update_fields=["thumbnail_img_path"])

    def _add_custom_styles(self, html_file_path: str):
        """Add custom styles and scripts to HTML file."""
        with open(html_file_path, "r+", encoding="utf-8") as f:
            content = f.read()
            style = """
            <style>
                body::-webkit-scrollbar { display: none; }
                html { scrollbar-width: none; }
            </style>
            """
            scroll_script = """
            <script>
                window.addEventListener('scroll', function() {
                    if (document.documentElement.scrollHeight - window.innerHeight - 200 <= window.scrollY) {
                        window.parent.postMessage('iframeScrollEnd', '*');
                    }
                });
            </script>
            """
            modified_content = content.replace(
                "</head>", f"{style}{scroll_script}</head>"
            )

            # Replace incompatible image extensions
            for ext in [".heic", ".HEIC", ".heif", ".HEIF", ".webp", ".WEBP", ".avif", ".AVIF"]:
                modified_content = modified_content.replace(ext, ".jpg")

            f.seek(0)
            f.write(modified_content)
            f.truncate()

    def _rewrite_image_paths(self, html_file_path: str, filename_mapping: dict = None):
        """Rewrite image paths in HTML file to web-accessible URLs."""
        html_dir = os.path.dirname(html_file_path)

        with open(html_file_path, "r+", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

            for tag in soup.find_all(["img", "a"]):
                attr = "src" if tag.name == "img" else "href"
                original_path = tag.get(attr)

                if not original_path or original_path.startswith(
                    ("http", "/", "#", "data:")
                ):
                    continue

                decoded_path = unquote(original_path)

                # Apply filename mapping if available
                if filename_mapping:
                    for orig, new in filename_mapping.items():
                        if decoded_path == orig or decoded_path == unquote(orig):
                            decoded_path = new
                            break

                # Determine absolute filesystem path
                is_mapped = filename_mapping and decoded_path in filename_mapping.values()
                if is_mapped:
                    abs_fs_path = os.path.normpath(
                        os.path.join(
                            settings.MEDIA_ROOT,
                            "html_content",
                            str(self.id),
                            decoded_path,
                        )
                    )
                else:
                    abs_fs_path = os.path.normpath(
                        os.path.join(html_dir, decoded_path)
                    )

                # Convert to web URL
                if os.path.exists(abs_fs_path) or is_mapped:
                    relative_url_path = os.path.relpath(
                        abs_fs_path, settings.MEDIA_ROOT
                    )
                    final_url = os.path.join(
                        settings.MEDIA_URL, relative_url_path
                    ).replace("\\", "/")
                    tag[attr] = final_url

            f.seek(0)
            f.write(str(soup))
            f.truncate()

    def _safe_extract_zip(self, zip_ref, extract_dir: str) -> dict:
        """Safely extract zip file, shortening long filenames."""
        filename_mapping = {}

        for member in zip_ref.infolist():
            target_path = os.path.join(extract_dir, member.filename)

            # Shorten long paths
            if len(target_path) > 100:
                filename = os.path.basename(member.filename)
                dirname = os.path.dirname(member.filename)
                _, ext = os.path.splitext(filename)

                hash_name = hashlib.md5(filename.encode("utf-8")).hexdigest()[:16]
                new_filename = f"{hash_name}{ext}"

                if dirname:
                    dir_parts = dirname.split("/")
                    short_dir_parts = []
                    for part in dir_parts:
                        if len(part) > 50:
                            part_hash = hashlib.md5(
                                part.encode("utf-8")
                            ).hexdigest()[:12]
                            short_dir_parts.append(part_hash)
                        else:
                            short_dir_parts.append(part)
                    new_dirname = "/".join(short_dir_parts)
                    new_member_filename = f"{new_dirname}/{new_filename}"
                else:
                    new_member_filename = new_filename

                target_path = os.path.join(extract_dir, new_member_filename)
                filename_mapping[member.filename] = new_member_filename

            # Create directory and extract file
            target_dir = os.path.dirname(target_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)

            if not member.is_dir():
                try:
                    with zip_ref.open(member) as source, open(
                        target_path, "wb"
                    ) as target:
                        shutil.copyfileobj(source, target)
                except Exception as e:
                    print(f"파일 추출 실패: {member.filename} -> {e}")

        # Handle nested zip files
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.endswith(".zip"):
                    inner_zip_path = os.path.join(root, file)
                    try:
                        with zipfile.ZipFile(inner_zip_path, "r") as inner_zip:
                            inner_mapping = self._safe_extract_zip(
                                inner_zip, extract_dir
                            )
                            filename_mapping.update(inner_mapping)
                        os.remove(inner_zip_path)
                    except Exception as e:
                        print(f"내부 zip 압축 해제 실패: {file} -> {e}")

        # Convert images
        convert_images_in_directory(extract_dir, quality=85, max_width=2048)

        return filename_mapping

    def get_html_url(self) -> str | None:
        """Return the web URL for the HTML content."""
        if self.html_path:
            return f"{settings.MEDIA_URL}{self.html_path}"
        return None

    def delete(self, *args, **kwargs):
        """Delete associated files when deleting the model."""
        # Delete content directory
        content_dir = os.path.join(settings.MEDIA_ROOT, "html_content", str(self.id))
        if os.path.isdir(content_dir):
            shutil.rmtree(content_dir)

        # Delete thumbnail directory
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, "thumbnail_img", str(self.id))
        if os.path.isdir(thumbnail_dir):
            shutil.rmtree(thumbnail_dir)

        super().delete(*args, **kwargs)


class ContentViewHistory(models.Model):
    """
    사용자가 NotionContent를 조회한 이력을 기록하는 모델입니다.
    """

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="content_views",
        help_text="콘텐츠를 조회한 사용자",
    )
    content = models.ForeignKey(
        NotionContent,
        on_delete=models.CASCADE,
        related_name="view_history",
        help_text="조회된 콘텐츠",
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="조회한 시간",
    )

    class Meta:
        ordering = ["-viewed_at"]
        verbose_name = "콘텐츠 조회 이력"
        verbose_name_plural = "콘텐츠 조회 이력"
        indexes = [
            models.Index(fields=["user", "-viewed_at"]),
            models.Index(fields=["content", "-viewed_at"]),
        ]

    def __str__(self):
        return (
            f"{self.user}이(가) {self.content.title}을(를) "
            f"{self.viewed_at.strftime('%Y-%m-%d %H:%M')}에 조회"
        )

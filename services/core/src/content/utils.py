"""
Content utility functions for Changple Core service.
"""

import logging
import os
import re

import html2text
from PIL import Image

# HEIC support
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC_SUPPORT_AVAILABLE = True
except ImportError:
    HEIC_SUPPORT_AVAILABLE = False
    logging.warning("pillow-heif not installed. HEIC conversion will be skipped.")

logger = logging.getLogger(__name__)

# Image formats that need conversion
CONVERT_EXTENSIONS = {".heic", ".heif", ".webp", ".avif"}


def extract_meaningful_text_from_html(html_content: str) -> str:
    """
    Extract meaningful text from HTML content for LLM processing.

    Uses html2text to convert HTML to markdown format.
    """
    if not html_content:
        return ""

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0
    h.unicode_snob = True
    h.escape_snob = True

    markdown_text = h.handle(html_content)
    markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text)
    markdown_text = markdown_text.strip()

    return markdown_text


def extract_text_from_notion_content(content_id: int) -> str:
    """
    Extract text from a NotionContent's HTML file.

    Args:
        content_id: NotionContent model ID

    Returns:
        Extracted text or empty string
    """
    from django.conf import settings

    from src.content.models import NotionContent

    content = NotionContent.objects.get(pk=content_id)

    if not content.html_path:
        return ""

    file_path = os.path.join(settings.MEDIA_ROOT, content.html_path)

    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return extract_meaningful_text_from_html(html_content)


def should_convert_image(file_path: str) -> bool:
    """Check if file needs image conversion."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in CONVERT_EXTENSIONS


def get_converted_filename(original_path: str, target_format: str = "jpeg") -> str:
    """Generate converted filename."""
    name_without_ext = os.path.splitext(original_path)[0]
    ext = ".jpg" if target_format.lower() == "jpeg" else f".{target_format.lower()}"
    return f"{name_without_ext}{ext}"


def convert_image_to_jpeg(
    input_path: str,
    output_path: str | None = None,
    quality: int = 85,
    max_width: int | None = None,
) -> tuple[bool, str]:
    """
    Convert an image file to JPEG format.

    Args:
        input_path: Path to the source image
        output_path: Path for the converted image (auto-generated if None)
        quality: JPEG quality (1-100)
        max_width: Maximum width in pixels (None for original size)

    Returns:
        Tuple of (success, converted_path or error_message)
    """
    if not os.path.exists(input_path):
        return False, f"입력 파일을 찾을 수 없습니다: {input_path}"

    ext = os.path.splitext(input_path)[1].lower()
    if ext in {".heic", ".heif"} and not HEIC_SUPPORT_AVAILABLE:
        return False, "HEIC 지원이 설치되지 않았습니다. pillow-heif를 설치해주세요."

    if output_path is None:
        output_path = get_converted_filename(input_path, "jpeg")

    try:
        with Image.open(input_path) as img:
            # Convert to RGB
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if needed
            if max_width and img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"이미지 크기 조정: {input_path} -> {max_width}x{new_height}")

            img.save(output_path, "JPEG", quality=quality, optimize=True)

        logger.info(f"이미지 변환 완료: {input_path} -> {output_path}")
        return True, output_path

    except Exception as e:
        error_msg = f"이미지 변환 실패: {input_path} -> {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def convert_images_in_directory(
    directory_path: str,
    quality: int = 85,
    max_width: int | None = None,
) -> dict:
    """
    Convert all HEIC/HEIF images in a directory to JPEG.

    Args:
        directory_path: Directory containing images
        quality: JPEG quality (1-100)
        max_width: Maximum width in pixels

    Returns:
        Dict with success, failed, and mapping keys
    """
    if not os.path.exists(directory_path):
        return {"success": [], "failed": [], "mapping": {}}

    results = {
        "success": [],
        "failed": [],
        "mapping": {},
    }

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)

            if should_convert_image(file_path):
                converted_path = get_converted_filename(file_path, "jpeg")

                success, result = convert_image_to_jpeg(
                    file_path, converted_path, quality, max_width
                )

                if success:
                    results["success"].append(file_path)
                    results["mapping"][file_path] = converted_path

                    # Delete original file
                    try:
                        os.remove(file_path)
                        logger.info(f"원본 파일 삭제: {file_path}")
                    except OSError as e:
                        logger.warning(f"원본 파일 삭제 실패: {file_path} -> {e}")
                else:
                    results["failed"].append({"file": file_path, "error": result})
            else:
                results["mapping"][file_path] = file_path

    return results

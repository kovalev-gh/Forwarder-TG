import os
import imghdr
from dataclasses import dataclass
from PIL import Image
from telethon.tl.types import DocumentAttributeVideo


from config.settings import DOWNLOAD_DIR


# ============================================================
# DATA STRUCTURE
# ============================================================

@dataclass
class PreparedMedia:
    path: str
    original_name: str


# ============================================================
# HELPERS
# ============================================================

def generate_unique_path(base_name: str, ext: str) -> str:
    """
    Генерирует уникальный путь:
    file.jpg, file(1).jpg, file(2).jpg
    """
    counter = 0
    while True:
        suffix = f"({counter})" if counter > 0 else ""
        filename = f"{base_name}{suffix}{ext}"
        path = os.path.join(DOWNLOAD_DIR, filename)
        if not os.path.exists(path):
            return path
        counter += 1


def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print("⚠ cleanup error:", e)


# ============================================================
# IMAGE
# ============================================================

def prepare_image_file(path: str, original_name: str) -> PreparedMedia:
    """
    Приводит изображение к JPEG и сохраняет
    без .jpg.jpg
    """

    base_name, _ = os.path.splitext(original_name)

    final_path = generate_unique_path(base_name, ".jpg")

    try:
        img = Image.open(path)
        img.convert("RGB").save(final_path, "JPEG", quality=95)
    except Exception as e:
        print("⚠ image convert error:", e)
        final_path = path

    return PreparedMedia(
        path=final_path,
        original_name=original_name
    )


# ============================================================
# GENERIC
# ============================================================

def prepare_generic_file(path: str, original_name: str) -> PreparedMedia:
    """
    Для видео, документов, голосовых
    """

    base_name, ext = os.path.splitext(original_name)
    if not ext:
        ext = ""

    final_path = generate_unique_path(base_name, ext)

    if path != final_path:
        os.rename(path, final_path)

    return PreparedMedia(
        path=final_path,
        original_name=original_name
    )
# ============================================================
# SPOILER / MEDIA HELPERS (для закрытых каналов)
# ============================================================

def is_media_spoiler(msg) -> bool:
    """
    Корректная проверка spoiler для закрытых каналов.
    Работает надёжнее, чем msg.media.spoiler
    """
    try:
        return bool(msg.media and getattr(msg.media, "spoiler", False))
    except Exception:
        return False


def is_video_note(msg) -> bool:
    """
    Определение video note (кружок)
    """
    try:
        if not msg.media or not getattr(msg.media, "document", None):
            return False

        if getattr(msg.media, "round", False):
            return True

        for attr in msg.media.document.attributes:
            if isinstance(attr, DocumentAttributeVideo) and getattr(attr, "round_message", False):
                return True
    except Exception:
        pass

    return False
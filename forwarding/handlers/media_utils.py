from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaPoll,
    MessageMediaPaidMedia,
    MessageMediaWebPage,
    DocumentAttributeAudio,
    DocumentAttributeSticker,
    DocumentAttributeVideo,
)


# ============================================================
# BASIC DETECTORS (legacy, used by handlers)
# ============================================================

def is_photo(msg) -> bool:
    return isinstance(getattr(msg, "media", None), MessageMediaPhoto)


def is_document(msg) -> bool:
    return isinstance(getattr(msg, "media", None), MessageMediaDocument)


def is_poll(msg) -> bool:
    return isinstance(getattr(msg, "media", None), MessageMediaPoll)


def is_paid(msg) -> bool:
    return isinstance(getattr(msg, "media", None), MessageMediaPaidMedia)


def is_web_preview(msg) -> bool:
    """
    Link preview (Instagram, YouTube, Twitter, etc).

    Это НЕ фото и НЕ видео.
    Telegram генерирует preview автоматически из текста.
    """
    return isinstance(getattr(msg, "media", None), MessageMediaWebPage)


# ============================================================
# STICKER
# ============================================================

def is_sticker(msg) -> bool:
    media = getattr(msg, "media", None)
    if not isinstance(media, MessageMediaDocument) or not getattr(media, "document", None):
        return False

    return any(
        isinstance(a, DocumentAttributeSticker)
        for a in media.document.attributes
    )


# ============================================================
# VOICE
# ============================================================

def is_voice(msg) -> tuple[bool, int]:
    """
    Возвращает (is_voice, duration)
    """
    media = getattr(msg, "media", None)
    if not isinstance(media, MessageMediaDocument) or not getattr(media, "document", None):
        return False, 0

    for attr in media.document.attributes:
        if isinstance(attr, DocumentAttributeAudio) and getattr(attr, "voice", False):
            return True, getattr(attr, "duration", 0)

    return False, 0


# ============================================================
# VIDEO (КАНОНИЧЕСКИЙ СПОСОБ)
# ============================================================

def is_video(msg) -> bool:
    """
    Корректное определение видео:

    ✔ MessageMediaDocument
    ✔ наличие DocumentAttributeVideo
    ✖ НИКАКИХ проверок расширений
    """

    media = getattr(msg, "media", None)
    if not isinstance(media, MessageMediaDocument):
        return False

    doc = media.document
    if not doc:
        return False

    return any(
        isinstance(a, DocumentAttributeVideo)
        for a in doc.attributes
    )


# ============================================================
# CANONICAL MEDIA KIND (SOURCE OF TRUTH)
# ============================================================

def detect_media_kind(msg) -> str:
    """
    ЕДИНСТВЕННЫЙ ИСТОЧНИК ИСТИНЫ ДЛЯ ТИПА МЕДИА.

    Возвращает:
      - TEXT
      - PHOTO
      - VIDEO
      - DOCUMENT
      - WEB
      - OTHER

    Используется:
      - album_forwarder
      - debug
      - future extensions
    """

    media = getattr(msg, "media", None)

    if media is None:
        return "TEXT"

    if isinstance(media, MessageMediaWebPage):
        return "WEB"

    if isinstance(media, MessageMediaPhoto):
        return "PHOTO"

    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc and any(isinstance(a, DocumentAttributeVideo) for a in doc.attributes):
            return "VIDEO"
        return "DOCUMENT"

    return "OTHER"


# ============================================================
# FILE HELPERS (names only)
# ============================================================

def guess_filename(msg, fallback_ext: str = ".bin") -> str:
    """
    Возвращает реальное имя файла из Telegram.
    Если имени нет — безопасный fallback по id.
    """
    if getattr(msg, "file", None) and getattr(msg.file, "name", None):
        return msg.file.name

    return f"{msg.id}{fallback_ext}"

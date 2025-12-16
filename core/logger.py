import logging
import sys

LOG_TO_FILE = False
LOG_FILE = "forwarder.log"

ICONS = {
    "PHOTO": "📸",
    "VIDEO": "🎬",
    "VOICE": "🎤",
    "FILE": "📄",
    "ALBUM": "📚",
    "STICKER": "🔖",
    "PAID": "💰",
    "POLL": "📊",
    "TEXT": "💬",
    "OTHER": "ℹ️"
}


def setup_logger():
    logger = logging.getLogger("tg_forwarder")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if LOG_TO_FILE:
        file = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file.setFormatter(formatter)
        logger.addHandler(file)

    return logger


logger = setup_logger()


def tag(kind: str, ident: int) -> str:
    """
    Формирует выровненный лог-префикс.

    ПРАВИЛА (пока ident < 1000):
    - одиночные сообщения:
        ICON + KIND(7) + ' #' + ID(3)
    - альбомы:
        ICON + KIND(5) + ' #' + ID(3)
        (# на 2 пробела левее)
    """

    icon = ICONS.get(kind, "•")

    if kind == "ALBUM":
        # ALBUM короче → # на 2 пробела левее
        return f"{icon} {kind:<5} #{ident:<3}"
    else:
        return f"{icon} {kind:<7} #{ident:<3}"


def log_done(kind: str, ident: int, action: str, extra: str = ""):
    """
    Унифицированный финальный лог.
    """
    msg = f"{tag(kind, ident)} │ {action}"
    if extra:
        msg += f" ({extra})"
    logger.info(msg)

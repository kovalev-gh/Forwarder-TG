import re
from dataclasses import dataclass
from typing import Optional, Union


# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class TgLink:
    """
    Результат парсинга Telegram-ссылки.

    peer:
      - username (str)          → публичный канал / чат
      - chat_id (int, -100...)  → приватный канал (t.me/c)

    message_id:
      - id сообщения (если ссылка на пост)
      - None (если ссылка на канал)

    topic_id:
      - id топика (если есть)
      - None
    """
    peer: Union[str, int]
    message_id: Optional[int] = None
    topic_id: Optional[int] = None


# ============================================================
# REGEX
# ============================================================

# https://t.me/username
_TME_USERNAME_RE = re.compile(
    r"^https?://t\.me/(?P<username>[a-zA-Z0-9_]{5,})/?$"
)

# https://t.me/username/<message_id>
_TME_USERNAME_MSG_RE = re.compile(
    r"^https?://t\.me/(?P<username>[a-zA-Z0-9_]{5,})/(?P<message_id>\d+)/?$"
)

# https://t.me/c/<chat_id>/<message_id>
_TME_C_SIMPLE_RE = re.compile(
    r"^https?://t\.me/c/(?P<chat_id>\d+)/(?P<message_id>\d+)/?$"
)

# https://t.me/c/<chat_id>/<topic_id>/<message_id>
_TME_C_TOPIC_RE = re.compile(
    r"^https?://t\.me/c/(?P<chat_id>\d+)/(?P<topic_id>\d+)/(?P<message_id>\d+)/?$"
)

# https://t.me/c/<chat_id>
_TME_C_CHAT_RE = re.compile(
    r"^https?://t\.me/c/(?P<chat_id>\d+)/?$"
)


# ============================================================
# PARSER
# ============================================================

def parse_tme_link(link: str) -> Optional[TgLink]:
    """
    Универсальный парсер Telegram-ссылок.

    Поддерживает:
      - https://t.me/<username>
      - https://t.me/<username>/<message_id>
      - https://t.me/c/<chat_id>
      - https://t.me/c/<chat_id>/<message_id>
      - https://t.me/c/<chat_id>/<topic_id>/<message_id>

    Возвращает TgLink или None.
    """

    if not isinstance(link, str):
        return None

    link = link.strip()

    # ---------- t.me/c/<chat_id>/<topic_id>/<message_id> ----------
    m = _TME_C_TOPIC_RE.match(link)
    if m:
        internal_id = m.group("chat_id")
        return TgLink(
            peer=int(f"-100{internal_id}"),
            topic_id=int(m.group("topic_id")),
            message_id=int(m.group("message_id")),
        )

    # ---------- t.me/c/<chat_id>/<message_id> ----------
    m = _TME_C_SIMPLE_RE.match(link)
    if m:
        internal_id = m.group("chat_id")
        return TgLink(
            peer=int(f"-100{internal_id}"),
            message_id=int(m.group("message_id")),
        )

    # ---------- t.me/c/<chat_id> ----------
    m = _TME_C_CHAT_RE.match(link)
    if m:
        internal_id = m.group("chat_id")
        return TgLink(
            peer=int(f"-100{internal_id}")
        )

    # ---------- t.me/<username>/<message_id> ----------
    m = _TME_USERNAME_MSG_RE.match(link)
    if m:
        return TgLink(
            peer=m.group("username"),
            message_id=int(m.group("message_id")),
        )

    # ---------- t.me/<username> ----------
    m = _TME_USERNAME_RE.match(link)
    if m:
        return TgLink(
            peer=m.group("username")
        )

    return None


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def parse_tme_c_link(link: str):
    """
    ⚠ DEPRECATED

    Оставлено для обратной совместимости.
    Используй parse_tme_link().

    Возвращает:
      (chat_id, message_id) или None
    """

    parsed = parse_tme_link(link)
    if not parsed:
        return None

    if isinstance(parsed.peer, int) and parsed.message_id:
        return parsed.peer, parsed.message_id

    return None

from __future__ import annotations

from datetime import datetime
from typing import AsyncIterator, List, Optional, Union

from telethon.tl.types import Message, MessageService

import config.settings as settings
from core.logger import logger

# ======================================================
# DEBUG SWITCH
# ======================================================
DEBUG_FILTERS = False   # ← включай при отладке

Post = Union[Message, List[Message]]  # одиночное сообщение или альбом


# ------------------------------------------------------
# HELPERS
# ------------------------------------------------------
def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M")


def _normalize_dt(dt: datetime) -> datetime:
    """Убираем tzinfo для корректного сравнения"""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _in_range(
    msg: Message,
    dt_from: Optional[datetime],
    dt_to: Optional[datetime],
) -> bool:
    md = _normalize_dt(msg.date)

    if dt_from and md < dt_from:
        return False
    if dt_to and md > dt_to:
        return False
    return True


async def _yield_post_by_id(client, source_peer, post_id: int) -> AsyncIterator[Post]:
    """
    Yield одного поста по message_id:
      - Message (если одиночный)
      - List[Message] (если часть альбома)
    Если сообщения нет / удалено / сервисное → ничего не yield-ит.
    """

    msg = await client.get_messages(source_peer, ids=post_id)

    if not msg or isinstance(msg, MessageService):
        logger.warning(f"⚠️ POST_ID │ message {post_id} not found or deleted")
        return

    gid = getattr(msg, "grouped_id", None)

    # ---------- одиночный пост ----------
    if gid is None:
        yield msg
        return

    # ---------- альбом ----------
    album: List[Message] = []

    # Альбомы компактные; берём окно вокруг id и собираем по grouped_id
    async for m in client.iter_messages(
        source_peer,
        min_id=post_id - 20,
        max_id=post_id + 20,
    ):
        if isinstance(m, MessageService):
            continue
        if getattr(m, "grouped_id", None) == gid:
            album.append(m)

    if album:
        yield sorted(album, key=lambda m: m.id)


# ------------------------------------------------------
# MAIN ITERATOR (STREAMING)
# ------------------------------------------------------
async def iter_posts(
    client,
    source_peer,
    post_id: Optional[int] = None,        # ← msg_id из resolve_source(SOURCE)
    source_topic_id: Optional[int] = None, # ← ДОБАВИЛИ (topic/thread id для forum)
) -> AsyncIterator[Post]:
    """
    Итератор постов (streaming):
      - Message
      - List[Message] (альбом)

    Режимы:
      - all
      - date_range
      - last_n   (N последних постов всего чата, с учётом альбомов)
      - post_id
    """

    mode = (settings.FORWARD_MODE or "all").lower().strip()
    if mode not in {"all", "date_range", "last_n", "post_id"}:
        mode = "all"

    if DEBUG_FILTERS:
        logger.debug(f"[FILTERS] mode={mode} post_id={post_id} source_topic_id={source_topic_id}")

    # --------------------------------------------------
    # POST_ID MODE — ранний выход
    # --------------------------------------------------
    if mode == "post_id":
        if not post_id or post_id <= 0:
            logger.warning(
                "⚠️ POST_ID │ FORWARD_MODE=post_id but SOURCE has no message id"
            )
            return

        async for p in _yield_post_by_id(client, source_peer, post_id):
            yield p
        return

    # --------------------------------------------------
    # FILTER PARAMS
    # --------------------------------------------------
    dt_from = _parse_dt(settings.DATE_FROM) if mode == "date_range" else None
    dt_to   = _parse_dt(settings.DATE_TO)   if mode == "date_range" else None
    last_n  = int(settings.LAST_N_MESSAGES or 0) if mode == "last_n" else None

    # --------------------------------------------------
    # LAST_N MODE — берём N последних постов (с конца чата)
    # --------------------------------------------------
    if mode == "last_n":
        if not last_n or last_n <= 0:
            return

        collected: List[Post] = []

        current_gid = None
        album_buf: List[Message] = []

        iter_kwargs = {
            "reverse": False,  # новые → старые
            "limit": None,
        }
        if source_topic_id:
            iter_kwargs["reply_to"] = source_topic_id  # ← ДОБАВИЛИ

        async for msg in client.iter_messages(source_peer, **iter_kwargs):
            if isinstance(msg, MessageService):
                continue

            gid = getattr(msg, "grouped_id", None)

            # ---------- продолжаем альбом ----------
            if current_gid is not None:
                if gid == current_gid:
                    album_buf.append(msg)
                    continue
                else:
                    album = sorted(album_buf, key=lambda m: m.id)
                    collected.append(album)
                    if len(collected) >= last_n:
                        break
                    album_buf = []
                    current_gid = None

            # ---------- начинаем альбом ----------
            if gid is not None:
                current_gid = gid
                album_buf = [msg]
                continue

            # ---------- одиночное ----------
            collected.append(msg)
            if len(collected) >= last_n:
                break

        # Если вышли из цикла посреди альбома — добьём его
        if len(collected) < last_n and current_gid and album_buf:
            album = sorted(album_buf, key=lambda m: m.id)
            collected.append(album)

        # Мы собирали новые→старые, а отдавать хотим старые→новые
        for p in reversed(collected):
            yield p

        return

    # --------------------------------------------------
    # STREAM MESSAGES (all / date_range)
    # --------------------------------------------------
    current_gid = None
    album_buf: List[Message] = []

    iter_kwargs = {
        "reverse": True,  # старые → новые
        "limit": None,
    }
    if source_topic_id:
        iter_kwargs["reply_to"] = source_topic_id  # ← ДОБАВИЛИ

    async for msg in client.iter_messages(source_peer, **iter_kwargs):
        if isinstance(msg, MessageService):
            continue

        gid = getattr(msg, "grouped_id", None)

        # ---------- продолжаем альбом ----------
        if current_gid is not None:
            if gid == current_gid:
                album_buf.append(msg)
                continue
            else:
                album = sorted(album_buf, key=lambda m: m.id)

                if mode != "date_range" or any(
                    _in_range(m, dt_from, dt_to) for m in album
                ):
                    yield album

                album_buf = []
                current_gid = None

        # ---------- начинаем альбом ----------
        if gid is not None:
            current_gid = gid
            album_buf = [msg]
            continue

        # ---------- одиночное сообщение ----------
        if mode == "date_range" and not _in_range(msg, dt_from, dt_to):
            continue

        yield msg

    # --------------------------------------------------
    # FLUSH LAST ALBUM
    # --------------------------------------------------
    if current_gid and album_buf:
        album = sorted(album_buf, key=lambda m: m.id)

        if mode != "date_range" or any(
            _in_range(m, dt_from, dt_to) for m in album
        ):
            yield album

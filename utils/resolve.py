from core.client import client
from core.logger import logger
from utils.tg_links import parse_tme_link, TgLink


async def _find_entity_in_dialogs(peer):
    """
    Fallback: пытаемся найти entity в уже известных диалогах.
    Работает, если пользователь ранее открывал этот чат.

    peer:
      - username (str)
      - chat_id (int, -100...)
    """
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if not entity:
            continue

        # numeric id
        if isinstance(peer, int) and getattr(entity, "id", None) == abs(peer):
            return entity

        # username
        if isinstance(peer, str) and getattr(entity, "username", None) == peer:
            return entity

    return None


# =========================================================
# SOURCE RESOLVE
# =========================================================
async def resolve_source(source):
    """
    SOURCE → (entity, message_id, topic_id)

    SOURCE может быть:
      - ссылкой на канал/чат
      - ссылкой на конкретное сообщение
      - ссылкой на сообщение внутри topic (forum)

    Формат SOURCE уже валиден (validate_settings).
    """

    parsed: TgLink = parse_tme_link(source)
    if not parsed:
        raise RuntimeError(f"Invalid SOURCE: {source}")

    peer = parsed.peer
    msg_id = parsed.message_id
    topic_id = parsed.topic_id  # ← ДОБАВИЛИ

    # 1️⃣ пробуем напрямую
    try:
        entity = await client.get_entity(peer)
        return entity, msg_id, topic_id  # ← ИЗМЕНИЛИ
    except Exception:
        pass

    # 2️⃣ fallback: ищем в диалогах
    entity = await _find_entity_in_dialogs(peer)
    if entity:
        return entity, msg_id, topic_id  # ← ИЗМЕНИЛИ

    # 3️⃣ честная runtime-ошибка
    raise RuntimeError(
        "Cannot resolve SOURCE chat.\n\n"
        f"Source: {source}\n\n"
        "Make sure that:\n"
        "- the account IS a member of this chat\n"
        "- the chat was opened at least once in Telegram\n"
        "- the chat is public or accessible\n"
    )


# =========================================================
# TARGET RESOLVE
# =========================================================
async def resolve_target(target):
    parsed: TgLink = parse_tme_link(target)
    if not parsed:
        raise RuntimeError(f"Invalid TARGET: {target}")

    peer = parsed.peer
    topic_id = parsed.topic_id  # ← ДОБАВИЛИ

    try:
        entity = await client.get_entity(peer)
        return entity, topic_id  # ← ИЗМЕНИЛИ
    except Exception:
        pass

    entity = await _find_entity_in_dialogs(peer)
    if entity:
        return entity, topic_id  # ← ИЗМЕНИЛИ

    # 3️⃣ честная runtime-ошибка
    raise RuntimeError(
        "Cannot resolve TARGET chat.\n\n"
        f"Target: {target}\n\n"
        "Make sure that:\n"
        "- the account HAS access to this chat\n"
        "- the chat was opened at least once in Telegram\n"
        "- the chat is public or accessible\n"
    )

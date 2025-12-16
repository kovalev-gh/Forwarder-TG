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
    SOURCE → (entity, message_id)

    SOURCE может быть:
      - ссылкой на канал
      - ссылкой на конкретное сообщение

    Формат SOURCE уже валиден (validate_settings).
    """

    parsed: TgLink = parse_tme_link(source)
    if not parsed:
        raise RuntimeError(f"Invalid SOURCE: {source}")

    peer = parsed.peer
    msg_id = parsed.message_id

    # 1️⃣ пробуем напрямую
    try:
        entity = await client.get_entity(peer)
        #logger.info(
        #    "📌 SOURCE resolved │ "
        #    f"peer={peer} message_id={msg_id}"
        #)
        return entity, msg_id
    except Exception:
        pass

    # 2️⃣ fallback: ищем в диалогах
    entity = await _find_entity_in_dialogs(peer)
    if entity:
        #logger.info(
        #   "📌 SOURCE resolved from dialogs │ "
        #    f"peer={peer} message_id={msg_id}"
        #)
        return entity, msg_id

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
    """
    TARGET → entity (Channel / Chat)

    TARGET может быть:
      - ссылкой на канал
      - ссылкой на сообщение (message_id игнорируется)
    """

    parsed: TgLink = parse_tme_link(target)
    if not parsed:
        raise RuntimeError(f"Invalid TARGET: {target}")

    peer = parsed.peer

    # 1️⃣ пробуем напрямую
    try:
        entity = await client.get_entity(peer)
        #logger.info(
        #    "🎯 TARGET resolved │ "
        #    f"peer={peer}"
        #)
        return entity
    except Exception:
        pass

    # 2️⃣ fallback: ищем в диалогах
    entity = await _find_entity_in_dialogs(peer)
    if entity:
        #logger.info(
        #    "🎯 TARGET resolved from dialogs │ "
        #    f"peer={peer}"
        #)
        return entity

    # 3️⃣ честная runtime-ошибка
    raise RuntimeError(
        "Cannot resolve TARGET chat.\n\n"
        f"Target: {target}\n\n"
        "Make sure that:\n"
        "- the account HAS access to this chat\n"
        "- the chat was opened at least once in Telegram\n"
        "- the chat is public or accessible\n"
    )

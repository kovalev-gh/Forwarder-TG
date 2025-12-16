from telethon.tl.types import (
    MessageMediaPaidMedia,
    MessageExtendedMediaPreview,
)

from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag


async def handle_paid(msg, final_text, final_entities, reply_to, target_chat):
    """
    Обработчик платного контента (PaidMedia).

    Возвращает:
        - None → если сообщение полностью обработано (stub)
        - msg  → если контент разлочен и должен быть передан дальше другим handler'ам
    """

    paid = msg.media
    unlocked = getattr(paid, "extended_media", None)

    paid_tag = tag("PAID", msg.id)

    # ---------- ПОЛНОСТЬЮ ЗАКРЫТЫЙ КОНТЕНТ ----------
    if unlocked is None:
        logger.warning(f"{paid_tag} │ locked (no access)")

        stub = final_text + "\n\n⚠ Контент доступен только за звезды."
        sent = await client.send_message(
            target_chat,
            stub,
            reply_to=reply_to,
            formatting_entities=final_entities,
        )

        if sent:
            id_map[msg.id] = sent.id
            logger.info(f"{paid_tag} │ stub sent")

        return None

    # ---------- ТОЛЬКО PREVIEW, НЕТ МЕДИА ----------
    if isinstance(unlocked[0], MessageExtendedMediaPreview):
        logger.warning(f"{paid_tag} │ preview only (no media)")

        stub = final_text + "\n\n⚠ Контент доступен только за звезды."
        sent = await client.send_message(
            target_chat,
            stub,
            reply_to=reply_to,
            formatting_entities=final_entities,
        )

        if sent:
            id_map[msg.id] = sent.id
            logger.info(f"{paid_tag} │ stub sent")

        return None

    # ---------- РАЗЛОЧЕННЫЙ КОНТЕНТ ----------
    logger.info(f"{paid_tag} │ unlocked, forwarding media")

    # Подменяем media на разлоченную версию
    msg.media = unlocked[0]

    # Возвращаем msg — теперь другой handler обработает его
    return msg

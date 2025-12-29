from telethon.tl.types import (
    MessageMediaPaidMedia,
    MessageExtendedMediaPreview,
)

from core.ids_map import id_map
from core.logger import logger, tag
from forwarding.media_sender import send_text  # ← ДОБАВИЛИ


async def handle_paid(
    msg,
    final_text,
    final_entities,
    reply_ctx,
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости
):
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

        sent = await send_text(
            chat_id=target_chat,
            text=stub,
            entities=final_entities,
            reply_ctx=reply_ctx,
        )

        if sent:
            id_map[msg.id] = sent.id
            logger.info(f"{paid_tag} │ stub sent")

        return None

    # ---------- ТОЛЬКО PREVIEW, НЕТ МЕДИА ----------
    if isinstance(unlocked[0], MessageExtendedMediaPreview):
        logger.warning(f"{paid_tag} │ preview only (no media)")

        stub = final_text + "\n\n⚠ Контент доступен только за звезды."

        sent = await send_text(
            chat_id=target_chat,
            text=stub,
            entities=final_entities,
            reply_ctx=reply_ctx,
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

from telethon.tl.types import (
    MessageMediaDocument,
    DocumentAttributeSticker,
    InputDocument,
)

from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag


async def handle_sticker(
    msg,
    final_text,
    final_entities,
    reply_ctx,
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости
):
    """
    Корректная пересылка стикера так, чтобы Telegram показывал кнопку
    'Добавить набор'.
    """

    sticker_tag = tag("STICKER", msg.id)

    if not isinstance(msg.media, MessageMediaDocument):
        logger.warning(f"{sticker_tag} │ wrong media type")
        return None

    doc = msg.media.document

    # Проверяем, что документ — стикер
    if not any(isinstance(a, DocumentAttributeSticker) for a in doc.attributes):
        logger.warning(f"{sticker_tag} │ media is not a sticker")
        return None

    input_doc = InputDocument(
        id=doc.id,
        access_hash=doc.access_hash,
        file_reference=doc.file_reference,
    )

    # send_file принимает reply_to только как int, поэтому берём:
    # - reply на конкретного родителя (если есть)
    # - иначе reply на корень темы (если это forum topic)
    send_reply_to = None
    if reply_ctx:
        send_reply_to = reply_ctx.reply_to_msg_id or reply_ctx.top_msg_id

    sent = await client.send_file(
        target_chat,
        input_doc,
        caption=final_text,
        formatting_entities=final_entities,
        reply_to=send_reply_to,
    )

    if sent:
        id_map[msg.id] = sent.id
        logger.info(f"{sticker_tag} │ sent")

    return sent

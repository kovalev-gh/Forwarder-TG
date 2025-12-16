from telethon.tl.types import (
    MessageMediaDocument,
    DocumentAttributeSticker,
    InputDocument,
)

from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag


async def handle_sticker(msg, final_text, final_entities, reply_to, target_chat):
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

    sent = await client.send_file(
        target_chat,
        input_doc,
        caption=final_text,
        formatting_entities=final_entities,
        reply_to=reply_to,
    )

    if sent:
        id_map[msg.id] = sent.id
        logger.info(f"{sticker_tag} │ sent")

    return sent

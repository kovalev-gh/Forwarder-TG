from core.ids_map import id_map
from core.logger import logger, tag
from forwarding.media_sender import send_text  # ← ДОБАВИЛИ


async def handle_other(
    msg,
    final_text,
    final_entities,
    reply_ctx,
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости
):
    """
    Заглушка для неподдерживаемых типов сообщений.

    Использует стандартный header из build_final_text
    и добавляет короткий body.
    """

    other_tag = tag("OTHER", msg.id)

    text = (
        final_text.rstrip()
        + "\n\n"
        + "⚠ Неподдерживаемый тип данных"
    )

    sent = await send_text(
        chat_id=target_chat,
        text=text,
        entities=final_entities,
        reply_ctx=reply_ctx,
    )

    if sent:
        id_map[msg.id] = sent.id
        logger.warning(f"{other_tag} │ sent")

    return sent

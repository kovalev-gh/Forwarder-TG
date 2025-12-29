from core.ids_map import id_map
from core.logger import logger, tag
from forwarding.media_sender import send_text  # ← ДОБАВИЛИ


async def handle_web_preview(
    msg,
    final_text,
    final_entities,
    reply_ctx,
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости
):
    """
    Web page preview (Instagram, YouTube, etc).

    Telegram сам сгенерирует preview из ссылки.
    """


    sent = await send_text(
        chat_id=target_chat,
        text=final_text,
        entities=final_entities,
        reply_ctx=reply_ctx,
        link_preview=True,  # ← ВАЖНО
    )

    return sent

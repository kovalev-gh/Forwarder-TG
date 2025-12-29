from telethon.tl.types import MessageMediaPoll

from core.ids_map import id_map
from core.logger import logger, tag
from forwarding.media_sender import send_poll


async def handle_poll(
    msg,
    final_text,
    final_entities,
    reply_ctx,  # ← было reply_to
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости, но используем reply_ctx
):
    """
    Обработчик опросов (polls).
    Пересобирает опрос и отправляет его корректно в target_chat.
    """

    poll_tag = tag("POLL", msg.id)

    if not isinstance(msg.media, MessageMediaPoll):
        logger.warning(f"{poll_tag} │ wrong media type")
        return None

    poll = msg.media.poll

    sent = await send_poll(
        chat_id=target_chat,
        poll=poll,
        caption=final_text,
        entities=final_entities,
        reply_ctx=reply_ctx,  # ← было reply_to=...
    )

    if sent:
        id_map[msg.id] = sent.id
        logger.info(f"{poll_tag} │ sent")

    return sent

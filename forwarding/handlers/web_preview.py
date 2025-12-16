from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag


async def handle_web_preview(msg, final_text, final_entities, reply_to, target_chat):
    """
    Web page preview (Instagram, YouTube, etc).

    Telegram сам сгенерирует preview из ссылки.
    """

    wp_tag = tag("WEB", msg.id)

    sent = await client.send_message(
        target_chat,
        final_text,
        formatting_entities=final_entities,
        reply_to=reply_to,
        link_preview=True,  # ← ВАЖНО
    )

    #if sent:
    #    id_map[msg.id] = sent.id
    #    logger.info(f"{wp_tag} │ sent")

    return sent

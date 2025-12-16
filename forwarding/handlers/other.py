from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag


async def handle_other(msg, final_text, final_entities, reply_to, target_chat):
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

    sent = await client.send_message(
        target_chat,
        text,
        formatting_entities=final_entities,
        reply_to=reply_to,
    )

    if sent:
        id_map[msg.id] = sent.id
        logger.warning(f"{other_tag} │ sent")

    return sent

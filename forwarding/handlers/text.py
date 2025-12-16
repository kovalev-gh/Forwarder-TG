from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag

TEXT_LIMIT = 4096


def _split_text(text, entities, limit):
    """
    Примитивный, но безопасный сплит текста по лимиту.
    Entities режем по границам чанков.
    """

    if len(text) <= limit:
        return [(text, entities)]

    chunks = []
    offset = 0

    while offset < len(text):
        chunk_text = text[offset:offset + limit]

        chunk_entities = []
        for e in entities:
            start = e.offset
            end = e.offset + e.length

            if start >= offset and end <= offset + limit:
                chunk_entities.append(
                    e.__class__(
                        offset=start - offset,
                        length=e.length,
                        **{
                            k: getattr(e, k)
                            for k in vars(e)
                            if k not in ("offset", "length")
                        }
                    )
                )

        chunks.append((chunk_text, chunk_entities))
        offset += limit

    return chunks


async def handle_text(msg, final_text, final_entities, reply_to, target_chat):
    """
    Обработчик обычного текстового сообщения.

    ПОВЕДЕНИЕ:
    - если текст <= 4096 → отправляется одним сообщением
    - если > 4096 → режется на несколько сообщений-ответов
    """

    text_tag = tag("TEXT", msg.id)

    parts = _split_text(final_text, final_entities, TEXT_LIMIT)

    sent = None
    current_reply = reply_to

    for idx, (text, entities) in enumerate(parts, start=1):
        sent = await client.send_message(
            target_chat,
            text,
            formatting_entities=entities,
            reply_to=current_reply,
        )

        if not sent:
            break

        current_reply = sent.id

        #logger.info(
        #    f"{text_tag} │ sent part {idx}/{len(parts)}"
        #)

    if sent:
        id_map[msg.id] = sent.id
        logger.info(f"{text_tag} │ sent")

    return sent

from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag
from forwarding.media_sender import send_text  # ← ДОБАВИЛИ

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


async def handle_text(
    msg,
    final_text,
    final_entities,
    reply_ctx,
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости
):
    """
    Обработчик обычного текстового сообщения.

    ПОВЕДЕНИЕ:
    - если текст <= 4096 → отправляется одним сообщением
    - если > 4096 → режется на несколько сообщений-ответов

    ВАЖНО:
    Текст в forum topics отправляем через raw SendMessageRequest (send_text),
    чтобы можно было передать InputReplyToMessage(top_msg_id=...).
    """

    text_tag = tag("TEXT", msg.id)

    parts = _split_text(final_text, final_entities, TEXT_LIMIT)

    sent = None
    current_ctx = reply_ctx  # для первого чанка

    for idx, (text, entities) in enumerate(parts, start=1):
        sent = await send_text(
            chat_id=target_chat,
            text=text,
            entities=entities,
            reply_ctx=current_ctx,
        )

        if not sent:
            break

        # Следующие чанки цепляем reply'ем друг к другу.
        # Для этого делаем новый контекст: reply_to=sent.id, top_msg_id тот же.
        next_ctx = None
        if reply_ctx:
            next_ctx = reply_ctx.__class__(
                reply_to_msg_id=sent.id,
                top_msg_id=getattr(reply_ctx, "top_msg_id", None),
            )
        else:
            # без topics тоже работает (просто обычный reply)
            next_ctx = None

        current_ctx = next_ctx

    if sent:
        id_map[msg.id] = sent.id
        logger.info(f"{text_tag} │ sent")

    return sent

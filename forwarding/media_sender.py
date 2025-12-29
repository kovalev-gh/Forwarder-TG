from core.client import client
from utils.helpers import extract_msg
from core.progress import make_progress

from telethon.tl.functions.messages import SendMediaRequest, SendMessageRequest
from telethon.tl.types import (
    InputMediaUploadedPhoto,
    InputMediaUploadedDocument,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    InputMediaPoll,
    Poll,
    PollAnswer,
    InputReplyToMessage,
)


# ============================================================
# INTERNAL: BUILD InputReplyToMessage FROM reply_ctx
# ============================================================
def _build_reply_to_obj(reply_ctx):
    """
    Возвращает TL-объект InputReplyToMessage или None.

    Правила:
    1) Если есть reply_to_msg_id: отвечаем на него.
       - Если это ответ внутри topic: добавляем top_msg_id (topicID),
         чтобы Telegram не "уронил" reply в General.
    2) Если reply_to_msg_id НЕТ, но есть top_msg_id: это НЕ reply, а просто "постинг в топик".
       - Чтобы сообщение гарантированно попало в нужный топик, делаем
         InputReplyToMessage(reply_to_msg_id=top_msg_id).
       - top_msg_id в этом случае не нужен (это и есть base).
    3) Если ничего нет: None.
    """
    if not reply_ctx:
        return None

    reply_to_msg_id = getattr(reply_ctx, "reply_to_msg_id", None)
    top_msg_id = getattr(reply_ctx, "top_msg_id", None)

    # Нечего привязывать.
    if not reply_to_msg_id and not top_msg_id:
        return None

    # --------------------------------------------------------
    # CASE A: обычное сообщение в topic (не reply)
    # --------------------------------------------------------
    if not reply_to_msg_id and top_msg_id:
        # В raw API reply_to должен быть TLObject, поэтому используем InputReplyToMessage.
        return InputReplyToMessage(
            reply_to_msg_id=top_msg_id,
            top_msg_id=None,
        )

    # --------------------------------------------------------
    # CASE B: настоящий reply (на конкретное сообщение)
    # --------------------------------------------------------
    # top_msg_id добавляем только когда:
    # - топик задан
    # - reply_to_msg_id != topicID
    # - topicID != 1 (General)
    need_top = bool(
        top_msg_id
        and reply_to_msg_id
        and reply_to_msg_id != top_msg_id
        and top_msg_id != 1
    )

    return InputReplyToMessage(
        reply_to_msg_id=reply_to_msg_id,
        top_msg_id=top_msg_id if need_top else None,
    )


# ============================================================
# SEND TEXT (RAW, FOR TOPICS)
# ============================================================
async def send_text(chat_id, text, entities, reply_ctx, link_preview=None):
    """
    Отправка текста через raw messages.SendMessageRequest.

    ВАЖНО:
    - reply_to здесь должен быть TLObject (InputReplyToMessage) или None. [web:41]
    """
    reply_to_obj = _build_reply_to_obj(reply_ctx)

    updates = await client(
        SendMessageRequest(
            peer=chat_id,
            message=text,
            entities=entities,
            reply_to=reply_to_obj,
            no_webpage=(False if link_preview is None else (not bool(link_preview))),
        )
    )

    msg = await extract_msg(updates)
    return msg


# ============================================================
# SEND PHOTO (NO PROGRESS)
# ============================================================
async def send_photo(chat_id, path, original_name, caption, entities, reply_ctx, spoiler):
    uploaded = await client.upload_file(
        path,
        file_name=original_name,
    )

    media = InputMediaUploadedPhoto(
        file=uploaded,
        spoiler=spoiler,
    )

    reply_to_obj = _build_reply_to_obj(reply_ctx)

    updates = await client(
        SendMediaRequest(
            peer=chat_id,
            media=media,
            message="",
            reply_to=reply_to_obj,
        )
    )

    msg = await extract_msg(updates)
    if not msg:
        return None

    await client.edit_message(
        chat_id,
        msg.id,
        caption,
        formatting_entities=entities,
    )

    return msg


# ============================================================
# SEND VIDEO (WITH UPLOAD PROGRESS)
# ============================================================
async def send_video(
    chat_id,
    path,
    original_name,
    caption,
    entities,
    reply_ctx,
    spoiler,
    progress_callback=None,
    progress_prefix=None,
):
    finish = None

    if progress_callback is None and progress_prefix:
        progress_callback, finish = make_progress(progress_prefix)

    uploaded = await client.upload_file(
        path,
        file_name=original_name,
        progress_callback=progress_callback,
    )

    if finish:
        finish()

    media = InputMediaUploadedDocument(
        file=uploaded,
        mime_type="video/mp4",
        spoiler=spoiler,
        attributes=[
            DocumentAttributeVideo(
                duration=1,
                w=1,
                h=1,
                supports_streaming=True,
            )
        ],
    )

    reply_to_obj = _build_reply_to_obj(reply_ctx)

    updates = await client(
        SendMediaRequest(
            peer=chat_id,
            media=media,
            message="",
            reply_to=reply_to_obj,
        )
    )

    msg = await extract_msg(updates)
    if not msg:
        return None

    await client.edit_message(
        chat_id,
        msg.id,
        caption,
        formatting_entities=entities,
    )

    return msg


# ============================================================
# SEND VOICE (NO PROGRESS)
# ============================================================
async def send_voice(
    chat_id,
    path,
    original_name,
    caption,
    entities,
    reply_ctx,
    spoiler,
    duration=1,
):
    uploaded = await client.upload_file(
        path,
        file_name=original_name,
    )

    media = InputMediaUploadedDocument(
        file=uploaded,
        mime_type="audio/ogg",
        spoiler=spoiler,
        attributes=[
            DocumentAttributeAudio(
                duration=duration,
                voice=True,
            )
        ],
    )

    reply_to_obj = _build_reply_to_obj(reply_ctx)

    updates = await client(
        SendMediaRequest(
            peer=chat_id,
            media=media,
            message="",
            reply_to=reply_to_obj,
        )
    )

    msg = await extract_msg(updates)
    if not msg:
        return None

    await client.edit_message(
        chat_id,
        msg.id,
        caption,
        formatting_entities=entities,
    )

    return msg


# ============================================================
# SEND POLL
# ============================================================
async def send_poll(chat_id, poll, caption, entities, reply_ctx):
    answers = [
        PollAnswer(text=a.text, option=a.option)
        for a in poll.answers
    ]

    new_poll = Poll(
        id=0,
        question=poll.question,
        answers=answers,
        multiple_choice=poll.multiple_choice,
        quiz=poll.quiz,
        public_voters=poll.public_voters,
    )

    media = InputMediaPoll(poll=new_poll)

    # Для poll оставляем high-level send_message, но reply_to берём как int.
    # Если есть reply_to_msg_id -> отвечаем на него, иначе (если задан top_msg_id) -> отвечаем на root темы.
    base_reply = None
    if reply_ctx:
        base_reply = getattr(reply_ctx, "reply_to_msg_id", None) or getattr(reply_ctx, "top_msg_id", None)

    sent = await client.send_message(
        chat_id,
        file=media,
        message=caption,
        formatting_entities=entities,
        reply_to=base_reply,
    )

    return sent

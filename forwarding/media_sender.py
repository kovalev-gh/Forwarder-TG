from core.client import client
from utils.helpers import extract_msg
from core.progress import make_progress

from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import (
    InputMediaUploadedPhoto,
    InputMediaUploadedDocument,
    DocumentAttributeVideo,
    DocumentAttributeAudio,
    InputMediaPoll,
    Poll,
    PollAnswer,
)


# ============================================================
# SEND PHOTO (NO PROGRESS)
# ============================================================
async def send_photo(chat_id, path, original_name, caption, entities, reply_to, spoiler):
    uploaded = await client.upload_file(
        path,
        file_name=original_name,
    )

    media = InputMediaUploadedPhoto(
        file=uploaded,
        spoiler=spoiler,
    )

    updates = await client(
        SendMediaRequest(peer=chat_id, media=media, message="")
    )

    msg = await extract_msg(updates)
    if not msg:
        return None

    if reply_to:
        stub = await client.send_message(chat_id, ".", reply_to=reply_to)
        await client.delete_messages(chat_id, [stub.id])

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
    reply_to,
    spoiler,
    progress_callback=None,
    progress_prefix=None,
):
    """
    Если передан progress_callback — используем его.
    Иначе, если передан progress_prefix — создаём progress внутри.
    """

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

    updates = await client(
        SendMediaRequest(peer=chat_id, media=media, message="")
    )

    msg = await extract_msg(updates)
    if not msg:
        return None

    if reply_to:
        stub = await client.send_message(chat_id, ".", reply_to=reply_to)
        await client.delete_messages(chat_id, [stub.id])

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
    reply_to,
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

    updates = await client(
        SendMediaRequest(peer=chat_id, media=media, message="")
    )

    msg = await extract_msg(updates)
    if not msg:
        return None

    if reply_to:
        stub = await client.send_message(chat_id, ".", reply_to=reply_to)
        await client.delete_messages(chat_id, [stub.id])

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
async def send_poll(chat_id, poll, caption, entities, reply_to):
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

    sent = await client.send_message(
        chat_id,
        file=media,
        message=caption,
        formatting_entities=entities,
        reply_to=reply_to,
    )

    return sent

import os

from telethon.tl.types import MessageMediaDocument, DocumentAttributeAudio

from core.ids_map import id_map
from core.client import client
from core.logger import logger, tag

from forwarding.media_sender import send_voice

from utils.media import (
    is_media_spoiler,
    prepare_generic_file,
    cleanup_file,
)

from utils.caption_policy import apply_caption_policy

from config.settings import DOWNLOAD_DIR, DELETE_FILES_AFTER_SEND


async def handle_voice(msg, final_text, final_entities, reply_to, target_chat):
    """
    Обработчик VOICE сообщений (.ogg, opus).

    ПОВЕДЕНИЕ:
    - если caption влезает → voice + полный caption
    - если НЕ влезает:
        * voice + служебка + notice
        * оригинальный текст отправляется reply ниже

    ПРАВИЛА:
    - БЕЗ процентов
    - БЕЗ секунд в логах
    - БЕЗ progress bar
    """

    voice_tag = tag("VOICE", msg.id)

    # -------------------------------------------------
    # TYPE CHECK
    # -------------------------------------------------
    if not isinstance(msg.media, MessageMediaDocument):
        logger.warning(f"{voice_tag} │ wrong media type")
        return None

    doc = msg.media.document

    # -------------------------------------------------
    # DETECT VOICE + DURATION
    # -------------------------------------------------
    is_voice = False
    duration = 1

    for attr in doc.attributes:
        if isinstance(attr, DocumentAttributeAudio) and getattr(attr, "voice", False):
            is_voice = True
            duration = getattr(attr, "duration", 1)
            break

    if not is_voice:
        logger.warning(f"{voice_tag} │ not a voice message")
        return None

    # -------------------------------------------------
    # SPOILER (для закрытых каналов)
    # -------------------------------------------------
    spoiler = is_media_spoiler(msg)

    # -------------------------------------------------
    # ORIGINAL NAME (для Telegram)
    # -------------------------------------------------
    original_name = (
        msg.file.name
        if msg.file and msg.file.name
        else f"{msg.id}"
    )

    # -------------------------------------------------
    # DOWNLOAD (NO PROGRESS)
    # -------------------------------------------------
    tmp_path = os.path.join(DOWNLOAD_DIR, f"tmp_{msg.id}")

    raw_path = await msg.download_media(
        file=tmp_path,
        thumb=None,
    )

    if not raw_path:
        logger.warning(f"{voice_tag} │ download failed")
        return None

    media = None
    sent = None

    try:
        # -------------------------------------------------
        # PREPARE FILE
        # -------------------------------------------------
        media = prepare_generic_file(
            path=raw_path,
            original_name=original_name,
        )

        # -------------------------------------------------
        # APPLY CAPTION POLICY
        # -------------------------------------------------
        base_text = msg.message or ""

        text_data = {
            "final_text": final_text,
            "final_entities": final_entities,
            "base_text": base_text,
            "base_entities": msg.entities or [],
            "header_text_len": len(final_text) - len(base_text),
        }

        caption, caption_entities, extra_text, extra_entities = apply_caption_policy(
            text_data
        )

        # -------------------------------------------------
        # SEND VOICE
        # -------------------------------------------------
        sent = await send_voice(
            chat_id=target_chat,
            path=media.path,
            original_name=media.original_name,
            caption=caption,
            entities=caption_entities,
            reply_to=reply_to,
            spoiler=spoiler,
            duration=duration,
        )

        if sent:
            id_map[msg.id] = sent.id

        # -------------------------------------------------
        # SEND EXTRA TEXT BELOW (IF ANY)
        # -------------------------------------------------
        if sent and extra_text:
            await client.send_message(
                target_chat,
                extra_text,
                formatting_entities=extra_entities,
                reply_to=sent.id,
            )

        # -------------------------------------------------
        # FINAL LOG
        # -------------------------------------------------
        size_mb = os.path.getsize(media.path) / (1024 * 1024)

        logger.info(
            f"{voice_tag} │ sent ({size_mb:.1f} MB)"
        )

        return sent

    finally:
        # -------------------------------------------------
        # CLEANUP
        # -------------------------------------------------
        if DELETE_FILES_AFTER_SEND:
            if media and media.path:
                cleanup_file(media.path)
            cleanup_file(raw_path)

import os

from core.ids_map import id_map
from core.client import client
from forwarding.media_sender import send_photo

from core.logger import logger, tag

from utils.media import (
    is_media_spoiler,
    prepare_image_file,
    cleanup_file,
)

from utils.caption_policy import apply_caption_policy

from config.settings import DOWNLOAD_DIR, DELETE_FILES_AFTER_SEND


async def handle_photo(msg, final_text, final_entities, reply_to, target_chat):
    """
    Обработчик PHOTO.

    ПОВЕДЕНИЕ:
    - если caption влезает → фото + полный caption
    - если НЕ влезает:
        * фото + служебка + notice
        * оригинальный текст отправляется reply ниже
    """

    spoiler = is_media_spoiler(msg)
    photo_tag = tag("PHOTO", msg.id)

    # -------------------------------------------------
    # ORIGINAL NAME
    # -------------------------------------------------
    original_name = (
        msg.file.name
        if msg.file and msg.file.name
        else f"{msg.id}"
    )

    # -------------------------------------------------
    # DOWNLOAD (NO UI PROGRESS)
    # -------------------------------------------------
    tmp_path = os.path.join(DOWNLOAD_DIR, f"tmp_{msg.id}")

    raw_path = await msg.download_media(
        file=tmp_path,
        thumb=None,
    )

    if not raw_path:
        logger.warning(f"{photo_tag} │ download failed")
        return None

    size_mb = os.path.getsize(raw_path) / (1024 * 1024)

    logger.info(
        f"{photo_tag} │ download ({size_mb:.1f} MB)"
    )

    media = None
    sent = None

    try:
        # -------------------------------------------------
        # PREPARE IMAGE
        # -------------------------------------------------
        media = prepare_image_file(
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
        # SEND PHOTO
        # -------------------------------------------------
        sent = await send_photo(
            chat_id=target_chat,
            path=media.path,
            original_name=media.original_name,
            caption=caption,
            entities=caption_entities,
            reply_to=reply_to,
            spoiler=spoiler,
        )

        if sent:
            id_map[msg.id] = sent.id

        logger.info(
            f"{photo_tag} │ sent ({size_mb:.1f} MB)"
        )

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

        return sent

    finally:
        # -------------------------------------------------
        # CLEANUP
        # -------------------------------------------------
        if DELETE_FILES_AFTER_SEND:
            if media and media.path:
                cleanup_file(media.path)
            cleanup_file(raw_path)

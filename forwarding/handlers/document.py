import os

from telethon.tl.types import MessageMediaDocument

from core.ids_map import id_map
from core.client import client
from core.logger import logger, tag
from core.progress import make_progress

from utils.media import (
    prepare_generic_file,
    cleanup_file,
)

from utils.caption_policy import apply_caption_policy

from config.settings import DOWNLOAD_DIR, DELETE_FILES_AFTER_SEND


async def handle_document(msg, final_text, final_entities, reply_to, target_chat):
    """
    Обработчик DOCUMENT.

    ПОВЕДЕНИЕ:
    - если caption влезает → отправляется как есть
    - если НЕ влезает:
        * в caption остаётся служебка + notice
        * оригинальный текст отправляется reply ниже
    """

    # -------------------------------------------------
    # TYPE CHECK (защита)
    # -------------------------------------------------
    if not isinstance(msg.media, MessageMediaDocument):
        return None

    file_tag = tag("FILE", msg.id)

    # -------------------------------------------------
    # ORIGINAL NAME
    # -------------------------------------------------
    original_name = (
        msg.file.name
        if msg.file and msg.file.name
        else f"{msg.id}"
    )

    # -------------------------------------------------
    # DOWNLOAD (UI progress)
    # -------------------------------------------------
    tmp_path = os.path.join(DOWNLOAD_DIR, f"tmp_{msg.id}")

    dl_progress, dl_finish = make_progress(
        f"{file_tag} │ downloading"
    )

    raw_path = await msg.download_media(
        file=tmp_path,
        thumb=None,
        progress_callback=dl_progress,
    )

    if not raw_path:
        logger.warning(f"{file_tag} │ download failed")
        return None

    dl_time = dl_finish()
    size_mb = os.path.getsize(raw_path) / (1024 * 1024)

    logger.info(
        f"{file_tag} │ download ({size_mb:.1f} MB, {dl_time:.1f} s)"
    )

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
        text_data = {
            "final_text": final_text,
            "final_entities": final_entities,
            "base_text": msg.message or "",
            "base_entities": [],
            "header_text_len": len(final_text) - len(msg.message or ""),
        }

        caption, caption_entities, extra_text, extra_entities = apply_caption_policy(
            text_data
        )

        # -------------------------------------------------
        # UPLOAD (AS DOCUMENT)
        # -------------------------------------------------
        ul_progress, ul_finish = make_progress(
            f"{file_tag} │ uploading"
        )

        sent = await client.send_file(
            target_chat,
            media.path,
            caption=caption,
            formatting_entities=caption_entities,
            reply_to=reply_to,
            force_document=True,
            progress_callback=ul_progress,
        )

        ul_time = ul_finish()

        if sent:
            id_map[msg.id] = sent.id

        logger.info(
            f"{file_tag} │ sent ({size_mb:.1f} MB, {ul_time:.1f} s)"
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

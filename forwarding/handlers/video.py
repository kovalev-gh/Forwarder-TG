import os

from core.ids_map import id_map
from core.client import client
from forwarding.media_sender import send_video  # ничего не меняем: extra_text оставляем через client.send_message

from core.logger import logger, tag
from core.progress import make_progress

from utils.media import (
    is_media_spoiler,
    prepare_generic_file,
    cleanup_file,
)

from utils.caption_policy import apply_caption_policy

from config.settings import DOWNLOAD_DIR, DELETE_FILES_AFTER_SEND


async def handle_video(
    msg,
    final_text,
    final_entities,
    reply_ctx,
    target_chat,
    target_topic_id=None,  # ← оставили для совместимости
):
    """
    Обработчик ВИДЕО.

    ПОВЕДЕНИЕ:
    - если caption влезает → видео + полный caption
    - если НЕ влезает:
        * видео + служебка + notice
        * оригинальный текст отправляется reply ниже
    """

    spoiler = is_media_spoiler(msg)
    video_tag = tag("VIDEO", msg.id)

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
        f"{video_tag} │ downloading"
    )

    raw_path = await msg.download_media(
        file=tmp_path,
        thumb=None,
        progress_callback=dl_progress,
    )

    if not raw_path:
        logger.warning(f"{video_tag} │ download failed")
        return None

    dl_time = dl_finish()
    size_mb = os.path.getsize(raw_path) / (1024 * 1024)

    logger.info(
        f"{video_tag} │ download ({size_mb:.1f} MB, {dl_time:.1f} s)"
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
        # UPLOAD VIDEO
        # -------------------------------------------------
        ul_progress, ul_finish = make_progress(
            f"{video_tag} │ uploading"
        )

        sent = await send_video(
            chat_id=target_chat,
            path=media.path,
            original_name=media.original_name,
            caption=caption,
            entities=caption_entities,
            reply_ctx=reply_ctx,
            spoiler=spoiler,
            progress_callback=ul_progress,
        )

        ul_time = ul_finish()

        if sent:
            id_map[msg.id] = sent.id

        logger.info(
            f"{video_tag} │ sent ({size_mb:.1f} MB, {ul_time:.1f} s)"
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

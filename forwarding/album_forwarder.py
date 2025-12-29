import os
import time
import asyncio

from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPaidMedia,
    MessageExtendedMediaPreview,
    DocumentAttributeSticker,
    InputDocument,
)

from config.settings import DOWNLOAD_DIR, DELETE_FILES_AFTER_SEND
from core.client import client
from core.ids_map import id_map
from core.logger import logger, tag
from core.progress import make_progress

from forwarding.message_builder import build_final_text
from forwarding.reply_handler import handle_reply

from forwarding.handlers.media_utils import detect_media_kind

from utils.caption_policy import apply_caption_policy

from utils.media import (
    prepare_image_file,
    prepare_generic_file,
    cleanup_file,
)


async def forward_album(
    group_msgs,
    public_cid,
    album_no: int,
    target_chat,
    target_topic_id=None,
):
    """
    Пересылает grouped_id как альбом.

    ПОВЕДЕНИЕ ПРИ ПЕРЕПОЛНЕНИИ CAPTION:
    - в альбоме остаётся служебка + notice
    - оригинальный текст отправляется одним reply ниже
    """

    if not group_msgs:
        return

    album_tag = tag("ALBUM", album_no)

    # -------------------------------------------------
    # 1. SORT + CAPTION MESSAGE
    # -------------------------------------------------
    group_msgs = sorted(group_msgs, key=lambda m: m.id)
    caption_msg = next((m for m in group_msgs if m.message), group_msgs[-1])

    reply_ctx, quote_text, quote_entities = await handle_reply(
        caption_msg,
        public_cid,
        target_chat,
        target_topic_id=target_topic_id,
    )

    text_data = await build_final_text(
        caption_msg,
        quote_text,
        quote_entities,
        client,
    )

    caption, caption_entities, extra_text, extra_entities = apply_caption_policy(
        text_data
    )

    logger.info(f"{album_tag} │ processing {len(group_msgs)} items")

    # -------------------------------------------------
    # 2. SPLIT BY CANONICAL KIND
    # -------------------------------------------------
    media_msgs = []   # PHOTO + VIDEO
    doc_msgs = []     # DOCUMENT
    has_locked_paid = False

    for m in group_msgs:
        kind = detect_media_kind(m)
        if kind in ("PHOTO", "VIDEO"):
            media_msgs.append(m)
        elif kind == "DOCUMENT":
            doc_msgs.append(m)

    # -------------------------------------------------
    # helper: spinner
    # -------------------------------------------------
    async def _run_spinner(prefix):
        progress, finish = make_progress(prefix, spinner_only=True)

        async def _spinner():
            try:
                while True:
                    progress(1, 0)
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(_spinner())
        return task, finish

    caption_attached = False

    async def _attach_caption(sent):
        nonlocal caption_attached
        if caption_attached:
            return None

        messages = sent if isinstance(sent, list) else [sent]
        caption_target = messages[0]

        await client.edit_message(
            target_chat,
            caption_target.id,
            caption,
            formatting_entities=caption_entities,
        )

        caption_attached = True
        return caption_target.id

    # -------------------------------------------------
    # helper: reply_to for send_file (int)
    # -------------------------------------------------
    def _base_reply_to_from_ctx():
        if not reply_ctx:
            return None
        return reply_ctx.reply_to_msg_id or reply_ctx.top_msg_id

    base_reply_to = _base_reply_to_from_ctx()

    # -------------------------------------------------
    # 3. PHOTO + VIDEO ALBUM
    # -------------------------------------------------
    if media_msgs:
        upload_paths = []
        original_ids = []

        for idx, m in enumerate(media_msgs, start=1):
            media = m.media

            # ---------- PAID ----------
            if isinstance(media, MessageMediaPaidMedia):
                unlocked = getattr(media, "extended_media", None)
                if not unlocked or isinstance(unlocked[0], MessageExtendedMediaPreview):
                    has_locked_paid = True
                    logger.warning(
                        f"💰 PAID │ album #{album_no} │ locked item {idx}/{len(media_msgs)}"
                    )
                    continue
                m.media = unlocked[0]

            original_name = (
                getattr(getattr(m, "file", None), "name", None)
                or f"{m.id}"
            )

            kind = detect_media_kind(m)
            tmp_path = os.path.join(DOWNLOAD_DIR, f"tmp_{m.id}")

            progress = None
            finish = None

            if kind == "VIDEO":
                progress, finish = make_progress(
                    f"{album_tag} │ item {idx}/{len(media_msgs)} VIDEO"
                )

            raw_path = await m.download_media(
                file=tmp_path,
                progress_callback=progress,
            )

            if not raw_path:
                logger.warning(
                    f"{album_tag} │ failed download item {idx}/{len(media_msgs)}"
                )
                continue

            elapsed = finish() if finish else None
            size_mb = os.path.getsize(raw_path) / (1024 * 1024)

            try:
                if kind == "PHOTO":
                    prepared = prepare_image_file(raw_path, original_name)
                    logger.info(
                        f"{album_tag} │ item {idx}/{len(media_msgs)} PHOTO "
                        f"({size_mb:.1f} MB)"
                    )
                else:
                    prepared = prepare_generic_file(raw_path, original_name)
                    logger.info(
                        f"{album_tag} │ item {idx}/{len(media_msgs)} VIDEO "
                        f"({size_mb:.1f} MB, {elapsed:.1f} s)"
                    )

                upload_paths.append(prepared.path)
                original_ids.append(m.id)

            finally:
                if DELETE_FILES_AFTER_SEND:
                    cleanup_file(raw_path)

        if upload_paths:
            if has_locked_paid:
                caption += "\n\n⚠ Часть контента доступна только за звезды."

            spinner, finish = await _run_spinner(
                f"{album_tag} │ uploading album"
            )

            sent = await client.send_file(
                target_chat,
                upload_paths,
                caption="",
                reply_to=base_reply_to,
                supports_streaming=True,
            )

            spinner.cancel()
            finish()

            caption_mid = await _attach_caption(sent)
            if caption_mid:
                for mid in original_ids:
                    id_map[mid] = caption_mid

            # ----- SEND EXTRA TEXT BELOW -----
            if caption_mid and extra_text:
                await client.send_message(
                    target_chat,
                    extra_text,
                    formatting_entities=extra_entities,
                    reply_to=caption_mid,
                )

            logger.info(
                f"{album_tag} │ sent, caption attached to msg {caption_mid}"
            )

            if DELETE_FILES_AFTER_SEND:
                for p in upload_paths:
                    cleanup_file(p)

    # -------------------------------------------------
    # 4. DOCUMENT ALBUM
    # -------------------------------------------------
    if doc_msgs:
        upload_paths = []
        original_ids = []

        for idx, m in enumerate(doc_msgs, start=1):
            media = m.media

            if isinstance(media, MessageMediaDocument):
                doc = media.document
                if any(isinstance(a, DocumentAttributeSticker) for a in doc.attributes):
                    upload_paths.append(
                        InputDocument(
                            id=doc.id,
                            access_hash=doc.access_hash,
                            file_reference=doc.file_reference,
                        )
                    )
                    original_ids.append(m.id)
                    logger.info(
                        f"{album_tag} │ item {idx}/{len(doc_msgs)} STICKER"
                    )
                    continue

            original_name = (
                getattr(getattr(m, "file", None), "name", None)
                or f"{m.id}"
            )

            tmp_path = os.path.join(DOWNLOAD_DIR, f"tmp_{m.id}")

            progress, finish = make_progress(
                f"{album_tag} │ item {idx}/{len(doc_msgs)} FILE"
            )

            raw_path = await m.download_media(
                file=tmp_path,
                progress_callback=progress,
            )

            if not raw_path:
                logger.warning(
                    f"{album_tag} │ failed download item {idx}/{len(doc_msgs)}"
                )
                continue

            elapsed = finish()
            size_mb = os.path.getsize(raw_path) / (1024 * 1024)

            try:
                prepared = prepare_generic_file(raw_path, original_name)
                upload_paths.append(prepared.path)
                original_ids.append(m.id)

                logger.info(
                    f"{album_tag} │ item {idx}/{len(doc_msgs)} FILE "
                    f"({size_mb:.1f} MB, {elapsed:.1f} s)"
                )

            finally:
                if DELETE_FILES_AFTER_SEND:
                    cleanup_file(raw_path)

        if upload_paths:
            spinner, finish = await _run_spinner(
                f"{album_tag} │ uploading album"
            )

            sent = await client.send_file(
                target_chat,
                upload_paths,
                caption="",
                reply_to=base_reply_to,
                force_document=True,
            )

            spinner.cancel()
            finish()

            caption_mid = await _attach_caption(sent)
            if caption_mid:
                for mid in original_ids:
                    id_map[mid] = caption_mid

            # ----- SEND EXTRA TEXT BELOW -----
            if caption_mid and extra_text:
                await client.send_message(
                    target_chat,
                    extra_text,
                    formatting_entities=extra_entities,
                    reply_to=caption_mid,
                )

            logger.info(
                f"{album_tag} │ sent, caption attached to msg {caption_mid}"
            )

            if DELETE_FILES_AFTER_SEND:
                for p in upload_paths:
                    if isinstance(p, str):
                        cleanup_file(p)

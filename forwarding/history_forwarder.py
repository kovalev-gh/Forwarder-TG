import asyncio

from telethon.tl.types import MessageService
from telethon.errors import FloodWaitError

from core.client import client
from core.logger import logger
from core.progress import make_progress

from config.settings import FORWARD_MODE

from forwarding.filters import iter_posts
from forwarding.album_forwarder import forward_album
from forwarding.message_builder import build_final_text
from forwarding.reply_handler import handle_reply

# handlers
from forwarding.handlers.text import handle_text
from forwarding.handlers.photo import handle_photo
from forwarding.handlers.video import handle_video
from forwarding.handlers.voice import handle_voice
from forwarding.handlers.sticker import handle_sticker
from forwarding.handlers.document import handle_document
from forwarding.handlers.poll import handle_poll
from forwarding.handlers.paid import handle_paid
from forwarding.handlers.other import handle_other
from forwarding.handlers.web_preview import handle_web_preview

# utils (CANONICAL)
from forwarding.handlers.media_utils import (
    detect_media_kind,
    is_sticker,
    is_voice,
    is_poll,
    is_paid,
    is_web_preview,
)

# =========================================================
# GLOBAL SEND DELAY (seconds)
# =========================================================
SEND_DELAY = 0.2


async def forward_history(
    source_chat,
    target_chat,
    source_post_id=None,
    target_topic_id=None,   # нужно для forum topics (куда постить)
    source_topic_id=None,   # ← ДОБАВИЛИ (откуда читать, если SOURCE указывает topic)
):
    logger.info("🚀 FORWARD │ history started")

    target_ent = await client.get_entity(target_chat)
    public_cid = abs(getattr(target_ent, "id", target_chat))

    album_counter = 0

    # =========================================================
    # PREPARING DATA SPINNER (last_n / date_range only)
    # =========================================================
    prep_task = None
    prep_finish = None

    if FORWARD_MODE in {"last_n", "date_range"}:
        progress, finish = make_progress(
            "Preparing data",
            spinner_only=True,
        )

        async def _prepare_spinner():
            try:
                while True:
                    progress(1, 0)
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass

        prep_task = asyncio.create_task(_prepare_spinner())
        prep_finish = finish

    # =========================================================
    # MAIN LOOP — ITERATE POSTS, NOT MESSAGES
    # =========================================================
    async for post in iter_posts(
        client,
        source_chat,
        post_id=source_post_id,
        source_topic_id=source_topic_id,  # ← ДОБАВИЛИ
    ):
        # -----------------------------------------------------
        # STOP PREPARING SPINNER BEFORE FIRST REAL SEND
        # -----------------------------------------------------
        if prep_task:
            prep_task.cancel()
            prep_finish()
            prep_task = None
            prep_finish = None

        try:
            # ⏱ GLOBAL DELAY BEFORE ANY SEND OPERATION
            await asyncio.sleep(SEND_DELAY)

            # =================================================
            # ALBUM = SINGLE POST
            # =================================================
            if isinstance(post, list):
                album_counter += 1
                await forward_album(
                    post,
                    public_cid,
                    album_counter,
                    target_chat,
                    target_topic_id=target_topic_id,  # ← ДОБАВИЛИ (ВАЖНО для topic)
                )
                continue

            # =================================================
            # SINGLE MESSAGE
            # =================================================
            msg = post

            if isinstance(msg, MessageService):
                continue

            # -------------------------------------------------
            # REPLY / QUOTE / ANCHOR
            # -------------------------------------------------
            reply_ctx, quote_text, quote_entities = await handle_reply(
                msg,
                public_cid,
                target_chat,
                target_topic_id=target_topic_id,  # ← ВАЖНО: прокидываем topic id
            )

            # -------------------------------------------------
            # BUILD FINAL TEXT
            # -------------------------------------------------
            text_data = await build_final_text(
                msg,
                quote_text,
                quote_entities,
                client,
            )

            final_text = text_data["final_text"]
            final_entities = text_data["final_entities"]

            # -------------------------------------------------
            # POLL
            # -------------------------------------------------
            if is_poll(msg):
                await handle_poll(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # PAID CONTENT
            # -------------------------------------------------
            if is_paid(msg):
                paid_result = await handle_paid(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                if paid_result is None:
                    continue
                msg = paid_result

            kind = detect_media_kind(msg)

            # -------------------------------------------------
            # TEXT
            # -------------------------------------------------
            if kind == "TEXT":
                await handle_text(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # WEB PREVIEW
            # -------------------------------------------------
            if is_web_preview(msg):
                await handle_web_preview(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # STICKER
            # -------------------------------------------------
            if is_sticker(msg):
                await handle_sticker(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # VOICE
            # -------------------------------------------------
            is_voice_flag, _ = is_voice(msg)
            if is_voice_flag:
                await handle_voice(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # PHOTO
            # -------------------------------------------------
            if kind == "PHOTO":
                await handle_photo(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # VIDEO
            # -------------------------------------------------
            if kind == "VIDEO":
                sent = await handle_video(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                if sent:
                    continue

            # -------------------------------------------------
            # DOCUMENT
            # -------------------------------------------------
            if kind == "DOCUMENT":
                await handle_document(
                    msg,
                    final_text,
                    final_entities,
                    reply_ctx,  # ← было reply_new_id
                    target_chat,
                    target_topic_id=target_topic_id,
                )
                continue

            # -------------------------------------------------
            # OTHER
            # -------------------------------------------------
            await handle_other(
                msg,
                final_text,
                final_entities,
                reply_ctx,  # ← было reply_new_id
                target_chat,
                target_topic_id=target_topic_id,
            )

        # =====================================================
        # 🟥 FLOODWAIT
        # =====================================================
        except FloodWaitError as e:
            logger.error(
                f"🟥 FLOOD_WAIT │ Telegram требует подождать {e.seconds} секунд. "
                f"Скрипт остановлен."
            )
            raise SystemExit(1)

        except Exception:
            if isinstance(post, list):
                post_id = post[0].id if post else "?"
            else:
                post_id = getattr(post, "id", "?")

            logger.exception(
                f"❌ FORWARD │ error processing post {post_id}"
            )

    logger.info("🎉 FORWARD │ history completed")

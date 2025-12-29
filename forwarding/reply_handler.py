from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, List

from core.ids_map import id_map
from config.settings import FORWARD_MODE

from telethon.tl.types import (
    MessageEntityBlockquote,
    MessageEntityTextUrl,
)

from core.reply_anchor import get_or_create_anchor


# -------------------------------------------------
# CONSTANT TEXT (ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ)
# -------------------------------------------------
OUT_OF_RANGE_QUOTE_TEXT = (
    "Цитата из поста или сообщения, "
    "которое было опубликовано ранее выбранного диапазона"
)


# -------------------------------------------------
# REPLY CONTEXT
# -------------------------------------------------
@dataclass
class ReplyCtx:
    """
    Контекст для корректной отправки reply в forum topics.

    reply_to_msg_id:
      - новый message_id родителя в target (если он был в диапазоне и уже отправлен)
      - либо anchor_id (если используете anchors)
      - либо None (если reply нужно игнорировать)

    top_msg_id:
      - topic_id / message_id root-топика в target, если пересылаете в forum topic
      - нужен, чтобы Telegram не "уронил" сообщения в General.
    """
    reply_to_msg_id: Optional[int] = None
    top_msg_id: Optional[int] = None


async def handle_reply(
    msg,
    public_cid,
    target_chat,
    target_topic_id: Optional[int] = None,
) -> Tuple[ReplyCtx, str, List]:
    """
    Обработка reply / quote.

    Итоговая логика:

    1) Нет reply:
        - возвращаем ReplyCtx(reply_to_msg_id=None, top_msg_id=target_topic_id)
          → сообщение пойдёт в указанный topic, но не будет reply.
    2) Есть QUOTE:
        - оригинал в диапазоне → честная цитата с ссылкой на пересланный пост
        - оригинал ВНЕ диапазона → подменённая цитата + anchor
        - НИКОГДА не делаем reply (reply_to_msg_id=None)
    3) Обычный reply:
        - оригинал в диапазоне → reply_to_msg_id = id пересланного родителя в target
        - оригинал ВНЕ диапазона:
            - FORWARD_MODE == "all" → игнорируем reply (reply_to_msg_id=None)
            - иначе → reply_to_msg_id = anchor_id
    """

    # По умолчанию: знаем только topicID (если задан), но не делаем никакого reply.
    reply_ctx = ReplyCtx(reply_to_msg_id=None, top_msg_id=target_topic_id)
    quote_text = ""
    quote_entities: List = []

    # -------------------------------------------------
    # NO REPLY
    # -------------------------------------------------
    if not msg.reply_to:
        # Просто сообщение в топике.
        # media_sender возьмёт reply_to_msg_id=None и top_msg_id=target_topic_id,
        # и отправит как reply к root-топика (или без reply, если topicID не задан).
        return reply_ctx, quote_text, quote_entities

    rh = msg.reply_to
    orig_id = getattr(rh, "reply_to_msg_id", None)

    if not orig_id:
        # reply-объект есть, но без конкретного message_id — считаем, что это "без reply".
        return reply_ctx, quote_text, quote_entities

    # =================================================
    # 1. QUOTE LOGIC (ВСЕГДА ПЕРВИЧНА)
    # =================================================
    if getattr(rh, "quote", False):
        # ---------------------------------------------
        # 1.1 ОРИГИНАЛ В ДИАПАЗОНЕ → ЧЕСТНАЯ ЦИТАТА
        # ---------------------------------------------
        if orig_id in id_map and getattr(rh, "quote_text", None):
            qt = (rh.quote_text or "").strip()

            if qt:
                quote_text = f"{qt}\n"
                target_id = id_map[orig_id]
                public_link = f"https://t.me/c/{public_cid}/{target_id}"

                quote_entities = [
                    MessageEntityBlockquote(
                        offset=0,
                        length=len(qt),
                    ),
                    MessageEntityTextUrl(
                        offset=0,
                        length=len(qt),
                        url=public_link,
                    ),
                ]

            # ⛔️ при quote НИКОГДА не делаем reply
            reply_ctx.reply_to_msg_id = None
            return reply_ctx, quote_text, quote_entities

        # ---------------------------------------------
        # 1.2 ОРИГИНАЛ ВНЕ ДИАПАЗОНА → ПОДМЕНЁННАЯ ЦИТАТА
        # ---------------------------------------------
        anchor_id = await get_or_create_anchor(
            target_chat,
            "quote",
            target_topic_id=target_topic_id,
        )

        qt = OUT_OF_RANGE_QUOTE_TEXT
        quote_text = f"{qt}\n"

        public_link = f"https://t.me/c/{public_cid}/{anchor_id}"

        quote_entities = [
            MessageEntityBlockquote(
                offset=0,
                length=len(qt),
            ),
            MessageEntityTextUrl(
                offset=0,
                length=len(qt),
                url=public_link,
            ),
        ]

        # ⛔️ при quote НИКОГДА не делаем reply
        reply_ctx.reply_to_msg_id = None
        return reply_ctx, quote_text, quote_entities

    # =================================================
    # 2. ORDINARY REPLY (НЕ ЦИТАТА)
    # =================================================
    # ---------------------------------------------
    # 2.1 ОРИГИНАЛ В ДИАПАЗОНЕ → ЧЕСТНЫЙ REPLY
    # ---------------------------------------------
    if orig_id in id_map:
        reply_ctx.reply_to_msg_id = id_map[orig_id]
        return reply_ctx, quote_text, quote_entities

    # ---------------------------------------------
    # 2.2 ОРИГИНАЛ ВНЕ ДИАПАЗОНА → FALLBACK
    # ---------------------------------------------
    if FORWARD_MODE != "all":
        # Ответ на anchor в том же чате/топике.
        reply_ctx.reply_to_msg_id = await get_or_create_anchor(
            target_chat,
            "reply",
            target_topic_id=target_topic_id,
        )
    else:
        # Игнорируем reply, оставляем только привязку к topicID (если есть).
        reply_ctx.reply_to_msg_id = None

    return reply_ctx, quote_text, quote_entities

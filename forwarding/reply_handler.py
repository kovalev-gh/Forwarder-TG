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
    "которое было опубликованного ранее выбранного диапазона"
)


async def handle_reply(msg, public_cid, target_chat):
    """
    Обработка reply / quote.

    Итоговая логика:

    1) Нет reply → ничего не делаем
    2) Есть QUOTE:
        - оригинал в диапазоне → обычная цитата
        - оригинал ВНЕ диапазона → подменённая цитата + anchor
        - НИКОГДА не делаем reply
    3) Обычный reply:
        - оригинал в диапазоне → честный reply
        - оригинал ВНЕ диапазона:
            - FORWARD_MODE == "all" → игнорируем
            - иначе → reply на anchor
    """

    reply_new_id = None
    quote_text = ""
    quote_entities = []

    # -------------------------------------------------
    # NO REPLY
    # -------------------------------------------------
    if not msg.reply_to:
        return reply_new_id, quote_text, quote_entities

    rh = msg.reply_to
    orig_id = rh.reply_to_msg_id

    if not orig_id:
        return reply_new_id, quote_text, quote_entities

    # =================================================
    # 1. QUOTE LOGIC (ВСЕГДА ПЕРВИЧНА)
    # =================================================
    if getattr(rh, "quote", False):
        # ---------------------------------------------
        # 1.1 ОРИГИНАЛ В ДИАПАЗОНЕ → ЧЕСТНАЯ ЦИТАТА
        # ---------------------------------------------
        if orig_id in id_map and rh.quote_text:
            qt = rh.quote_text.strip()

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
            return None, quote_text, quote_entities

        # ---------------------------------------------
        # 1.2 ОРИГИНАЛ ВНЕ ДИАПАЗОНА → ПОДМЕНЁННАЯ ЦИТАТА
        # ---------------------------------------------
        anchor_id = await get_or_create_anchor(
            target_chat,
            "quote",
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
        return None, quote_text, quote_entities

    # =================================================
    # 2. ORDINARY REPLY (НЕ ЦИТАТА)
    # =================================================
    # ---------------------------------------------
    # 2.1 ОРИГИНАЛ В ДИАПАЗОНЕ → ЧЕСТНЫЙ REPLY
    # ---------------------------------------------
    if orig_id in id_map:
        reply_new_id = id_map[orig_id]
        return reply_new_id, quote_text, quote_entities

    # ---------------------------------------------
    # 2.2 ОРИГИНАЛ ВНЕ ДИАПАЗОНА → FALLBACK
    # ---------------------------------------------
    if FORWARD_MODE != "all":
        reply_new_id = await get_or_create_anchor(
            target_chat,
            "reply",
        )

    return reply_new_id, quote_text, quote_entities

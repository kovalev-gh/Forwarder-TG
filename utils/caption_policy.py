from telethon.tl.types import MessageEntityItalic

# ============================================================
# LIMITS
# ============================================================

CAPTION_LIMIT = 1024

# ============================================================
# USER NOTICE (shown in media post if text moved below)
# ============================================================

NOTICE_TEXT = "В оригинале медиа и текст ниже идут одним постом"


# ============================================================
# MAIN POLICY
# ============================================================

def apply_caption_policy(text_data):
    """
    Применяет политику overflow для caption медиа / альбомов.

    Вход:
        text_data — dict из build_final_text(), содержит:
            final_text
            final_entities
            base_text
            base_entities
            header_text_len

    Выход:
        caption_text
        caption_entities
        extra_text (или None)
        extra_entities (или None)

    Логика:
      - если всё влезает в caption → ничего не делаем
      - если не влезает:
          * caption = ТОЛЬКО служебная часть + notice
          * оригинальный текст отправляется отдельным reply
    """

    final_text = text_data["final_text"]
    final_entities = text_data["final_entities"]
    base_text = text_data["base_text"]
    base_entities = text_data["base_entities"]
    header_len = text_data["header_text_len"]

    # --------------------------------------------------------
    # CASE 1: всё влезает в caption
    # --------------------------------------------------------
    if len(final_text) <= CAPTION_LIMIT:
        return final_text, final_entities, None, None

    # --------------------------------------------------------
    # CASE 2: overflow — делаем служебный caption
    # --------------------------------------------------------

    # служебная часть (переслано / quote / timestamp / sender)
    header_text = final_text[:header_len].rstrip()

    caption_text = (
        header_text
        + "\n\n"
        + NOTICE_TEXT
    )

    # entities — только те, что полностью в header
    caption_entities = [
        e for e in final_entities
        if e.offset + e.length <= len(header_text)
    ]

    # italic для notice
    caption_entities.append(
        MessageEntityItalic(
            offset=len(header_text) + 2,
            length=len(NOTICE_TEXT),
        )
    )

    # --------------------------------------------------------
    # extra text — чистый оригинал (без служебки)
    # --------------------------------------------------------
    extra_text = base_text
    extra_entities = base_entities

    return caption_text, caption_entities, extra_text, extra_entities

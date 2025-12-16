from utils.entities import clone_entities
from telethon.tl.types import (
    MessageEntityItalic,
    MessageEntityPre,
    MessageEntityTextUrl,
)


async def get_forward_header(msg, client):
    """
    Возвращает текст "Переслано от X\n" и entities.
    Если сообщение не переслано — возвращает ("", []).
    """

    if not msg.fwd_from:
        return "", []

    fwd = msg.fwd_from

    if getattr(fwd, "from_name", None):
        name = fwd.from_name
    else:
        try:
            ent = await client.get_entity(fwd.from_id)
            name = (
                getattr(ent, "title", None)
                or getattr(ent, "first_name", None)
                or "Источник"
            )
        except Exception:
            name = "Источник"

    header_text = f"Переслано от {name}\n"
    header_entities = []

    return header_text, header_entities


def clone_and_shift_entity(e, offset_shift=0):
    """
    Унифицированное клонирование entity с учётом всех возможных параметров.
    """

    params = {
        "offset": e.offset + offset_shift,
        "length": e.length,
    }

    if hasattr(e, "url"):
        params["url"] = getattr(e, "url", None)

    if hasattr(e, "language"):
        params["language"] = getattr(e, "language", "") or ""

    return e.__class__(**params)


async def build_final_text(msg, quote_text, quote_entities, client):
    """
    Формирует финальный текст сообщения.

    ВАЖНО:
    Возвращает НЕ ТОЛЬКО финальный текст, но и:
      - base_text (чистый оригинальный текст)
      - base_entities
      - длину служебной части (header_text_len)

    Это нужно для политики caption overflow.
    """

    # ------------------------------------------------------------
    # TIMESTAMP
    # ------------------------------------------------------------
    timestamp = msg.date.strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------------------------
    # CHAT TYPE + SENDER NAME
    # ------------------------------------------------------------
    sender_part = ""

    try:
        chat = await msg.get_chat()
        is_channel = getattr(chat, "broadcast", False)
    except Exception:
        is_channel = False

    if not is_channel:
        sender = await msg.get_sender()
        if sender:
            first = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            full_name = " ".join(x for x in (first, last) if x).strip()
            if full_name:
                sender_part = full_name

    # ------------------------------------------------------------
    # HEADER LINE (ITALIC)
    # ------------------------------------------------------------
    if sender_part:
        header_line = f"{sender_part} · {timestamp}"
    else:
        header_line = timestamp

    header_entities = [
        MessageEntityItalic(
            offset=0,
            length=len(header_line),
        )
    ]

    # ------------------------------------------------------------
    # BASE TEXT (ORIGINAL MESSAGE ONLY)
    # ------------------------------------------------------------
    base_text = msg.message or ""
    base_entities = clone_entities(base_text, msg.entities)

    # ------------------------------------------------------------
    # FORWARD HEADER
    # ------------------------------------------------------------
    fwd_text, fwd_entities = await get_forward_header(msg, client)

    # ------------------------------------------------------------
    # FINAL TEXT (FULL)
    # ------------------------------------------------------------
    final_text = (
        fwd_text
        + quote_text
        + header_line
        + "\n\n"
        + base_text
    )

    final_entities = []
    offset = 0

    # 1) forward header entities
    for e in fwd_entities:
        final_entities.append(clone_and_shift_entity(e, offset))
    offset += len(fwd_text)

    # 2) quote entities
    for e in quote_entities:
        final_entities.append(clone_and_shift_entity(e, offset))
    offset += len(quote_text)

    # 3) header line (italic)
    for e in header_entities:
        final_entities.append(clone_and_shift_entity(e, offset))
    offset += len(header_line) + 2  # "\n\n"

    # 4) base text entities
    for e in base_entities:
        final_entities.append(clone_and_shift_entity(e, offset))

    # ------------------------------------------------------------
    # RETURN STRUCT (for caption policy)
    # ------------------------------------------------------------
    return {
        "final_text": final_text,
        "final_entities": final_entities,
        "base_text": base_text,
        "base_entities": base_entities,
        "header_text_len": len(final_text) - len(base_text),
    }

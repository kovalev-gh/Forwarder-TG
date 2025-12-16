def utf16_to_utf32_offset(text: str, utf16_offset: int) -> int:
    if utf16_offset is None:
        return 0
    before_utf16 = text.encode("utf-16-le")[:utf16_offset * 2]
    return len(before_utf16.decode("utf-16-le"))


async def extract_msg(updates):
    from telethon.tl.types import UpdateNewMessage, UpdateNewChannelMessage

    if hasattr(updates, "updates"):
        for u in updates.updates:
            if isinstance(u, (UpdateNewMessage, UpdateNewChannelMessage)):
                return u.message
    return None

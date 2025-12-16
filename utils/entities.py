from telethon.tl.types import (
    MessageEntityPre,
    MessageEntitySpoiler,
    MessageEntityBlockquote,
    MessageEntityTextUrl,
    MessageEntityCustomEmoji,
)


def clone_entities(text, entities):
    """
    Клонирует entities для нового текста.

    ВАЖНО:
    - MessageEntityCustomEmoji НЕ клонируется
      (у него обязателен document_id, Telegram
       корректно рендерит emoji и без entity)
    """

    new = []
    if not entities:
        return new

    for e in entities:
        off, ln = e.offset, e.length

        # 🚫 CustomEmoji пропускаем полностью
        if isinstance(e, MessageEntityCustomEmoji):
            continue

        if isinstance(e, MessageEntityPre):
            new.append(
                MessageEntityPre(
                    off,
                    ln,
                    e.language or ""
                )
            )

        elif isinstance(e, MessageEntityTextUrl):
            new.append(
                MessageEntityTextUrl(
                    off,
                    ln,
                    e.url
                )
            )

        elif isinstance(e, MessageEntitySpoiler):
            new.append(
                MessageEntitySpoiler(
                    off,
                    ln
                )
            )

        elif isinstance(e, MessageEntityBlockquote):
            new.append(
                MessageEntityBlockquote(
                    off,
                    ln
                )
            )

        else:
            # универсальный fallback
            try:
                new.append(e.__class__(off, ln))
            except TypeError:
                try:
                    new.append(e.__class__(offset=off, length=ln))
                except Exception:
                    # если entity невозможно клонировать — просто пропускаем
                    continue

    return new

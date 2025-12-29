import asyncio

from core.client import client
from forwarding.history_forwarder import forward_history

from config.settings import SOURCE, TARGET
from config.validate_settings import validate_settings
from utils.resolve import resolve_source, resolve_target


async def main():
    validate_settings()

    async with client:
        source_entity, source_post_id, source_topic_id = await resolve_source(SOURCE)  # ← ИЗМЕНИЛИ
        target_entity, target_topic_id = await resolve_target(TARGET)

        await forward_history(
            source_chat=source_entity,
            target_chat=target_entity,
            source_post_id=source_post_id,
            target_topic_id=target_topic_id,
            source_topic_id=source_topic_id,  # ← ДОБАВИЛИ
        )


if __name__ == "__main__":
    asyncio.run(main())

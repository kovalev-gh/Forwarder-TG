import json
import os
from typing import Literal, Optional

from core.client import client
from core.logger import logger

# -------------------------------------------------
# PATH
# -------------------------------------------------
STATE_PATH = os.path.join("runtime", "state.json")

# -------------------------------------------------
# ANCHOR TEXTS (СОГЛАСОВАННЫЕ ФОРМУЛИРОВКИ)
# -------------------------------------------------
ANCHOR_TEXTS = {
    "reply": "Пост или сообщение было опубликовано ранее выбранного диапазона",
    "quote": (
        "Цитата из поста или сообщения, "
        "которое было опубликованного ранее выбранного диапазона"
    ),
}

AnchorType = Literal["reply", "quote"]


# -------------------------------------------------
# STATE HELPERS
# -------------------------------------------------
def _load_state() -> dict:
    """
    Загружает runtime/state.json.
    Если файла нет или он битый — создаёт новый.
    """
    if not os.path.exists(STATE_PATH):
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        state = {"anchors": {}}
        _save_state(state)
        return state

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("state.json is not a dict")
            return data
    except Exception:
        logger.exception("Failed to read state.json, recreating")
        state = {"anchors": {}}
        _save_state(state)
        return state


def _save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# -------------------------------------------------
# PUBLIC API
# -------------------------------------------------
async def get_or_create_anchor(
    target_chat: int,
    anchor_type: AnchorType,
    target_topic_id: Optional[int] = None,  # ← ДОБАВИЛИ
) -> int:
    """
    Возвращает message_id служебного anchor-сообщения.

    Anchor:
    - привязан к target_chat
    - привязан к target_topic_id (если задан), чтобы anchor создавался в нужной теме
    - различается по типу: reply / quote
    - хранится в runtime/state.json

    Создаётся автоматически при первом использовании.
    """

    state = _load_state()

    anchors_root = state.setdefault("anchors", {})

    # ВАЖНО: разделяем anchors по чату И по теме, иначе anchor из General будет ломать replies в topic.
    chat_key = f"{target_chat}:{target_topic_id or 0}"  # ← ИЗМЕНИЛИ
    chat_anchors = anchors_root.setdefault(chat_key, {})

    anchor_key = f"{anchor_type}_out_of_range"

    # -------------------------------------------------
    # 1. УЖЕ СУЩЕСТВУЕТ
    # -------------------------------------------------
    anchor_id = chat_anchors.get(anchor_key)
    if isinstance(anchor_id, int):
        return anchor_id

    # -------------------------------------------------
    # 2. СОЗДАЁМ НОВЫЙ ANCHOR
    # -------------------------------------------------
    text = ANCHOR_TEXTS[anchor_type]

    logger.info(
        f"Creating {anchor_type} anchor for target chat {target_chat} "
        f"(topic={target_topic_id or 0})"
    )

    # Если target_topic_id задан — создаём anchor как reply на root темы,
    # чтобы он гарантированно оказался в этом топике, а не в General.
    sent = await client.send_message(
        target_chat,
        text,
        reply_to=target_topic_id if target_topic_id else None,  # ← ДОБАВИЛИ
    )

    chat_anchors[anchor_key] = sent.id
    _save_state(state)

    return sent.id

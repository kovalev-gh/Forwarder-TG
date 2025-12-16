from datetime import datetime

from config import settings
from utils.tg_links import parse_tme_link


_ALLOWED_FORWARD_MODES = {
    "post_id",
    "all",
    "last_n",
    "date_range",
}


def _parse_dt(value: str, name: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    except Exception:
        raise RuntimeError(
            f"Invalid {name}.\n"
            "Expected format: YYYY-MM-DD HH:MM\n"
            f"Got: {value}"
        )


def validate_settings():
    """
    Validate user-provided configuration.

    Raises RuntimeError with human-readable message
    if configuration is invalid.
    """

    # -------------------------------------------------
    # SOURCE / TARGET
    # -------------------------------------------------
    parsed_links = {}

    for name in ("SOURCE", "TARGET"):
        value = getattr(settings, name)
        parsed = parse_tme_link(value)

        if not parsed:
            raise RuntimeError(
                f"Invalid {name}.\n"
                "Allowed Telegram links:\n"
                "  https://t.me/<username>\n"
                "  https://t.me/<username>/<message_id>\n"
                "  https://t.me/c/<chat_id>\n"
                "  https://t.me/c/<chat_id>/<message_id>\n"
                "  https://t.me/c/<chat_id>/<topic_id>/<message_id>\n\n"
                f"Got: {value}"
            )

        parsed_links[name] = parsed

    # -------------------------------------------------
    # FORWARD MODE
    # -------------------------------------------------
    if settings.FORWARD_MODE not in _ALLOWED_FORWARD_MODES:
        raise RuntimeError(
            "Invalid FORWARD_MODE.\n"
            f"Allowed values: {', '.join(sorted(_ALLOWED_FORWARD_MODES))}\n"
            f"Got: {settings.FORWARD_MODE}"
        )

    # -------------------------------------------------
    # POST_ID MODE — SOURCE MUST CONTAIN MESSAGE_ID
    # -------------------------------------------------
    if settings.FORWARD_MODE == "post_id":
        source = parsed_links["SOURCE"]
        if not source.message_id:
            raise RuntimeError(
                "FORWARD_MODE='post_id' requires SOURCE "
                "to be a link to a specific message.\n\n"
                "Examples:\n"
                "  https://t.me/<username>/<message_id>\n"
                "  https://t.me/c/<chat_id>/<message_id>\n"
                "  https://t.me/c/<chat_id>/<topic_id>/<message_id>"
            )

    # -------------------------------------------------
    # LAST N
    # -------------------------------------------------
    if settings.FORWARD_MODE == "last_n":
        if not isinstance(settings.LAST_N_MESSAGES, int):
            raise RuntimeError(
                "LAST_N_MESSAGES must be an integer "
                "when FORWARD_MODE='last_n'"
            )
        if settings.LAST_N_MESSAGES <= 0:
            raise RuntimeError(
                "LAST_N_MESSAGES must be > 0 "
                "when FORWARD_MODE='last_n'"
            )

    # -------------------------------------------------
    # DATE RANGE
    # -------------------------------------------------
    if settings.FORWARD_MODE == "date_range":
        if not settings.DATE_FROM and not settings.DATE_TO:
            raise RuntimeError(
                "FORWARD_MODE='date_range' requires "
                "DATE_FROM and/or DATE_TO"
            )

        dt_from = None
        dt_to = None

        if settings.DATE_FROM:
            dt_from = _parse_dt(settings.DATE_FROM, "DATE_FROM")
        if settings.DATE_TO:
            dt_to = _parse_dt(settings.DATE_TO, "DATE_TO")

        if dt_from and dt_to and dt_from > dt_to:
            raise RuntimeError(
                "Invalid date range: DATE_FROM > DATE_TO"
            )

    # -------------------------------------------------
    # DELETE_FILES_AFTER_SEND
    # -------------------------------------------------
    if not isinstance(settings.DELETE_FILES_AFTER_SEND, bool):
        raise RuntimeError(
            "DELETE_FILES_AFTER_SEND must be True or False"
        )

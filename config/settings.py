import os

# SOURCE / TARGET
# Only Telegram message links
SOURCE = "https://t.me/username/123456"
TARGET = "https://t.me/c/987654/3210"

# FORWARD MODE
# all       — forward all messages
# last_n   — forward last N messages
# date_range — forward messages by date
# post_id  — forward one message (recommended)
FORWARD_MODE = "all"

# LAST N SETTINGS
LAST_N_MESSAGES = 100

# DATE RANGE SETTINGS
# ⚠️ IMPORTANT: All dates and times MUST be specified in UTC.
# Format: "YYYY-MM-DD HH:MM" (e.g. "2025-12-11 00:00")
DATE_FROM = None
DATE_TO = None

# FILE HANDLING
# If True  → delete downloaded files after successful send
# If False → keep files in DOWNLOAD_DIR
DELETE_FILES_AFTER_SEND = True

# PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
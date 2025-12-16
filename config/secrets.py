import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# TELEGRAM API (FROM ENV)
# ==============================

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
SESSION_NAME = os.getenv("TG_SESSION_NAME", "tg_master_session")

if not API_ID or not API_HASH:
    raise RuntimeError("TG_API_ID / TG_API_HASH not set in .env")

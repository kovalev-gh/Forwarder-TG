# Telegram Forwarder

This script forwards messages from **private Telegram channels and groups** (if your account has access).

---

## Quick start

1. Get `api_id` and `api_hash`
2. Create and fill the `.env` file
3. Set **SOURCE** and **TARGET** (message links)
4. Choose forward mode
5. Run the script

---

## How to get api_id and api_hash (Telethon)

1. Open Telegram official website:
   [https://my.telegram.org/auth](https://my.telegram.org/auth)
2. Login with your phone number and confirm the code from Telegram.
3. Open **API Development Tools**.
4. Click **Create new application**.
5. Fill the form (any values are fine).

After creation you will see:

* **api_id** — numeric ID
* **api_hash** — string value

✔ These values are required for Telethon.

⚠ **Keep them private** — they give access to your account.

---

## Installation

Requirements:

* Python 3.10+
* `uv`

Install dependencies:

```bash
uv pip install -r requirements.txt
```

---

## Environment variables (.env)

The project contains a template file:

```
.env.example
```

Before the first run you **must** copy it to `.env`:

```bash
cp .env.example .env
```

Then open `.env` and fill your data:

```env
API_ID=123456
API_HASH=abcdef1234567890abcdef1234567890
```

---

## First run

On the first run Telethon will:

* ask for your phone number
* send a login code in Telegram
* create a session file (`*.session`)

⚠ This is normal. You do it only once.

---

## Settings

All user settings are located in:

```
config/settings.py
```

---

## SOURCE and TARGET (required)

❗ **You must provide links to any message from each chat**

### Supported formats

```
https://t.me/c/<chat_id>/<message_id>
https://t.me/c/<chat_id>/<topic_id>/<message_id>
https://t.me/<username>/<message_id>
https://t.me/<username>/<topic_id>/<message_id>
```


❌ **Not allowed**:

* channel links without `message_id`
* numeric IDs

If the format is invalid, the script will stop with an error.

---

## Forward modes

Set in `config/settings.py`:

```python
FORWARD_MODE = "post_id"
```

### post_id

Forwards **one specific message** from `SOURCE`.

* if the message is part of an album → the **whole album** is forwarded
* if the message is deleted → a log message is printed

---

### all

Forwards **all messages** from the source chat.

```python
FORWARD_MODE = "all"
```

---

### last_n

Forwards last **N** messages.

```python
FORWARD_MODE = "last_n"
LAST_N_MESSAGES = 10
```

---

### date_range

Forwards messages in a date range.

⚠️ **Important:**  
Time must be specified in **UTC**.

```python
FORWARD_MODE = "date_range"
DATE_FROM = "2025-01-01 00:00"
DATE_TO   = "2025-01-31 23:59"
```

Date format:

```
YYYY-MM-DD HH:MM
```

If a message is part of an album, the whole album is forwarded.

---

## File handling

```python
DELETE_FILES_AFTER_SEND = True
```

* `True` — downloaded files are deleted after sending
* `False` — files stay in the `downloads/` folder

---

## Run

```bash
uv run main.py
```
---
##  Future versions

See `./FEATURES.MD`
import os
import re
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION_NAME = "insighthub_session"
TARGET_CHANNEL = "ChartBankGlobal"

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# -----------------------------
# Simple tag filter logic
# -----------------------------
INCLUDE_TAGS = {
    "Freshview",
    "Update",
    "Partbooking",
    "Takeoutcapital"
}

TAG_PATTERN = re.compile(r"#(\w+)")


def extract_tags(text):
    if not text:
        return []
    return TAG_PATTERN.findall(text)


def is_relevant(tags):
    return any(tag in INCLUDE_TAGS for tag in tags)


async def main():
    print("Connecting to Telegram...")

    await client.start()

    print("Connected.\n")

    channel = await client.get_entity(TARGET_CHANNEL)

    messages = await client.get_messages(channel, limit=50)

    print(f"Scanning {len(messages)} messages...\n")

    for msg in reversed(messages):
        text = msg.message

        if not text:
            continue

        tags = extract_tags(text)

        if not is_relevant(tags):
            continue

        print("--------------------------------------------------")
        print(f"Date: {msg.date}")
        print(f"Tags: {tags}")
        print(f"Text:\n{text}\n")


with client:
    client.loop.run_until_complete(main())
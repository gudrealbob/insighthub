import os
import re
import yaml

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

with open("config/settings.yaml", "r") as f:
    settings = yaml.safe_load(f)

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION_NAME = "insighthub_session"

TARGET_CHANNEL = settings["telegram"]["channels"][0]
MESSAGE_LIMIT = settings["collector"]["message_limit"]

INCLUDE_TAGS = set(settings["filters"]["include_tags"])

TAG_PATTERN = re.compile(r"#(\w+)")

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


def extract_tags(text):
    if not text:
        return []
    return TAG_PATTERN.findall(text)


def is_relevant(tags):
    return any(tag in INCLUDE_TAGS for tag in tags)


async def main():
    await client.start()

    channel = await client.get_entity(TARGET_CHANNEL)

    messages = await client.get_messages(
        channel,
        limit=MESSAGE_LIMIT,
    )

    print(f"\nReading channel: {TARGET_CHANNEL}\n")

    for msg in reversed(messages):
        text = msg.message

        if not text:
            continue

        tags = extract_tags(text)

        if not is_relevant(tags):
            continue

        print("-" * 80)
        print(msg.date)
        print(tags)
        print(text)


with client:
    client.loop.run_until_complete(main())
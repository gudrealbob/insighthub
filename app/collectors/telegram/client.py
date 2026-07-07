import os
import re
import yaml

from app.db.database import SessionLocal
from app.services.message_service import save_message
from app.services.recommendation_service import save_recommendation
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

with open("config/settings.yaml", "r") as f:
    settings = yaml.safe_load(f)

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION_NAME = "insighthub_session"

TARGET_CHANNELS = settings["telegram"]["channels"]
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

    for channel_cfg in TARGET_CHANNELS:

    channel = await client.get_entity(
        channel_cfg["channel_name"]
    )

    print(
        f"\nReading channel: "
        f"{channel_cfg['display_name']}\n"
    )

    messages = await client.get_messages(
        channel,
        limit=MESSAGE_LIMIT,
    )

    for msg in reversed(messages):
        text = msg.message

        if not text:
            continue

        tags = extract_tags(text)

        if not is_relevant(tags):
            continue

        db = SessionLocal()
        source = get_source_by_name(db, "telegram")
        try:
            message = save_message(
                db=db,
                source_id=source.id,      
                telegram_message=msg,
                tags=tags,
            )

            print(f"Saved message {message.id}")
            save_recommendation(db, message)

        finally:
            db.close()


with client:
    client.loop.run_until_complete(main())
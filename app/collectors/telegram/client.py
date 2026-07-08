import os
import re
import yaml

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import UsernameNotOccupiedError

from app.db.database import SessionLocal
from app.models.channel import Channel
from app.services.channel_service import update_checkpoint
from app.services.message_service import save_message
from app.services.recommendation_service import save_recommendation


load_dotenv()


with open("config/settings.yaml", "r") as f:
    settings = yaml.safe_load(f)


API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

SESSION_NAME = "insighthub_session"


TARGET_CHANNELS = settings["telegram"]["channels"]

COLLECTOR_MODE = settings["collector"]["mode"]
MESSAGE_LIMIT = settings["collector"]["message_limit"]

INCLUDE_TAGS = set(settings["filters"]["include_tags"])

TAG_PATTERN = re.compile(r"#(\w+)")


client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH
)


def extract_tags(text):
    if not text:
        return []

    return TAG_PATTERN.findall(text)


def is_relevant(tags):
    return any(tag in INCLUDE_TAGS for tag in tags)


async def resolve_telegram_channel(channel_name):

    try:
        return await client.get_entity(channel_name)

    except UsernameNotOccupiedError:
        print(
            f"Telegram username '{channel_name}' does not exist."
        )

    except ValueError:
        print(
            f"Unable to resolve Telegram channel '{channel_name}'."
        )

    return None


async def main():

    await client.start()

    db = SessionLocal()

    try:

        for channel_cfg in TARGET_CHANNELS:

            channel_name = channel_cfg["channel_name"]

            print(
                f"\nProcessing channel: {channel_name}"
            )

            try:

                #
                # First validate channel exists in DB
                #
                channel_db = (
                    db.query(Channel)
                    .filter(
                        Channel.channel_name == channel_name
                    )
                    .first()
                )


                if channel_db is None:

                    print(
                        f"Skipping channel '{channel_name}': "
                        "not found in database"
                    )

                    continue


                #
                # Resolve Telegram channel
                #
                telegram_channel = await resolve_telegram_channel(
                    channel_name
                )


                if telegram_channel is None:

                    print(
                        f"Skipping channel '{channel_name}' "
                        "because Telegram entity was not found"
                    )

                    continue


                print(
                    f"Reading {channel_cfg['display_name']}"
                )


                #
                # Message iterator
                #
                if COLLECTOR_MODE == "historical":

                    iterator = client.iter_messages(
                        telegram_channel,
                        reverse=True
                    )

                else:

                    iterator = client.iter_messages(
                        telegram_channel,
                        reverse=True,
                        limit=MESSAGE_LIMIT
                    )


                async for msg in iterator:


                    if (
                        COLLECTOR_MODE == "incremental"
                        and channel_db.last_message_id
                        and msg.id <= channel_db.last_message_id
                    ):
                        continue


                    text = msg.message


                    if not text:
                        continue


                    tags = extract_tags(text)


                    if not is_relevant(tags):
                        continue


                    message = save_message(
                        db=db,
                        channel_id=channel_db.id,
                        telegram_message=msg,
                        tags=tags,
                    )


                    recommendation = save_recommendation(
                        db=db,
                        message=message
                    )


                    if recommendation:

                        print(
                            f"Recommendation created "
                            f"{recommendation.id}"
                        )


                    update_checkpoint(
                        db=db,
                        channel=channel_db,
                        telegram_message=msg,
                    )


                    print(
                        f"Saved Message {message.id}"
                    )


            except Exception as e:

                print(
                    f"Error processing channel '{channel_name}': {e}"
                )

                continue


    finally:

        db.close()



with client:

    client.loop.run_until_complete(main())
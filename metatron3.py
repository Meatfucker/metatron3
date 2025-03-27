import asyncio
import discord
from modules.logger import setup_logger
from modules.settings_loader import SettingsLoader
from modules.discord_client import Metatron3
from modules.avernus_client import AvernusClient
from modules.twitch_client import TwitchEventSubClient

logger = setup_logger("metatron3.log")
settings = SettingsLoader("configs")
url = settings["avernus"]["ip"]
port = settings["avernus"]["port"]
avernus_client = AvernusClient(url, port)
discord_client = Metatron3(avernus_client=avernus_client, intents=discord.Intents.all())
if settings["twitch"]["twitch_enabled"]:
    twitch_client = TwitchEventSubClient(discord_client=discord_client)


async def start_clients():
    """Spin off clients to threads and start them"""
    if settings["twitch"]["twitch_enabled"]:
        await asyncio.gather(
            discord_client.start(settings["discord"]["token"]),  # Start the discord client
            twitch_client.start()
            )
    else:
        await asyncio.gather(discord_client.start(settings["discord"]["token"]))

def run_program():
    """Main startup loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(start_clients())
    except KeyboardInterrupt:
        logger.info("Metatron3 SHUTDOWN")
    finally:
        loop.close()

if __name__ == "__main__":
    run_program()

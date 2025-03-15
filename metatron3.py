import asyncio
import discord
from modules.logger import setup_logger
from modules.settings_loader import SettingsLoader
from modules.discord_client import Metatron3
from modules.avernus_client import AvernusClient

logger = setup_logger("metatron3.log")
settings = SettingsLoader("configs")
avernus_client = AvernusClient(settings["avernus"]["ip"], settings["avernus"]["port"])
discord_client = Metatron3(avernus_client=avernus_client, intents=discord.Intents.all())

async def start_clients():
    """Spin off clients to threads and start them"""
    await asyncio.gather(
        discord_client.start(settings["discord"]["token"])  # Start the discord client
        )

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

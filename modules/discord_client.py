import asyncio
import re
import discord
from loguru import logger
from modules.settings_loader import SettingsLoader
from modules.avernus_client import AvernusClient
from modules.llm_chat import LlmChat
from modules.mtg_card import MTGCardGen, MTGCardGenThreePack


# noinspection PyUnresolvedReferences
class Metatron3(discord.Client):
    """Discord client for Metatron3"""
    def __init__(self, *, avernus_client: AvernusClient, intents: discord.Intents):
        super().__init__(intents=intents)
        self.avernus_client = avernus_client
        self.slash_commands = discord.app_commands.CommandTree(self)
        self.settings = SettingsLoader("configs")
        self.request_queue = asyncio.Queue()
        self.request_queue_concurrency_list = {}
        self.request_currently_processing = False
        self.allowed_mentions = discord.AllowedMentions(everyone=False, replied_user=True, users=True)

    async def setup_hook(self):
        """This loads the various shit before logging in to discord"""
        self.loop.create_task(self.process_request_queue())
        self.slash_commands.add_command(discord.app_commands.Command(
            name="mtg_gen",
            description="This generates satire MTG cards",
            callback=self.mtg_gen
        ))
        self.slash_commands.add_command(discord.app_commands.Command(
            name="mtg_gen_three_pack",
            description="This generates three satire MTG cards",
            callback=self.mtg_gen_three_pack
        ))

    async def on_message(self, message):
        """This captures people talking to the bot in chat and responds."""
        if self.user.mentioned_in(message):
            prompt = re.sub(r'<[^>]+>', '', message.content).lstrip()
            if await self.is_room_in_queue(message.author.id):
                self.request_queue_concurrency_list[message.author.id] += 1
                chat_request = LlmChat(self, prompt, message.channel, message.author)
                await self.request_queue.put(chat_request)
                chat_logger = logger.bind(user=message.author.name, prompt=prompt)
                chat_logger.info("Chat Queued")
            else:
                await message.channel.send("Queue limit has been reached, please wait for your previous gens to finish")

    async def on_ready(self):
        """Prints the bots name to discord and syncs the slash commands"""
        await self.slash_commands.sync()
        on_ready_logger = logger.bind(user=self.user.name, userid=self.user.id)
        on_ready_logger.info("Discord Login Success")

    async def process_request_queue(self):
        """Processes the request queue objects"""
        while True:
            self.request_currently_processing = True
            queue_request = await self.request_queue.get()
            try:
                await queue_request.run()
            except Exception as e:
                self.request_queue_concurrency_list[queue_request.user.id] -= 1
                logger.error(f"Exception: {e}")
            finally:
                self.request_queue_concurrency_list[queue_request.user.id] -= 1
                self.request_queue.task_done()
                self.request_currently_processing = False

    async def is_room_in_queue(self, user_id):
        """This checks the users current number of pending gens against the max,
         and if there is room, returns true, otherwise, false"""
        self.request_queue_concurrency_list.setdefault(user_id, 0)
        user_queue_depth = self.settings["discord"]["max_user_queue"]
        if self.request_queue_concurrency_list[user_id] >= user_queue_depth:
            return False
        return True

    async def mtg_gen(self, interaction: discord.Interaction, prompt: str):
        """This is the slash command to generate a card."""

        mtg_card_request = MTGCardGen(self, prompt, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
            card_queue_logger.info(f'Card Queued')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            await self.request_queue.put(mtg_card_request)
            await interaction.response.send_message('Card Being Created:', ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

    async def mtg_gen_three_pack(self, interaction: discord.Interaction, prompt: str):
        """This is the slash command to generate a card pack."""

        mtg_card_request = MTGCardGenThreePack(self, prompt, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
            card_queue_logger.info(f'Card Pack Queued')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            await self.request_queue.put(mtg_card_request)
            await interaction.response.send_message('Pack Being Created:', ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")
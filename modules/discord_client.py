import asyncio
import json
import os
import re
import discord
from typing import Optional
from loguru import logger
from modules.settings_loader import SettingsLoader
from modules.avernus_client import AvernusClient
from modules.llm_chat import LlmChat
from modules.mtg_card import MTGCardGen, MTGCardGenThreePack
from modules.sdxl import SDXLGen
from modules.flux import FluxGen


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
        await self.register_slash_commands()

    async def on_message(self, message):
        """This captures people talking to the bot in chat and responds."""
        if message.type != discord.MessageType.reply:
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
        if await self.is_user_banned(user_id):
            return False
        self.request_queue_concurrency_list.setdefault(user_id, 0)
        user_queue_depth = self.settings["discord"]["max_user_queue"]
        if self.request_queue_concurrency_list[user_id] >= user_queue_depth:
            return False
        return True

    async def is_user_banned(self, user_id):
        """Checks the users config if they are banned and returns true if they are, else false"""
        file_path = f"configs/users/{user_id}.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                try:
                    user_data = json.load(file)
                    return user_data.get("banned", False)  # Default to False if key is missing
                except json.JSONDecodeError:  # Handle empty or corrupted files
                    return False
        return False  # Return False if file doesn't exist

    async def register_slash_commands(self):
        self.slash_commands.add_command(discord.app_commands.Command(
            name="toggle_user_ban",
            description="Toggles whether a user is banned or not",
            callback=self.toggle_user_ban
        ))
        self.slash_commands.add_command(discord.app_commands.Command(
            name="mtg_gen",
            description="This generates a satire MTG card",
            callback=self.mtg_gen
        ))
        self.slash_commands.add_command(discord.app_commands.Command(
            name="mtg_gen_three_pack",
            description="This generates three satire MTG cards",
            callback=self.mtg_gen_three_pack
        ))
        self.slash_commands.add_command(discord.app_commands.Command(
            name="sdxl_gen",
            description="Generate an image using SDXL",
            callback=self.sdxl_gen
        ))
        self.slash_commands.add_command(discord.app_commands.Command(
            name="flux_gen",
            description="Generate an image using Flux",
            callback=self.flux_gen
        ))

    async def toggle_user_ban(self, interaction: discord.Interaction, user_id: str):
        """Toggles the 'banned' setting for the user in their JSON file.
        If the key exists, it flips its boolean value.
        If it does not exist, it sets 'banned' to True."""
        file_path = f"configs/users/{user_id}.json"
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    try:
                        user_data = json.load(file)
                    except json.JSONDecodeError:  # Handle empty or corrupted files
                        user_data = {}
            else:
                user_data = {}
            # Toggle or set the 'banned' key
            user_data["banned"] = not user_data.get("banned", False)
            # Write back to the file
            with open(file_path, 'w') as file:
                json.dump(user_data, file, indent=4)
            await interaction.response.send_message(f'Ban toggled for user:{user_id} Banned:{user_data["banned"]}',
                                                    ephemeral=True, delete_after=5)
        except Exception as e:
            logger.info(f"Ban exception: {e}")

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

    async def sdxl_gen(self, interaction: discord.Interaction, prompt: str, negative_prompt: Optional[str],
                       width: Optional[int], height: Optional[int], batch_size: Optional[int], lora_name: Optional[str]):
        """This is the slash command to generate SDXL images"""
        sdxl_request = SDXLGen(self,
                               prompt,
                               interaction.channel,
                               interaction.user,
                               negative_prompt=negative_prompt,
                               width=width,
                               height=height,
                               batch_size=batch_size,
                               lora_name=lora_name)

        if await self.is_room_in_queue(interaction.user.id):
            sdxl_queuelogger = logger.bind(user=interaction.user.name, prompt=prompt)
            sdxl_queuelogger.info("SDXL Queued")
            self.request_queue_concurrency_list[interaction.user.id] += 1
            await self.request_queue.put(sdxl_request)
            await interaction.response.send_message("SDXL Image Being Created:", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish")

    async def flux_gen(self, interaction: discord.Interaction, prompt: str, width: Optional[int],
                       height: Optional[int], batch_size: Optional[int], lora_name: Optional[str]):
        """This is the slash command to generate Flux images"""
        flux_request = FluxGen(self,
                               prompt,
                               interaction.channel,
                               interaction.user,
                               width=width,
                               height=height,
                               batch_size=batch_size,
                               lora_name=lora_name)

        if await self.is_room_in_queue(interaction.user.id):
            flux_queuelogger = logger.bind(user=interaction.user.name, prompt=prompt)
            flux_queuelogger.info("Flux Queued")
            self.request_queue_concurrency_list[interaction.user.id] += 1
            await self.request_queue.put(flux_request)
            await interaction.response.send_message("Flux Image Being Created:", ephemeral=True, delete_after=5)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish")

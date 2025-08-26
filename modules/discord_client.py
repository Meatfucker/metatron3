import asyncio
import json
import os
import re
import discord
from typing import Optional
from loguru import logger
from modules.settings_loader import SettingsLoader
from modules.avernus_client import AvernusClient
from modules.llm_chat import LlmChat, LlmChatClear
from modules.mtg_card import MTGCardGen, MTGCardGenThreePack, MTGCardGenFlux, MTGCardGenFluxThreePack
from modules.sdxl import SDXLGen, SDXLGenEnhanced
from modules.flux import FluxGen, FluxGenEnhanced, FluxKontextGen


# noinspection PyUnresolvedReferences
class Metatron3(discord.Client):
    """Discord client for Metatron3"""
    def __init__(self, *, avernus_client: AvernusClient, intents: discord.Intents):
        super().__init__(intents=intents)
        self.avernus_client: AvernusClient = avernus_client
        self.slash_commands: discord.app_commands.CommandTree = discord.app_commands.CommandTree(self)
        self.settings: SettingsLoader = SettingsLoader("configs")
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.request_queue_concurrency_list: dict = {}
        self.request_currently_processing: bool = False
        self.allowed_mentions: discord.AllowedMentions = discord.AllowedMentions(everyone=False, replied_user=True, users=True)
        self.sd_xl_models_choices: list = []
        self.sd_xl_loras_choices: list = []
        self.sd_xl_controlnet_choices: list = []
        self.flux_loras_choices: list = []

    async def setup_hook(self):
        """This loads the various shit before logging in to discord"""
        avernus_status = await self.avernus_client.check_status()
        avernus_status_logger = logger.bind(status=avernus_status)
        avernus_status_logger.info("Avernus")
        await self.build_discord_choices()
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
            queue_request = await self.request_queue.get()
            try:
                self.request_currently_processing = True
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

    async def get_queue_depth(self):
        if self.request_currently_processing is True:
            size = int(self.request_queue.qsize()) + 1
        else:
            size = int(self.request_queue.qsize())
        return size

    @staticmethod
    async def is_user_banned(user_id):
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

    async def build_discord_choices(self):
        sd_xl_loras_list = await self.avernus_client.list_sdxl_loras()  # get the list of available loras to build the interface with
        for lora in sd_xl_loras_list:
            self.sd_xl_loras_choices.append(discord.app_commands.Choice(name=lora, value=lora))

        sd_xl_controlnets_list = await self.avernus_client.list_sdxl_controlnets()
        for controlnet in sd_xl_controlnets_list:
            self.sd_xl_controlnet_choices.append(discord.app_commands.Choice(name=controlnet, value=controlnet))

        flux_loras_list = await self.avernus_client.list_flux_loras()  # get the list of available loras to build the interface with
        for lora in flux_loras_list:
            self.flux_loras_choices.append(discord.app_commands.Choice(name=lora, value=lora))

        for model in self.settings["avernus"]["sdxl_models_list"]:
            self.sd_xl_models_choices.append(discord.app_commands.Choice(name=model, value=model))


    async def register_slash_commands(self):
        toggle_user_ban_command = discord.app_commands.Command(name="toggle_user_ban",
                                                               description="Toggles whether a user is banned or not",
                                                               callback=self.toggle_user_ban)
        clear_chat_command = discord.app_commands.Command(name="clear_chat_history",
                                                          description="Clears the users chat history with the LLM",
                                                          callback=self.clear_chat_history)
        mtg_command = discord.app_commands.Command(name="mtg_gen",
                                                   description="This generates a satire MTG card",
                                                   callback=self.mtg_gen)
        mtg_three_pack_command = discord.app_commands.Command(name="mtg_gen_three_pack",
                                                              description="This generates three satire MTG cards",
                                                              callback=self.mtg_gen_three_pack)
        mtx_flux_command = discord.app_commands.Command(name="mtg_flux_gen",
                                                        description="This generates a satire Flux MTG card",
                                                        callback=self.mtg_flux_gen)
        mtg_flux_three_pack_command = discord.app_commands.Command(name="mtg_gen_flux_three_pack",
                                                              description="This generates three satire Flux MTG cards",
                                                              callback=self.mtg_gen_flux_three_pack)
        sdxl_command = discord.app_commands.Command(name="sdxl_gen",
                                                    description="Generate an image using SDXL",
                                                    callback=self.sdxl_gen)
        sdxl_command._params["model_name"].choices = self.sd_xl_models_choices
        sdxl_command._params["lora_name"].choices = self.sd_xl_loras_choices
        sdxl_command._params["control_processor"].choices = self.sd_xl_controlnet_choices
        flux_command = discord.app_commands.Command(name="flux_gen",
                                                    description="Generate an image using Flux",
                                                    callback=self.flux_gen)
        flux_command._params["lora_name"].choices = self.flux_loras_choices
        kontext_command = discord.app_commands.Command(name="kontext_gen",
                                                    description="Edit an image using Kontext",
                                                    callback=self.kontext_gen)
        kontext_command._params["lora_name"].choices = self.flux_loras_choices
        self.slash_commands.add_command(toggle_user_ban_command)
        self.slash_commands.add_command(clear_chat_command)
        self.slash_commands.add_command(mtg_command)
        self.slash_commands.add_command(mtg_three_pack_command)
        self.slash_commands.add_command(mtx_flux_command)
        self.slash_commands.add_command(mtg_flux_three_pack_command)
        self.slash_commands.add_command(sdxl_command)
        self.slash_commands.add_command(flux_command)
        self.slash_commands.add_command(kontext_command)

    @staticmethod
    async def toggle_user_ban(interaction: discord.Interaction, user_id: str):
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

    async def clear_chat_history(self, interaction: discord.Interaction):
        """Clears a users saved llm chat history"""

        clear_chat_request = LlmChatClear(self, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            clear_chat_queue_logger = logger.bind(user=interaction.user.name)
            clear_chat_queue_logger.info(f'Chat History Cleared')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Clearing chat history: {size} requests in queue ahead of you.", ephemeral=True
            )
            await self.request_queue.put(clear_chat_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )


    async def mtg_gen(self, interaction: discord.Interaction, prompt: str):
        """This is the slash command to generate a card."""

        mtg_card_request = MTGCardGen(self, prompt, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
            card_queue_logger.info(f'Card Queued')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Card Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(mtg_card_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

    async def mtg_flux_gen(self, interaction: discord.Interaction, prompt: str):
        """This is the slash command to generate a card."""

        mtg_card_request = MTGCardGenFlux(self, prompt, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
            card_queue_logger.info(f'Flux Card Queued')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Flux Card Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(mtg_card_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

    async def mtg_gen_three_pack(self, interaction: discord.Interaction, prompt: str):
        """This is the slash command to generate a card pack."""

        mtg_card_request = MTGCardGenThreePack(self, prompt, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
            card_queue_logger.info(f'Card Pack Queued')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Pack Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(mtg_card_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

    async def mtg_gen_flux_three_pack(self, interaction: discord.Interaction, prompt: str):
        """This is the slash command to generate a card pack."""

        mtg_card_request = MTGCardGenFluxThreePack(self, prompt, interaction.channel, interaction.user)

        if await self.is_room_in_queue(interaction.user.id):
            card_queue_logger = logger.bind(user=interaction.user.name, prompt=prompt)
            card_queue_logger.info(f'Flux Card Pack Queued')
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Pack Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(mtg_card_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

    async def sdxl_gen(self,
                       interaction: discord.Interaction,
                       prompt: str,
                       negative_prompt: Optional[str],
                       width: Optional[int],
                       height: Optional[int],
                       enhance_prompt: Optional[bool],
                       lora_name: Optional[str],
                       model_name: Optional[str],
                       i2i_image: Optional[discord.Attachment],
                       i2i_strength: Optional[float],
                       ipadapter_image: Optional[discord.Attachment],
                       ipadapter_strength: Optional[float],
                       control_processor: Optional[str],
                       control_image: Optional[discord.Attachment],
                       control_strength: Optional[float],
                       guidance_scale: Optional[float],
                       batch_size: Optional[int] = 4,):
        """This is the slash command to generate SDXL images

        This generates images using the SDXL pipeline

        Args:
            prompt (str): What you want to generate
            negative_prompt (str): Default=None: Things you dont want in the image"
            width (int): Default=1024: How many pixels wide you want the image
            height (int): Default=1024: How many pixels tall you want the image
            enhance_prompt (bool): Default=False: Whether to use a LLM to enhance your prompt
            lora_name: Default=None: What optional lora to use
            model_name: What model to use to generate with
            i2i_image: An image to use as a base for generation
            i2i_strength: Default=0.7: A number between 0-1 that represents the percent of pixels to replace in the i2i_image
            ipadapter_image: An image to extract a style or contents from.
            ipadapter_strength: Default=0.6: A number between 0-1 that represents the strength of the extracted style
            control_processor: Which controlnet processor to use on the controlnet image
            control_image: An image to supply to the controlnet processor
            control_strength: Default=0.5: A number between 0-1 representing the balance between the controlnet and the generation. 0.5 being equally balanced
            guidance_scale: Default=5.0: A floating point number altering the strength of classifier free guidance. Higher numbers will listen to the prompt better but will cook the image.
            batch_size: Default=4: How many images to gen at once. More images take longer and can potentially crash

        Returns:
            A list containing the generated images
        """
        if i2i_image:
            if "image" not in i2i_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return
        if ipadapter_image:
            if "image" not in ipadapter_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return
        if control_image:
            if "image" not in control_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return
        if enhance_prompt:
            sdxl_request = SDXLGenEnhanced(self,
                                           prompt,
                                           interaction.channel,
                                           interaction.user,
                                           negative_prompt=negative_prompt,
                                           width=width,
                                           height=height,
                                           batch_size=batch_size,
                                           lora_name=lora_name,
                                           model_name=model_name,
                                           i2i_image=i2i_image,
                                           strength=i2i_strength,
                                           ipadapter_image=ipadapter_image,
                                           ipadapter_strength=ipadapter_strength,
                                           control_processor=control_processor,
                                           control_image=control_image,
                                           control_strength=control_strength,
                                           guidance_scale=guidance_scale)
        else:
            sdxl_request = SDXLGen(self,
                                   prompt,
                                   interaction.channel,
                                   interaction.user,
                                   negative_prompt=negative_prompt,
                                   width=width,
                                   height=height,
                                   batch_size=batch_size,
                                   lora_name=lora_name,
                                   model_name=model_name,
                                   i2i_image=i2i_image,
                                   strength=i2i_strength,
                                   ipadapter_image=ipadapter_image,
                                   ipadapter_strength=ipadapter_strength,
                                   control_processor=control_processor,
                                   control_image=control_image,
                                   control_strength=control_strength,
                                   guidance_scale=guidance_scale)

        if await self.is_room_in_queue(interaction.user.id):
            sdxl_queuelogger = logger.bind(user=interaction.user.name, prompt=prompt)
            sdxl_queuelogger.info("SDXL Queued")
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"SDXL Image Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(sdxl_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

    async def flux_gen(self,
                       interaction: discord.Interaction,
                       prompt: str,
                       width: Optional[int],
                       height: Optional[int],
                       lora_name: Optional[str],
                       enhance_prompt: Optional[bool],
                       i2i_image: Optional[discord.Attachment],
                       i2i_strength: Optional[float],
                       ipadapter_image: Optional[discord.Attachment],
                       ipadapter_strength: Optional[float],
                       batch_size: Optional[int] = 4):
        """This is the slash command to generate Flux images"""
        if i2i_image:
            if "image" not in i2i_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return
        if ipadapter_image:
            if "image" not in ipadapter_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return

        if enhance_prompt:
            flux_request = FluxGenEnhanced(self,
                                           prompt,
                                           interaction.channel,
                                           interaction.user,
                                           width=width,
                                           height=height,
                                           batch_size=batch_size,
                                           lora_name=lora_name,
                                           i2i_image=i2i_image,
                                           strength=i2i_strength,
                                           ipadapter_image=ipadapter_image,
                                           ipadapter_strength=ipadapter_strength)
        else:
            flux_request = FluxGen(self,
                                   prompt,
                                   interaction.channel,
                                   interaction.user,
                                   width=width,
                                   height=height,
                                   batch_size=batch_size,
                                   lora_name=lora_name,
                                   i2i_image=i2i_image,
                                   strength=i2i_strength,
                                   ipadapter_image=ipadapter_image,
                                   ipadapter_strength=ipadapter_strength)

        if await self.is_room_in_queue(interaction.user.id):
            flux_queuelogger = logger.bind(user=interaction.user.name, prompt=prompt)
            flux_queuelogger.info("Flux Queued")
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Flux Image Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(flux_request)

        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

    async def kontext_gen(self,
                          interaction: discord.Interaction,
                          prompt: str,
                          i2i_image: discord.Attachment,
                          width: Optional[int],
                          height: Optional[int],
                          lora_name: Optional[str],
                          i2i_strength: Optional[float],
                          ipadapter_image: Optional[discord.Attachment],
                          ipadapter_strength: Optional[float],
                          batch_size: Optional[int] = 1):
        """This is the slash command to generate Flux images"""
        if i2i_image:
            if "image" not in i2i_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return
        if ipadapter_image:
            if "image" not in ipadapter_image.content_type:
                await interaction.response.send_message("Please choose a valid image", ephemeral=True, delete_after=5)
                return

        flux_request = FluxKontextGen(self,
                                      prompt,
                                      interaction.channel,
                                      interaction.user,
                                      width=width,
                                      height=height,
                                      batch_size=batch_size,
                                      lora_name=lora_name,
                                      i2i_image=i2i_image,
                                      strength=i2i_strength,
                                      ipadapter_image=ipadapter_image,
                                      ipadapter_strength=ipadapter_strength)

        if await self.is_room_in_queue(interaction.user.id):
            flux_queuelogger = logger.bind(user=interaction.user.name, prompt=prompt)
            flux_queuelogger.info("Kontext Queued")
            self.request_queue_concurrency_list[interaction.user.id] += 1
            size = await self.get_queue_depth()
            await interaction.response.send_message(
                f"Kontext Image Being Created: {size} requests in queue ahead of you", ephemeral=True
            )
            await self.request_queue.put(flux_request)

        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

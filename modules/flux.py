import base64
import io
import re
import discord
from loguru import logger
from modules.settings_loader import SettingsLoader

class FluxGen:
    """This is the queue object for flux generations"""
    def __init__(self,
                 discord_client,
                 prompt,
                 channel,
                 user,
                 width,
                 height,
                 lora_name=None,
                 batch_size=1):
        self.settings = SettingsLoader("configs")
        self.discord_client = discord_client
        self.avernus_client = discord_client.avernus_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.width = width
        self.height = height
        self.lora_name = lora_name
        self.batch_size = batch_size

        if self.batch_size > 10:
            self.batch_size = 10

    async def run(self):
        if self.lora_name:
            base64_images = await self.avernus_client.flux_image(self.prompt,
                                                                 batch_size=self.batch_size,
                                                                 width=self.width,
                                                                 height=self.height,
                                                                 lora_name=self.lora_name)
        else:
            base64_images = await self.avernus_client.flux_image(self.prompt,
                                                                 batch_size=self.batch_size,
                                                                 width=self.width,
                                                                 height=self.height)
        images = await self.base64_to_pil_images(base64_images)
        files = await self.images_to_discord_files(images)
        await self.channel.send(
            content=f"Flux Gen for {self.user.mention}: Prompt: `{self.prompt}`",
            files=files,
            view=FluxButtons(self.discord_client,
                             self.prompt,
                             self.channel,
                             self.user,
                             self.width,
                             self.height,
                             self.lora_name,
                             self.batch_size))

        sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
        sdxl_logger.info("Flux Success")


    async def images_to_discord_files(self, images):
        """Takes a list of images or image objects and returns a list of discord file objects"""
        discord_files = []
        for image in images:
            discord_file = discord.File(image, filename=f'{self.prompt[:20]}.png')
            discord_files.append(discord_file)

        return discord_files

    @staticmethod
    async def base64_to_pil_images(base64_images):
        """Converts a list of base64 images into a list of file-like objects."""
        image_files = []
        for base64_image in base64_images:
            img_data = base64.b64decode(base64_image)  # Decode base64 string
            img_file = io.BytesIO(img_data)  # Convert to file-like object
            image_files.append(img_file)

        return image_files


class FluxGenEnhanced(FluxGen):
    async def run(self):
        enhanced_prompt = await self.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
        if self.lora_name:
            base64_images = await self.avernus_client.flux_image(enhanced_prompt,
                                                                                batch_size=self.batch_size,
                                                                                width=self.width,
                                                                                height=self.height,
                                                                                lora_name=self.lora_name)
        else:
            base64_images = await self.avernus_client.flux_image(enhanced_prompt,
                                                                                batch_size=self.batch_size,
                                                                                width=self.width,
                                                                                height=self.height,
                                                                                )
        images = await self.base64_to_pil_images(base64_images)
        files = await self.images_to_discord_files(images)
        await self.channel.send(
            content=f"Flux Gen for: {self.user.mention} Prompt:`{self.prompt}` Enhanced Prompt:`{enhanced_prompt}`",
            files=files,
            view=FluxEnhancedButtons(self.discord_client,
                                     self.prompt,
                                     self.channel,
                                     self.user,
                                     self.width,
                                     self.height,
                                     self.lora_name,
                                     self.batch_size))

        sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
        sdxl_logger.info("Flux Success")

class FluxButtons(discord.ui.View):
    """Class for the ui buttons on /flux_gen"""
    def __init__(self,
                 discord_client,
                 prompt,
                 channel,
                 user,
                 width,
                 height,
                 lora_name=None,
                 batch_size=4):
        super().__init__()
        self.timeout = None  # Disables the timeout on the buttons
        self.discord_client = discord_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.width = width
        self.height = height
        self.lora_name = lora_name
        self.batch_size = batch_size

    @discord.ui.button(label='Reroll', emoji="🎲", style=discord.ButtonStyle.grey)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rerolls last Flux gen"""
        if self.user.id == interaction.user.id:
            if await self.discord_client.is_room_in_queue(self.user.id):
                flux_request = FluxGen(self.discord_client,
                                       self.prompt,
                                       self.channel,
                                       self.user,
                                       width=self.width,
                                       height=self.height,
                                       batch_size=self.batch_size,
                                       lora_name=self.lora_name)
                await interaction.response.send_message("Rerolling...", ephemeral=True, delete_after=5)
                flux_queuelogger = logger.bind(user=self.user.name, prompt=self.prompt)
                flux_queuelogger.info("Flux Queued")
                self.discord_client.request_queue_concurrency_list[self.user.id] += 1
                await self.discord_client.request_queue.put(flux_request)
            else:
                await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

    @discord.ui.button(label='Mail', emoji="✉", style=discord.ButtonStyle.grey)
    async def dmimage(self, interaction: discord.Interaction, button: discord.ui.Button):
        """DMs Flux Image"""
        await interaction.response.send_message("DM'ing image...", ephemeral=True, delete_after=5)
        sanitized_prompt = re.sub(r'[^\w\s\-.]', '', self.prompt)[:100]
        files = []
        for file in interaction.message.attachments:
            image_bytes = await file.read()
            attachment = discord.File(io.BytesIO(image_bytes), filename=f'{sanitized_prompt}.png')
            files.append(attachment)
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send(content=self.prompt, files=files)
        image_dm_logger = logger.bind(user=interaction.user.name, userid=interaction.user.id)
        image_dm_logger.success("Flux DM successful")

    @discord.ui.button(label='Delete', emoji="❌", style=discord.ButtonStyle.grey)
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deletes message"""
        if self.user.id == interaction.user.id:
            await interaction.message.delete()
        await interaction.response.send_message("Image deleted.", ephemeral=True, delete_after=5)
        speak_delete_logger = logger.bind(user=interaction.user.name, userid=interaction.user.id)
        speak_delete_logger.info("Flux Delete")

class FluxEnhancedButtons(FluxButtons):
    """Class for the prompt enhanced ui buttons on /flux_gen"""
    @discord.ui.button(label='Reroll', emoji="🎲", style=discord.ButtonStyle.grey)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rerolls last flux enhanced gen"""
        if self.user.id == interaction.user.id:
            if await self.discord_client.is_room_in_queue(self.user.id):
                flux_request = FluxGenEnhanced(self.discord_client,
                                               self.prompt,
                                               self.channel,
                                               self.user,
                                               width=self.width,
                                               height=self.height,
                                               batch_size=self.batch_size,
                                               lora_name=self.lora_name)
                await interaction.response.send_message("Rerolling...", ephemeral=True, delete_after=5)
                flux_queuelogger = logger.bind(user=self.user.name, prompt=self.prompt)
                flux_queuelogger.info("Flux Queued")
                self.discord_client.request_queue_concurrency_list[self.user.id] += 1
                await self.discord_client.request_queue.put(flux_request)
            else:
                await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

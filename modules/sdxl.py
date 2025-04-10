import base64
import io
import re
import discord
from loguru import logger
from modules.settings_loader import SettingsLoader

class SDXLGen:
    """This is the queue object for sdxl generations"""
    def __init__(self,
                 discord_client,
                 prompt,
                 channel,
                 user,
                 width,
                 height,
                 negative_prompt=None,
                 lora_name=None,
                 batch_size=None,
                 model_name=None,
                 i2i_image=None,
                 strength=None):
        self.settings = SettingsLoader("configs")
        self.discord_client = discord_client
        self.avernus_client = discord_client.avernus_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.negative_prompt = negative_prompt
        self.width = width
        self.height = height
        self.lora_name = lora_name
        self.batch_size = batch_size if batch_size is not None else 4
        if self.batch_size > 10:
            self.batch_size = 10
        self.model_name = model_name
        self.i2i_image = i2i_image
        self.i2i_image_base64 = None
        self.strength = strength

    async def run(self):
        kwargs = {"prompt": self.prompt,
                  "negative_prompt": self.negative_prompt,
                  "width": self.width,
                  "height": self.height,
                  }
        if self.batch_size:
            kwargs["batch_size"] = self.batch_size
        if self.lora_name:
            kwargs["lora_name"] = self.lora_name
        if self.model_name:
            kwargs["model_name"] = self.model_name
        if self.i2i_image:
            self.i2i_image_base64 = await self.image_to_base64(self.i2i_image)
            kwargs["image"] = self.i2i_image_base64
        if self.strength:
            kwargs["strength"] = self.strength
        base64_images = await self.avernus_client.sdxl_image(**kwargs)
        images = await self.base64_to_pil_images(base64_images)
        files = await self.images_to_discord_files(images)
        await self.channel.send(
            content=f"SDXL Gen for {self.user.mention}: Prompt: `{self.prompt}`",
            files=files,
            view=SDXLButtons(self.discord_client,
                             self.prompt,
                             self.channel,
                             self.user,
                             self.width,
                             self.height,
                             self.negative_prompt,
                             self.lora_name,
                             self.model_name,
                             self.i2i_image,
                             self.strength,
                             self.batch_size))
        sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
        sdxl_logger.info("SDXL Success")

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

    @staticmethod
    async def image_to_base64(image):
        buffered = io.BytesIO()
        await image.save(buffered)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


class SDXLGenEnhanced(SDXLGen):
    async def run(self):
        enhanced_prompt = await self.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
        kwargs = {"prompt": self.prompt,
                  "negative_prompt": self.negative_prompt,
                  "width": self.width,
                  "height": self.height,
                  "batch_size": self.batch_size}
        if self.lora_name:
            kwargs["lora_name"] = self.lora_name
        if self.model_name:
            kwargs["model_name"] = self.model_name
        if self.i2i_image:
            self.i2i_image_base64 = await self.image_to_base64(self.i2i_image)
            kwargs["image"] = self.i2i_image_base64
        if self.strength:
            kwargs["strength"] = self.strength
        base64_images = await self.avernus_client.sdxl_image(**kwargs)
        images = await self.base64_to_pil_images(base64_images)
        files = await self.images_to_discord_files(images)
        await self.channel.send(
            content=f"SDXL Gen for:`{self.user}` Prompt:`{self.prompt}` Enhanced Prompt:`{enhanced_prompt}`",
            files=files,
            view=SDXLEnhancedButtons(self.discord_client,
                                     self.prompt,
                                     self.channel,
                                     self.user,
                                     self.width,
                                     self.height,
                                     self.negative_prompt,
                                     self.lora_name,
                                     self.model_name,
                                     self.i2i_image,
                                     self.strength,
                                     self.batch_size))
        sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
        sdxl_logger.info("SDXL Success")


class SDXLButtons(discord.ui.View):
    """Class for the ui buttons on /sdxl_gen"""
    def __init__(self,
                 discord_client,
                 prompt,
                 channel,
                 user,
                 width,
                 height,
                 negative_prompt=None,
                 lora_name=None,
                 model_name=None,
                 i2i_image=None,
                 strength=None,
                 batch_size=4):
        super().__init__()
        self.timeout = None  # Disables the timeout on the buttons
        self.discord_client = discord_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.negative_prompt = negative_prompt
        self.width = width
        self.height = height
        self.lora_name = lora_name
        self.batch_size = batch_size
        self.model_name = model_name
        self.i2i_image = i2i_image
        self.strength = strength

    @discord.ui.button(label='Reroll', emoji="🎲", style=discord.ButtonStyle.grey)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rerolls last SDXL gen"""
        if self.user.id == interaction.user.id:
            if await self.discord_client.is_room_in_queue(self.user.id):
                sdxl_request = SDXLGen(self.discord_client,
                                       self.prompt,
                                       self.channel,
                                       self.user,
                                       negative_prompt=self.negative_prompt,
                                       width=self.width,
                                       height=self.height,
                                       batch_size=self.batch_size,
                                       lora_name=self.lora_name,
                                       model_name=self.model_name,
                                       i2i_image=self.i2i_image,
                                       strength=self.strength)
                await interaction.response.send_message("Rerolling...", ephemeral=True, delete_after=5)
                sdxl_queuelogger = logger.bind(user=self.user.name, prompt=self.prompt)
                sdxl_queuelogger.info("SDXL Queued")
                self.discord_client.request_queue_concurrency_list[self.user.id] += 1
                await self.discord_client.request_queue.put(sdxl_request)
            else:
                await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

    @discord.ui.button(label='Mail', emoji="✉", style=discord.ButtonStyle.grey)
    async def dmimage(self, interaction: discord.Interaction, button: discord.ui.Button):
        """DMs SDXL Image"""
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
        image_dm_logger.success("SDXL DM successful")

    @discord.ui.button(label='Delete', emoji="❌", style=discord.ButtonStyle.grey)
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deletes message"""
        if self.user.id == interaction.user.id:
            await interaction.message.delete()
        await interaction.response.send_message("Image deleted.", ephemeral=True, delete_after=5)
        speak_delete_logger = logger.bind(user=interaction.user.name, userid=interaction.user.id)
        speak_delete_logger.info("IMAGEGEN Delete")

class SDXLEnhancedButtons(SDXLButtons):
    """Class for the prompt enhanced ui buttons on /sdxl_gen"""
    @discord.ui.button(label='Reroll', emoji="🎲", style=discord.ButtonStyle.grey)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rerolls last SDXL enhanced gen"""
        if self.user.id == interaction.user.id:
            if await self.discord_client.is_room_in_queue(self.user.id):
                sdxl_request = SDXLGenEnhanced(self.discord_client,
                                               self.prompt,
                                               self.channel,
                                               self.user,
                                               negative_prompt=self.negative_prompt,
                                               width=self.width,
                                               height=self.height,
                                               batch_size=self.batch_size,
                                               lora_name=self.lora_name,
                                               model_name=self.model_name,
                                               i2i_image=self.i2i_image,
                                               strength=self.strength)
                await interaction.response.send_message("Rerolling...", ephemeral=True, delete_after=5)
                sdxl_queuelogger = logger.bind(user=self.user.name, prompt=self.prompt)
                sdxl_queuelogger.info("SDXL Queued")
                self.discord_client.request_queue_concurrency_list[self.user.id] += 1
                await self.discord_client.request_queue.put(sdxl_request)
            else:
                await interaction.response.send_message("Queue limit reached, please wait until your current gen or gens finish")

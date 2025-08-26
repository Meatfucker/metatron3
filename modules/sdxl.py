import base64
import io
import re
import time
import discord
from loguru import logger
from PIL import Image
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
                 strength=None,
                 ipadapter_image=None,
                 ipadapter_strength=None,
                 control_processor=None,
                 control_image=None,
                 control_strength=None,
                 guidance_scale=None):
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
        self.ipadapter_image = ipadapter_image
        self.ipadapter_image_base64 = None
        self.ipadapter_strength = ipadapter_strength
        self.control_processor = control_processor
        self.control_image = control_image
        self.control_image_base64 = None
        self.control_strength = control_strength
        self.guidance_scale = guidance_scale

    async def run(self):
        start_time = time.time()
        try:
            kwargs = {"prompt": self.prompt,
                      "negative_prompt": self.negative_prompt}
            if self.height:
                kwargs["height"] = self.height
            else:
                kwargs["height"] = 1024
            if self.width:
                kwargs["width"] = self.width
            else:
                kwargs["width"] = 1024
            if self.batch_size:
                kwargs["batch_size"] = self.batch_size
            if self.lora_name:
                kwargs["lora_name"] = self.lora_name
            if self.model_name:
                kwargs["model_name"] = self.model_name
            if self.i2i_image:
                self.i2i_image_base64 = await self.image_to_base64(self.i2i_image, kwargs["width"], kwargs["height"])
                kwargs["image"] = self.i2i_image_base64
            if self.strength:
                kwargs["strength"] = self.strength
            if self.ipadapter_image:
                self.ipadapter_image_base64 = await self.image_to_base64(self.ipadapter_image, kwargs["width"], kwargs["height"])
                kwargs["ip_adapter_image"] = self.ipadapter_image_base64
            if self.ipadapter_strength:
                kwargs["ip_adapter_strength"] = self.ipadapter_strength
            if self.control_image:
                self.control_image_base64 = await self.image_to_base64(self.control_image, kwargs["width"], kwargs["height"])
                kwargs["controlnet_image"] = self.control_image_base64
            if self.control_processor:
                kwargs["controlnet_processor"] = self.control_processor
            if self.control_strength:
                kwargs["controlnet_strength"] = self.control_strength
            if self.guidance_scale:
                kwargs["guidance_scale"] = self.guidance_scale

            base64_images = await self.avernus_client.sdxl_image(**kwargs)
            images = await self.base64_to_pil_images(base64_images)
            files = await self.images_to_discord_files(images)
            end_time = time.time()
            elapsed_time = end_time - start_time
            try:
                await self.channel.send(
                    content=f"SDXL Gen for {self.user.mention}: Prompt: `{self.prompt}` Lora: `{self.lora_name}` Time:`{elapsed_time:.2f} seconds`",
                    files=files,
                    view=SDXLButtons(discord_client=self.discord_client,
                                     prompt=self.prompt,
                                     channel=self.channel,
                                     user=self.user,
                                     width=self.width,
                                     height=self.height,
                                     negative_prompt=self.negative_prompt,
                                     lora_name=self.lora_name,
                                     model_name=self.model_name,
                                     i2i_image=self.i2i_image,
                                     strength=self.strength,
                                     batch_size=self.batch_size,
                                     ipadapter_image=self.ipadapter_image,
                                     ipadapter_strength=self.ipadapter_strength,
                                     control_image=self.control_image,
                                     control_processor=self.control_processor,
                                     control_strength=self.control_strength,
                                     guidance_scale=self.guidance_scale))
            except Exception as e:
                logger.error(f"CHANNEL SEND ERROR: {e}")
            sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
            sdxl_logger.info("SDXL Success")
        except Exception as e:
            await self.channel.send(f"{self.user.mention} SDXL Error: {e}")
            sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
            sdxl_logger.error(f"SDXL ERROR: {e}")

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
    async def image_to_base64(image, width, height):
        attachment_buffer = io.BytesIO()
        await image.save(attachment_buffer)
        image = Image.open(attachment_buffer)
        image = image.convert("RGB")
        image = image.resize((width, height))
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


class SDXLGenEnhanced(SDXLGen):
    async def run(self):
        start_time = time.time()
        try:
            enhanced_prompt = await self.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            kwargs = {"prompt": self.prompt,
                      "negative_prompt": self.negative_prompt}
            if self.height:
                kwargs["height"] = self.height
            else:
                kwargs["height"] = 1024
            if self.width:
                kwargs["width"] = self.width
            else:
                kwargs["width"] = 1024
            if self.batch_size:
                kwargs["batch_size"] = self.batch_size
            if self.lora_name:
                kwargs["lora_name"] = self.lora_name
            if self.model_name:
                kwargs["model_name"] = self.model_name
            if self.i2i_image:
                self.i2i_image_base64 = await self.image_to_base64(self.i2i_image, kwargs["width"], kwargs["height"])
                kwargs["image"] = self.i2i_image_base64
            if self.strength:
                kwargs["strength"] = self.strength
            if self.ipadapter_image:
                self.ipadapter_image_base64 = await self.image_to_base64(self.ipadapter_image, kwargs["width"], kwargs["height"])
                kwargs["ip_adapter_image"] = self.ipadapter_image_base64
            if self.ipadapter_strength:
                kwargs["ip_adapter_strength"] = self.ipadapter_strength
            if self.control_image:
                self.control_image_base64 = await self.image_to_base64(self.control_image, kwargs["width"], kwargs["height"])
                kwargs["controlnet_image"] = self.control_image_base64
            if self.control_processor:
                kwargs["controlnet_processor"] = self.control_processor
            if self.control_strength:
                kwargs["controlnet_strength"] = self.control_strength
            if self.guidance_scale:
                kwargs["guidance_scale"] = self.guidance_scale

            base64_images = await self.avernus_client.sdxl_image(**kwargs)
            images = await self.base64_to_pil_images(base64_images)
            files = await self.images_to_discord_files(images)
            end_time = time.time()
            elapsed_time = end_time - start_time
            await self.channel.send(
                content=f"SDXL Gen for:`{self.user}` Prompt:`{self.prompt}` Enhanced Prompt:`{enhanced_prompt}` Lora: `{self.lora_name}` Time:`{elapsed_time:.2f} seconds`",
                files=files,
                view=SDXLEnhancedButtons(discord_client=self.discord_client,
                                         prompt=self.prompt,
                                         channel=self.channel,
                                         user=self.user,
                                         width=self.width,
                                         height=self.height,
                                         negative_prompt=self.negative_prompt,
                                         lora_name=self.lora_name,
                                         model_name=self.model_name,
                                         i2i_image=self.i2i_image,
                                         strength=self.strength,
                                         batch_size=self.batch_size,
                                         ipadapter_image=self.ipadapter_image,
                                         ipadapter_strength=self.ipadapter_strength,
                                         control_image=self.control_image,
                                         control_processor=self.control_processor,
                                         control_strength=self.control_strength,
                                         guidance_scale=self.guidance_scale))
            sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
            sdxl_logger.info("SDXL Success")
        except Exception as e:
            await self.channel.send(f"{self.user.mention} SDXL Error: {e}")
            sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
            sdxl_logger.error(f"SDXL ERROR: {e}")


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
                 batch_size=4,
                 ipadapter_image=None,
                 ipadapter_strength=None,
                 control_processor=None,
                 control_image=None,
                 control_strength=None,
                 guidance_scale=None):
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
        self.ipadapter_image = ipadapter_image
        self.ipadapter_strength = ipadapter_strength
        self.control_processor = control_processor
        self.control_image = control_image
        self.control_strength = control_strength
        self.guidance_scale = guidance_scale

    @discord.ui.button(label='Reroll', emoji="🎲", style=discord.ButtonStyle.grey)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rerolls last SDXL gen"""
        if await self.discord_client.is_room_in_queue(interaction.user.id):
            sdxl_request = SDXLGen(self.discord_client,
                                   self.prompt,
                                   self.channel,
                                   interaction.user,
                                   negative_prompt=self.negative_prompt,
                                   width=self.width,
                                   height=self.height,
                                   batch_size=self.batch_size,
                                   lora_name=self.lora_name,
                                   model_name=self.model_name,
                                   i2i_image=self.i2i_image,
                                   strength=self.strength,
                                   ipadapter_image=self.ipadapter_image,
                                   ipadapter_strength=self.ipadapter_strength,
                                   control_image=self.control_image,
                                   control_processor=self.control_processor,
                                   control_strength=self.control_strength,
                                   guidance_scale=self.guidance_scale)
            await interaction.response.send_message(
                f"Rerolling: {self.discord_client.request_queue.qsize()} requests in queue ahead of you.",
                ephemeral=True
            )
            sdxl_queuelogger = logger.bind(user=interaction.user.name, prompt=self.prompt)
            sdxl_queuelogger.info("SDXL Queued")
            self.discord_client.request_queue_concurrency_list[interaction.user.id] += 1
            await self.discord_client.request_queue.put(sdxl_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

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
        if await self.discord_client.is_room_in_queue(interaction.user.id):
            sdxl_request = SDXLGenEnhanced(self.discord_client,
                                           self.prompt,
                                           self.channel,
                                           interaction.user,
                                           negative_prompt=self.negative_prompt,
                                           width=self.width,
                                           height=self.height,
                                           batch_size=self.batch_size,
                                           lora_name=self.lora_name,
                                           model_name=self.model_name,
                                           i2i_image=self.i2i_image,
                                           strength=self.strength,
                                           ipadapter_image=self.ipadapter_image,
                                           ipadapter_strength=self.ipadapter_strength,
                                           control_image=self.control_image,
                                           control_processor=self.control_processor,
                                           control_strength=self.control_strength,
                                           guidance_scale=self.guidance_scale)
            await interaction.response.send_message(
                f"Rerolling: {self.discord_client.request_queue.qsize()} requests in queue ahead of you.",
                ephemeral=True
            )
            sdxl_queuelogger = logger.bind(user=interaction.user.name, prompt=self.prompt)
            sdxl_queuelogger.info("SDXL Queued")
            self.discord_client.request_queue_concurrency_list[interaction.user.id] += 1
            await self.discord_client.request_queue.put(sdxl_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True
            )

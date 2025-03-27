import base64
import io
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
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.width = width
        self.height = height
        self.lora_name = lora_name
        self.batch_size = batch_size

    async def run(self):
        if self.lora_name:
            base64_images = await self.discord_client.avernus_client.flux_image(self.prompt,
                                                                                batch_size=self.batch_size,
                                                                                width=self.width,
                                                                                height=self.height,
                                                                                lora_name=self.lora_name)
        else:
            base64_images = await self.discord_client.avernus_client.flux_image(self.prompt,
                                                                                batch_size=self.batch_size,
                                                                                width=self.width,
                                                                                height=self.height,
                                                                                )
        images = await self.base64_to_pil_images(base64_images)
        files = await self.images_to_discord_files(images)
        await self.channel.send(
            content=f"Flux Gen for `{self.user}`: Prompt: `{self.prompt}`",
            files=files)
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
        enhanced_prompt = await self.discord_client.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
        if self.lora_name:
            base64_images = await self.discord_client.avernus_client.flux_image(enhanced_prompt,
                                                                                batch_size=self.batch_size,
                                                                                width=self.width,
                                                                                height=self.height,
                                                                                lora_name=self.lora_name)
        else:
            base64_images = await self.discord_client.avernus_client.flux_image(enhanced_prompt,
                                                                                batch_size=self.batch_size,
                                                                                width=self.width,
                                                                                height=self.height,
                                                                                )
        images = await self.base64_to_pil_images(base64_images)
        files = await self.images_to_discord_files(images)
        await self.channel.send(
            content=f"Flux Gen for:`{self.user}` Prompt:`{self.prompt}` Enhanced Prompt:`{enhanced_prompt}`",
            files=files)
        sdxl_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
        sdxl_logger.info("Flux Success")
import io
import re
import tempfile
import time
import discord
from loguru import logger
from pydub import AudioSegment
from modules.settings_loader import SettingsLoader

class AceGen:
    """This is the queue object for flux generations"""
    def __init__(self,
                 discord_client,
                 prompt,
                 channel,
                 user,
                 lyrics,
                 length):
        self.settings = SettingsLoader("configs")
        self.discord_client = discord_client
        self.avernus_client = discord_client.avernus_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.lyrics = lyrics
        self.length = length

    async def run(self):
        start_time = time.time()
        try:
            kwargs = {"prompt": self.prompt}
            kwargs["lyrics"] = self.lyrics
            if self.length:
                kwargs["audio_duration"] = self.length
            else:
                kwargs["audio_duration"] = 30
            kwargs["infer_step"] = 120

            response = await self.avernus_client.ace_music(**kwargs)
            audio_item = load_audio_from_bytes(response)
            file = await self.audio_to_discord_files(audio_item)
            end_time = time.time()
            elapsed_time = end_time - start_time
            try:
                await self.channel.send(
                    content=f"Ace Gen for {self.user.mention}: Prompt: `{self.prompt}` Time:`{elapsed_time:.2f} seconds`",
                    file=file,
                    view=AceButtons(discord_client=self.discord_client,
                                    prompt=self.prompt,
                                    channel=self.channel,
                                    user=self.user,
                                    lyrics=self.lyrics,
                                    length=self.length))
            except Exception as e:
                logger.error(f"CHANNEL SEND ERROR: {e}")
            ace_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
            ace_logger.info("Ace Success")
        except Exception as e:
            await self.channel.send(f"{self.user.mention} Ace Error: {e}")
            ace_logger = logger.bind(user=f'{self.user}', prompt=self.prompt)
            ace_logger.error(f"FLUX ERROR: {e}")

    async def audio_to_discord_files(self, audio):
        """Takes a file path and returns a discord file object"""
        discord_file = discord.File(audio)
        return discord_file


class AceButtons(discord.ui.View):
    """Class for the ui buttons on /ace_gen"""
    def __init__(self,
                 discord_client,
                 prompt,
                 channel,
                 user,
                 lyrics,
                 length):
        super().__init__()
        self.timeout = None  # Disables the timeout on the buttons
        self.discord_client = discord_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.lyrics = lyrics
        self.length = length

    @discord.ui.button(label='Reroll', emoji="🎲", style=discord.ButtonStyle.grey)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rerolls last Ace gen"""
        if await self.discord_client.is_room_in_queue(interaction.user.id):
            ace_request = AceGen(self.discord_client,
                                 self.prompt,
                                 self.channel,
                                 interaction.user,
                                 self.lyrics,
                                 self.length)
            await interaction.response.send_message(
                f"Rerolling: {self.discord_client.request_queue.qsize()} requests in queue ahead of you.",
                ephemeral=True)
            ace_queuelogger = logger.bind(user=interaction.user.name, prompt=self.prompt)
            ace_queuelogger.info("Ace Queued")
            self.discord_client.request_queue_concurrency_list[interaction.user.id] += 1
            await self.discord_client.request_queue.put(ace_request)
        else:
            await interaction.response.send_message(
                "Queue limit reached, please wait until your current gen or gens finish", ephemeral=True)

    @discord.ui.button(label='Mail', emoji="✉", style=discord.ButtonStyle.grey)
    async def dmimage(self, interaction: discord.Interaction, button: discord.ui.Button):
        """DMs Ace Image"""
        await interaction.response.send_message("DM'ing mp3...", ephemeral=True, delete_after=5)
        sanitized_prompt = re.sub(r'[^\w\s\-.]', '', self.prompt)[:100]
        files = []
        for file in interaction.message.attachments:
            image_bytes = await file.read()
            attachment = discord.File(io.BytesIO(image_bytes), filename=f'{sanitized_prompt}.mp3')
            files.append(attachment)
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send(content=self.prompt, files=files)
        image_dm_logger = logger.bind(user=interaction.user.name, userid=interaction.user.id)
        image_dm_logger.success("Ace DM successful")

    @discord.ui.button(label='Delete', emoji="❌", style=discord.ButtonStyle.grey)
    async def delete_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deletes message"""
        if self.user.id == interaction.user.id:
            await interaction.message.delete()
        await interaction.response.send_message("Image deleted.", ephemeral=True, delete_after=5)
        speak_delete_logger = logger.bind(user=interaction.user.name, userid=interaction.user.id)
        speak_delete_logger.info("Ace Delete")

def load_audio_from_bytes(audio_bytes):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        f.flush()
        convert_wav_to_mp3(f.name, f.name)
        return f.name

def convert_wav_to_mp3(wav_path: str, mp3_path: str):
    try:
        audio = AudioSegment.from_wav(wav_path)
        audio.export(mp3_path, format="mp3")
    except Exception as e:
        print(f"Failed to convert WAV to MP3: {e}")
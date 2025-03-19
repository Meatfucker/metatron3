import base64
from datetime import datetime
import io
import json
import os
import random
import re
import discord
from loguru import logger
import requests
from PIL import Image, ImageFont, ImageDraw, ImageChops
from modules.settings_loader import SettingsLoader

with open('assets/mtg_card_gen/json/artist.json', 'r', encoding="utf-8") as file:
    artist_data = json.load(file)

class MTGCardGen:
    """This object builds a satire MTG card based on the users prompt"""

    def __init__(self, discord_client, prompt, channel, user):
        self.settings = SettingsLoader("configs")
        self.discord_client = discord_client
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.card = None
        self.card_title = None
        self.card_flavor_text = None
        self.card_artist = None
        self.card_type = None
        self.card_color = None
        self.card_primary_mana = None
        self.card_secondary_mana = None
        self.card_creature_type = None
        self.card_is_legendary = False

    async def run(self):
        """Builds a PIL image containing a card"""
        try:
            self.card_primary_mana = random.choice(range(1, 5))
            self.card_secondary_mana = random.choice(range(0, 5))
            self.choose_card_type()
            self.load_card_template()
            card_build_methods = {
                'creature': self.build_creature_card,
                'land': self.build_land_card,
                'instant': self.build_instant_card,
                'sorcery': self.build_sorcery_card,
                'artifact': self.build_artifact_card,
                'enchant': self.build_enchant_card,
            }

            for card_category, build_method in card_build_methods.items():
                if self.is_card_type(card_category):
                    await build_method()
                    break  # Only one type should match, so we stop after the first

            with io.BytesIO() as file_object:
                self.card.save(file_object, format="PNG")
                file_object.seek(0)
                filename = f'lighty_mtg_{self.prompt[:20]}.png'
                message = await self.channel.send(
                    content=f"Twitch Card for `{self.user}`: Prompt: `{self.prompt}`",
                    file=discord.File(file_object, filename=filename, spoiler=True)
                )

            sanitized_prompt = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', self.prompt)
            dir_path = f'assets/mtg_card_gen/users/{self.user}/{self.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
            os.makedirs(os.path.dirname(dir_path), exist_ok=True)
            self.card.save(dir_path, format="WEBP")

            message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"

            lightycard_logger = logger.bind(user=f'{self.user}', prompt=self.prompt, link=message_link)
            lightycard_logger.info("Card Success")
        except Exception as e:
            logger.info(f"MTG_CARD FAILURE: {e}")

    def choose_card_type(self):
        """Returns a random card type and associated color"""

        card_type_mapping = {
            'instant': ['black_instant', 'blue_instant', 'green_instant', 'red_instant', 'white_instant'],
            'sorcery': ['black_sorcery', 'blue_sorcery', 'green_sorcery', 'red_sorcery', 'white_sorcery'],
            'land': ['artifact_land', 'black_land', 'blue_land', 'green_land', 'red_land', 'white_land'],
            'creature': ['artifact_creature', 'black_creature', 'blue_creature', 'gold_creature', 'green_creature',
                         'red_creature', 'white_creature'],
            'artifact': ['artifact'],
            'enchant': ['black_enchant', 'blue_enchant', 'green_enchant', 'red_enchant', 'white_enchant']
        }

        card_color_mapping = {
            'artifact_creature': 'artifact', 'black_creature': 'black', 'blue_creature': 'blue',
            'gold_creature': 'gold',
            'green_creature': 'green', 'red_creature': 'red', 'white_creature': 'white',
            'artifact_land': 'artifact', 'black_land': 'black', 'blue_land': 'blue', 'green_land': 'green',
            'red_land': 'red', 'white_land': 'white', 'black_instant': 'black', 'blue_instant': 'blue',
            'green_instant': 'green', 'red_instant': 'red', 'white_instant': 'white', 'black_sorcery': 'black',
            'blue_sorcery': 'blue', 'green_sorcery': 'green', 'red_sorcery': 'red', 'white_sorcery': 'white',
            'artifact': 'artifact', 'black_enchant': 'black', 'blue_enchant': 'blue', 'green_enchant': 'green',
            'red_enchant': 'red', 'white_enchant': 'white'
        }

        base_card_type = random.choice(list(card_type_mapping.keys()))
        self.card_type = random.choice(card_type_mapping[base_card_type])
        self.card_color = card_color_mapping.get(self.card_type, 'error')

    def load_card_template(self):
        """Loads the base card template"""
        image_path = f"assets/mtg_card_gen/templates/{self.card_type}.png"
        with Image.open(image_path) as card_image:
            self.card = card_image.copy()

    def is_card_type(self, category):
        """Generalized function to check card type"""
        card_type_mapping = {
            'artifact': {'artifact'},
            'sorcery': {'black_sorcery', 'blue_sorcery', 'green_sorcery', 'red_sorcery', 'white_sorcery'},
            'instant': {'black_instant', 'blue_instant', 'green_instant', 'red_instant', 'white_instant'},
            'creature': {'artifact_creature', 'black_creature', 'blue_creature', 'gold_creature', 'green_creature',
                         'red_creature', 'white_creature'},
            'land': {'artifact_land', 'black_land', 'blue_land', 'green_land', 'red_land', 'white_land'},
            'enchant': {'black_enchant', 'blue_enchant', 'green_enchant', 'red_enchant', 'white_enchant'}
        }

        return self.card_type in card_type_mapping.get(category, set())

    async def build_creature_card(self):
        """Builds a creature card"""
        self.card_creature_type = self.generate_abilities('type_creature')
        await self.generate_card_text('creature')
        await self.generate_card_image('creature')
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_creature_card_atk_def()
        self.paste_mana()
        self.paste_type(self.card_creature_type)
        self.paste_ability("creature")
        self.roll_signature()

    async def build_land_card(self):
        """Builds a land card"""
        await self.generate_card_text('land')
        await self.generate_land_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_land_abilities()
        if self.card_is_legendary is True:
            self.paste_type("Legendary Land")
        else:
            self.paste_type("Land")
        self.roll_signature()

    async def build_instant_card(self):
        """Builds an instant card"""
        await self.generate_card_text('instant')
        await self.generate_card_image('spell')
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type("Instant")
        self.paste_ability("instant")
        self.roll_signature()

    async def build_sorcery_card(self):
        """Builds a sorcery card"""
        await self.generate_card_text('spell')
        await self.generate_card_image('spell')
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type("Sorcery")
        self.paste_ability("sorcery")
        self.roll_signature()

    async def build_artifact_card(self):
        """Builds an artifact card"""
        await self.generate_card_text('artifact')
        await self.generate_card_image('artifact')
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type("Artifact")
        self.paste_ability("artifact")
        self.roll_signature()

    async def build_enchant_card(self):
        """Builds an enchantment card"""
        await self.generate_card_text('enchant')
        await self.generate_card_image('spell')
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type('Enchantment')
        self.paste_ability('enchant')
        self.roll_signature()


    @staticmethod
    def generate_abilities(ability_file):
        """Returns a random card ability from the specified json file."""
        with open(f"assets/mtg_card_gen/json/{ability_file}.json", 'r') as instant_file:
            data = json.load(instant_file)
        return random.choice(data)

    async def generate_card_text(self, card_type):
        """Generates and returns a card title and card flavor text"""
        title_prompt = f"Create a new random Magic The Gathering {card_type} card title based on {self.prompt}. You respond with ONLY the title and it cannot be longer than 25 characters"
        flavor_prompt = f"Create a new random Magic The Gathering {card_type} card flavor text based on {self.prompt}. You respond with ONLY one sentence of flavor text."
        self.card_title = await self.discord_client.avernus_client.llm_chat(title_prompt,
                                                                            self.settings["avernus"]["mtg_llm_model"])
        self.card_flavor_text = await self.discord_client.avernus_client.llm_chat(flavor_prompt,
                                                                            self.settings["avernus"]["mtg_llm_model"])

    async def generate_card_image(self, category):
        """Prepares the prompt and generates an image based on the card category."""
        self.card_artist = self.get_random_artist_prompt()
        category_prompts = {
            'creature': f"{self.prompt}. {self.card_artist}. {self.card_title}.",
            'spell': f"casting spell {self.prompt}. {self.card_artist}. {self.card_title}.",
            'artifact': f"{self.prompt} artifact. {self.card_artist}. {self.card_title}."
        }
        generation_prompt = category_prompts.get(category)
        try:
            channel_settings = SettingsLoader("configs/channels")
            lora_name = channel_settings[f"{self.channel.id}"]["lora_name"]
            lora_prompt = channel_settings[f"{self.channel.id}"]["lora_prompt"]
        except Exception as e:
            lora_name = None

        if lora_name:
            generation_prompt = lora_prompt + generation_prompt
            base64_image = await self.discord_client.avernus_client.sdxl_image(generation_prompt,
                                                                               batch_size=1,
                                                                               lora_name=lora_name)
        else:
            base64_image = await self.discord_client.avernus_client.sdxl_image(generation_prompt, batch_size=1)
        image = await self.base64_to_pil_images(base64_image[0])
        resized_image = image.resize((568, 465))
        self.card.paste(resized_image, (88, 102))


    async def generate_land_image(self):
        """Prepares the prompt and generates a land card image."""
        self.card_artist = self.get_random_artist_prompt()
        land_color_mapping = {
            'artifact_land': f'{self.prompt} artifact structure. {self.card_artist}.',
            'black_land': f'{self.prompt} swamp. {self.card_artist}.',
            'blue_land': f'{self.prompt} shore. {self.card_artist}.',
            'white_land': f'{self.prompt} field of plains. {self.card_artist}.',
            'green_land': f'{self.prompt} forest. {self.card_artist}.',
            'red_land': f'{self.prompt} mountains. {self.card_artist}.'
        }
        generation_prompt = land_color_mapping.get(self.card_type)
        try:
            channel_settings = SettingsLoader("configs/channels")
            lora_name = channel_settings[f"{self.channel.id}"]["lora_name"]
            lora_prompt = channel_settings[f"{self.channel.id}"]["lora_prompt"]
        except Exception as e:
            lora_name = None

        if lora_name:
            generation_prompt = lora_prompt + generation_prompt
            base64_image = await self.discord_client.avernus_client.sdxl_image(generation_prompt,
                                                                               batch_size=1,
                                                                               lora_name=lora_name)
        else:
            base64_image = await self.discord_client.avernus_client.sdxl_image(generation_prompt, batch_size=1)
        image = await self.base64_to_pil_images(base64_image[0])
        resized_image = image.resize((568, 465))
        self.card.paste(resized_image, (88, 102))

    @staticmethod
    def get_random_artist_prompt():
        """Returns a string containing a random artist from a csv file full of artists"""
        selected_artist = random.choice(artist_data)
        return selected_artist.get('prompt')

    @staticmethod
    async def base64_to_pil_images(base64_image):
        """Converts a base64 images into a PIL image."""
        img_data = base64.b64decode(base64_image)  # Decode base64 string
        img = Image.open(io.BytesIO(img_data))  # Convert to PIL image

        return img

    def roll_foil(self):
        """Rolls to see if a card is foil, and if so adds the foil texture and foil set icon"""
        if random.randint(1, 50) == 1:
            foil_mapping = {
                'artifact_creature': 'assets/mtg_card_gen/foils/foil1.png',
                'black_creature': 'assets/mtg_card_gen/foils/foil1.png',
                'green_creature': 'assets/mtg_card_gen/foils/foil1.png',
                'blue_creature': 'assets/mtg_card_gen/foils/foil2.png',
                'gold_creature': 'assets/mtg_card_gen/foils/foil3.png',
                'red_creature': 'assets/mtg_card_gen/foils/foil4.png',
                'white_creature': 'assets/mtg_card_gen/foils/foil5.png',
                'artifact_land': 'assets/mtg_card_gen/foils/foil1.png',
                'black_land': 'assets/mtg_card_gen/foils/foil1.png',
                'green_land': 'assets/mtg_card_gen/foils/foil1.png',
                'blue_land': 'assets/mtg_card_gen/foils/foil2.png',
                'red_land': 'assets/mtg_card_gen/foils/foil4.png',
                'white_land': 'assets/mtg_card_gen/foils/foil5.png',
                'black_instant': 'assets/mtg_card_gen/foils/foil1.png',
                'green_instant': 'assets/mtg_card_gen/foils/foil1.png',
                'blue_instant': 'assets/mtg_card_gen/foils/foil2.png',
                'red_instant': 'assets/mtg_card_gen/foils/foil4.png',
                'white_instant': 'assets/mtg_card_gen/foils/foil5.png',
                'black_sorcery': 'assets/mtg_card_gen/foils/foil1.png',
                'green_sorcery': 'assets/mtg_card_gen/foils/foil1.png',
                'blue_sorcery': 'assets/mtg_card_gen/foils/foil2.png',
                'red_sorcery': 'assets/mtg_card_gen/foils/foil4.png',
                'white_sorcery': 'assets/mtg_card_gen/foils/foil5.png',
                'black_enchant': 'assets/mtg_card_gen/foils/foil1.png',
                'green_enchant': 'assets/mtg_card_gen/foils/foil1.png',
                'blue_enchant': 'assets/mtg_card_gen/foils/foil2.png',
                'red_enchant': 'assets/mtg_card_gen/foils/foil4.png',
                'white_enchant': 'assets/mtg_card_gen/foils/foil5.png'
            }
            foil_image = foil_mapping.get(self.card_type, 'error')
            with Image.open(foil_image).convert("RGBA") as foil_texture:
                resized_foil_texture = foil_texture.resize(self.card.size)
                self.card = ImageChops.soft_light(self.card, resized_foil_texture)
                icon_image = Image.open("assets/mtg_card_gen/icons/foilicon.png")
                self.card.paste(icon_image, (600, 585), icon_image)
            return
        server_icon = self.get_image_from_url(self.channel.guild.icon)
        circle_icon = self.make_circle(server_icon)
        icon_image = circle_icon.resize((42, 42))
        #icon_image = Image.open("assets/mtg_card_gen/icons/set_icon.png")
        self.card.paste(icon_image, (619, 579), icon_image)

    def paste_title_text(self):
        """Adds card title to a card"""
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/planewalker.otf", 36)
        draw = ImageDraw.Draw(self.card)
        draw.text((58, 52), self.card_title, font=font, fill="black")
        draw.text((56, 50), self.card_title, font=font, fill="white")

    def paste_artist_copyright(self):
        """Adds artist and copyright text to a card"""
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamond.ttf", 32)
        draw = ImageDraw.Draw(self.card)
        draw.text((72, 942), f"Illus. {self.card_artist}", font=font, fill="black")
        draw.text((70, 940), f"Illus. {self.card_artist}", font=font, fill="white")
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamond.ttf", 20)
        draw.text((72, 975), f"© 1994 {self.user} - {self.channel.guild.name}", font=font, fill="black")
        draw.text((70, 973), f"© 1994 {self.user} - {self.channel.guild.name}", font=font, fill="white")

    def paste_creature_card_atk_def(self):
        """Rolls the creature atk/def based on mana, then applies it to the card"""
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/planewalker.otf", 44)
        draw = ImageDraw.Draw(self.card)

        if self.card_color == 'gold':
            creature_def = random.choice(range(1, self.card_primary_mana * 2))
            creature_atk = random.choice(range(0, self.card_primary_mana * 2))

        if self.card_color in ['green', 'red', 'black', 'white', 'blue', 'artifact']:
            minimum_stat = max(1, (self.card_primary_mana + self.card_secondary_mana) // 2)

            if minimum_stat == self.card_primary_mana + self.card_secondary_mana:
                creature_def = self.card_primary_mana + self.card_secondary_mana
            else:
                creature_def = random.choice(range(minimum_stat, self.card_primary_mana + self.card_secondary_mana))
            if minimum_stat == self.card_primary_mana + self.card_secondary_mana:
                creature_atk = self.card_primary_mana + self.card_secondary_mana
            else:
                creature_atk = random.choice(range(minimum_stat, self.card_primary_mana + self.card_secondary_mana))

        draw.text((622, 936), f'{creature_atk}/{creature_def}', font=font, fill="black")
        draw.text((620, 934), f'{creature_atk}/{creature_def}', font=font, fill="white")

    def paste_mana(self):
        """Creates and adds mana icons to a card based on its color"""
        if self.card_color in ['green', 'red', 'black', 'white', 'blue']:
            primary_mana_image = Image.open(f"assets/mtg_card_gen/icons/{self.card_color}mana.png")
            secondary_mana_image = Image.open(f"assets/mtg_card_gen/icons/{self.card_secondary_mana}mana.png")
        if self.card_color == 'artifact':
            primary_mana_image = Image.open(f"assets/mtg_card_gen/icons/{self.card_secondary_mana + self.card_primary_mana}mana.png")
            self.card_secondary_mana = 0
        if self.card_color == 'gold':
            primary_mana_image = Image.open(f"assets/mtg_card_gen/icons/{self.card_secondary_mana}mana.png")
            secondary_mana_image = Image.open(f"assets/mtg_card_gen/icons/{self.card_secondary_mana}mana.png")

        primary_mana_width, primary_mana_height = primary_mana_image.size
        if self.card_color in ['green', 'red', 'black', 'white', 'blue']:
            combined_mana_width = primary_mana_width + (primary_mana_width * self.card_primary_mana)
        if self.card_color == 'artifact':
            combined_mana_width = primary_mana_width
        if self.card_color == 'gold':
            combined_mana_width = primary_mana_width + (primary_mana_width * self.card_primary_mana)
        combined_mana_image = Image.new('RGBA', (combined_mana_width, primary_mana_height))

        if random.randint(0, 2) != 1:
            use_secondary_mana = False
        else:
            use_secondary_mana = True
        if use_secondary_mana:
            if self.card_secondary_mana >= 1:
                combined_mana_image.paste(secondary_mana_image, (0, 0))

        if self.card_color in ['green', 'red', 'black', 'white', 'blue']:
            for i in range(self.card_primary_mana):
                combined_mana_image.paste(primary_mana_image, (primary_mana_width + i * primary_mana_width, 0))
        if self.card_color == 'artifact':
            combined_mana_image.paste(primary_mana_image, (0, 0))
        if self.card_color == 'gold':
            image_paths = [
                'assets/mtg_card_gen/icons/redmana.png',
                'assets/mtg_card_gen/icons/blackmana.png',
                'assets/mtg_card_gen/icons/whitemana.png',
                'assets/mtg_card_gen/icons/greenmana.png',
                'assets/mtg_card_gen/icons/bluemana.png'
            ]
            for i in range(self.card_primary_mana):
                primary_mana_image = Image.open(random.choice(image_paths))
                combined_mana_image.paste(primary_mana_image, (primary_mana_width + i * primary_mana_width, 0))
        self.card.paste(combined_mana_image, (676 - combined_mana_image.width, 49), combined_mana_image)

    def paste_type(self, card_type):
        """Adds creature type to a card"""
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamond.ttf", 36)
        draw = ImageDraw.Draw(self.card)
        draw.text((88, 582), card_type, font=font, fill="black")
        draw.text((86, 580), card_type, font=font, fill="white")

    def paste_ability(self, ability_file):
        """Draws a list of words onto an image, parsing mana symbols and wrapping to a new line if the text exceeds
        max_width."""
        mana_mapping = {
            '{W}': 'assets/mtg_card_gen/icons/white_mana_small.png',
            '{U}': 'assets/mtg_card_gen/icons/blue_mana_small.png',
            '{B}': 'assets/mtg_card_gen/icons/black_mana_small.png',
            '{R}': 'assets/mtg_card_gen/icons/red_mana_small.png',
            '{G}': 'assets/mtg_card_gen/icons/green_mana_small.png',
            '{T}': 'assets/mtg_card_gen/icons/tap.png',
            '{0}': 'assets/mtg_card_gen/icons/0_mana_small.png',
            '{1}': 'assets/mtg_card_gen/icons/1_mana_small.png',
            '{2}': 'assets/mtg_card_gen/icons/2_mana_small.png',
            '{3}': 'assets/mtg_card_gen/icons/3_mana_small.png',
            '{4}': 'assets/mtg_card_gen/icons/4_mana_small.png',
            '{5}': 'assets/mtg_card_gen/icons/5_mana_small.png',
            '{6}': 'assets/mtg_card_gen/icons/6_mana_small.png',
            '{7}': 'assets/mtg_card_gen/icons/7_mana_small.png',
            '{8}': 'assets/mtg_card_gen/icons/8_mana_small.png',
            '{9}': 'assets/mtg_card_gen/icons/9_mana_small.png',
            '{X}': 'assets/mtg_card_gen/icons/x_mana_small.png',
        }

        x_start, y_start = 94, 640
        draw = ImageDraw.Draw(self.card)
        ability_list = self.generate_abilities(ability_file)
        pattern = r'(\{[^}]+\}|\S+|\n)'
        words = re.findall(pattern, ability_list)
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamondbullet.ttf", 36)
        line_height = 32
        current_x, current_y = x_start, y_start

        for word in words:
            if word == "\n":
                current_x = x_start  # Move to the beginning of the next line
                current_y += line_height
                continue
            match = re.match(r'\{[A-Za-z0-9]\}', word)
            if match:
                mana_image = mana_mapping.get(match.group(0), 'error')
                uncolored_image = Image.open(mana_image)
                uncolored_width, uncolored_height = uncolored_image.size
                image_bbox = (current_x, current_y, current_x + uncolored_width, current_y + uncolored_height)
                if image_bbox[2] > 659:
                    # If image exceeds the width, move to the next line
                    current_x = x_start
                    current_y += uncolored_height
                self.card.paste(uncolored_image, (current_x, current_y), uncolored_image)
                current_x += uncolored_width
                continue
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            if current_x + word_width > 659:
                current_x = x_start
                current_y += line_height
            draw.text((current_x, current_y), word, font=font, fill="black")
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]

        current_x = x_start
        current_y += line_height
        if current_y <= 775:
            second_words = re.findall(pattern, self.card_flavor_text)
            second_font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamonditalic.ttf", 36)
            for word in second_words:
                if word == "\n":
                    current_x = x_start
                    current_y += line_height
                    continue
                bbox = draw.textbbox((0, 0), word, font=second_font)
                word_width = bbox[2] - bbox[0]
                if current_x + word_width > 659:
                    current_x = x_start
                    current_y += line_height
                draw.text((current_x, current_y), word, font=second_font, fill="black")
                current_x += word_width + draw.textbbox((0, 0), ' ', font=second_font)[2]

    def paste_land_abilities(self):
        """Adds land text and mana icons to a card"""
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamond.ttf", 36)
        draw = ImageDraw.Draw(self.card)
        draw.text((235, 668), "Tap to add", font=font, fill="black")
        draw.text((235, 713), "to your mana pool.", font=font, fill="black")

        if self.card_color == 'artifact':
            if random.randint(1, 10) == 1:
                base_image_path = f"assets/mtg_card_gen/icons/{random.randint(2, 4)}mana.png"
                self.card_is_legendary = True
            else:
                base_image_path = f"assets/mtg_card_gen/icons/1mana.png"
        else:
            if random.randint(1, 10) == 1:
                base_image_path = f'assets/mtg_card_gen/icons/{random.randint(1, 4)}{self.card_color}mana.png'
                self.card_is_legendary = True
            else:
                base_image_path = f'assets/mtg_card_gen/icons/{self.card_color}mana.png'
        mana_image = Image.open(base_image_path)
        mana_image_width, mana_image_height = mana_image.size
        combined_mana_image = Image.new('RGBA', (mana_image_width, mana_image_height))
        combined_mana_image.paste(mana_image, (0, 0))
        self.card.paste(combined_mana_image, (392, 665), combined_mana_image)

        x_start, y_start = 94, 760
        ability_list = self.card_flavor_text
        pattern = r'(\{[^}]+\}|\S+|\n)'
        words = re.findall(pattern, ability_list)
        font = ImageFont.truetype("assets/mtg_card_gen/fonts/garamonditalic.ttf", 36)
        current_x, current_y = x_start, y_start

        for word in words:
            if word == "\n":
                current_x = x_start  # Move to the beginning of the next line
                current_y += 32
                continue
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            if current_x + word_width > 659:
                current_x = x_start
                current_y += 32
            draw.text((current_x, current_y), word, font=font, fill="black")
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]

    def roll_signature(self):
        """Rolls to see if a card is signed, and if so adds the signature texture"""
        if random.randint(1, 100) == 1:
            signature_image = 'assets/mtg_card_gen/foils/signature.png'
            with Image.open(signature_image).convert("RGBA") as signature_texture:
                self.card.paste(signature_texture, (100, 590), signature_texture)
    @staticmethod
    def get_image_from_url(url: str) -> Image.Image:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we got a successful response
        return Image.open(io.BytesIO(response.content))

    @staticmethod
    def make_circle(image: Image.Image) -> Image.Image:
        size = image.size[0]  # Since it's square, width and height are the same

        # Create a blank RGBA image with transparency
        circle_image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

        # Create a circular mask
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        # Apply the mask to the image
        circle_image.paste(image, (0, 0), mask)

        return circle_image

class MTGCardGenThreePack(MTGCardGen):
    async def run(self):
        """Builds a PIL image containing a card"""
        now = datetime.now()
        now_string = now.strftime("%Y%m%d%H%M%S")
        sanitized_prompt = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', self.prompt)

        card1 = await self.make_card()
        dir_path_1 = f'assets/mtg_card_gen/users/{self.user}/{self.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
        card_path_1 = f'assets/mtg_card_gen/users/{self.user}/{now_string}/card1.webp'
        os.makedirs(os.path.dirname(dir_path_1), exist_ok=True)
        os.makedirs(os.path.dirname(card_path_1), exist_ok=True)
        card1.save(dir_path_1, format="WEBP")
        card1.save(card_path_1, format="WEBP")

        card2 = await self.make_card()
        dir_path_2 = f'assets/mtg_card_gen/users/{self.user}/{self.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
        card_path_2 = f'assets/mtg_card_gen/users/{self.user}/{now_string}/card2.webp'
        os.makedirs(os.path.dirname(dir_path_2), exist_ok=True)
        os.makedirs(os.path.dirname(card_path_2), exist_ok=True)
        card2.save(dir_path_2, format="WEBP")
        card2.save(card_path_2, format="WEBP")

        card3 = await self.make_card()
        dir_path_3 = f'assets/mtg_card_gen/users/{self.user}/{self.card_type}.{sanitized_prompt[:20]}.{random.randint(1, 99999999)}.webp'
        card_path_3 = f'assets/mtg_card_gen/users/{self.user}/{now_string}/card3.webp'
        os.makedirs(os.path.dirname(dir_path_3), exist_ok=True)
        os.makedirs(os.path.dirname(card_path_3), exist_ok=True)
        card3.save(dir_path_3, format="WEBP")
        card3.save(card_path_3, format="WEBP")

        message = await self.channel.send(f"# `{self.user}` [OPEN PACK](http://theblackgoat.net/cardflip-dynamic.html?username={self.user}&datetimestring={now_string})")
        await self.channel.send(
            content=f"Card Pack for `{self.user}`: Prompt: `{self.prompt}`",
            files=[discord.File(dir_path_1, filename=f'lighty_mtg_{self.prompt[:20]}.png', spoiler=True),
                   discord.File(dir_path_2, filename=f'lighty_mtg_{self.prompt[:20]}.png', spoiler=True),
                   discord.File(dir_path_3, filename=f'lighty_mtg_{self.prompt[:20]}.png', spoiler=True)]
        )
        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        lightycard_logger = logger.bind(user=f'{self.user}', prompt=self.prompt, link=message_link)
        lightycard_logger.info("Card Pack Success")

    async def make_card(self):
        try:
            self.card_primary_mana = random.choice(range(1, 5))
            self.card_secondary_mana = random.choice(range(0, 5))
            self.choose_card_type()
            self.load_card_template()
            card_build_methods = {
                'creature': self.build_creature_card,
                'land': self.build_land_card,
                'instant': self.build_instant_card,
                'sorcery': self.build_sorcery_card,
                'artifact': self.build_artifact_card,
                'enchant': self.build_enchant_card,
            }

            for card_category, build_method in card_build_methods.items():
                if self.is_card_type(card_category):
                    await build_method()
                    break  # Only one type should match, so we stop after the first

            return self.card
        except Exception as e:
            logger.info(f"MTG_CARD_THREE_PACK FAILURE: {e}")

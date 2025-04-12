import asyncio
import aiohttp
import json
import urllib.parse
import requests
import time
from loguru import logger
from modules.settings_loader import SettingsLoader
from modules.mtg_card import MTGCardGenThreePack
should_reconnect = asyncio.Event()


class TwitchEventSubClient:
    def __init__(self, discord_client):
        self.settings = SettingsLoader("configs")
        self.discord_client = discord_client
        self.twitch_eventsub_websocket = "wss://eventsub.wss.twitch.tv/ws"

    async def handle_websocket(self):
        """Handle Twitch EventSub WebSocket connection with automatic reconnection."""
        global should_reconnect  # Use the global event for signaling
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.twitch_eventsub_websocket) as ws:
                        logger.info("Twitch Login Success")

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                if data.get("metadata", {}).get("message_type") == "session_welcome":
                                    session_id = data["payload"]["session"]["id"]
                                    await self.subscribe_to_event(session, session_id)
                                elif data.get("metadata", {}).get("message_type") == "notification":
                                    event = data["payload"]["event"]
                                    prompt = event["user_input"]
                                    username = event["user_login"]
                                    user = CustomDiscordUser(username)
                                    channel = self.discord_client.get_channel(self.settings["twitch"]["card_reward_channel"])
                                    card_logger = logger.bind(user=username, prompt=prompt)
                                    card_logger.info("Card Redemption")
                                    if await self.discord_client.is_room_in_queue(user.id):
                                        mtg_card_request = MTGCardGenThreePack(self.discord_client, prompt, channel, user)
                                        self.discord_client.request_queue_concurrency_list[user.id] += 1
                                        await self.discord_client.request_queue.put(mtg_card_request)

                            elif msg.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                                logger.info("Twitch Reconnecting")
                                break
                            if should_reconnect.is_set():
                                logger.info("Twitch Reconnecting")
                                should_reconnect.clear()
                                break
            except Exception as e:
                logger.info(f"Twitch error: {e}, reconnecting in 5 seconds...")
            await asyncio.sleep(5)

    async def subscribe_to_event(self, session, session_id):
        """Send subscription request to Twitch EventSub API."""
        url = "https://api.twitch.tv/helix/eventsub/subscriptions"

        async def attempt_subscription():
            self.settings = SettingsLoader("configs")
            headers = {
                "Authorization": f"Bearer {self.settings['twitch']['channel_token']}",
                "Client-Id": self.settings["twitch"]["client_id"],
                "Content-Type": "application/json",
            }
            payload = {
                "type": "channel.channel_points_custom_reward_redemption.add",
                "version": "1",
                "condition": {"broadcaster_user_id": self.settings["twitch"]["channel_id"]},
                "transport": {"method": "websocket", "session_id": session_id},
            }
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 202:
                    logger.info("Twitch Subscribed")
                    return True
                else:
                    error_message = await response.text()
                    logger.info(f"Failed to subscribe: {error_message}")
                    return False

        if not await attempt_subscription():
            logger.info("Attempting to refresh tokens")
            await self.refresh_token()
            await attempt_subscription()

    async def refresh_token(self):
        """Refresh auth tokens and signal reconnection."""
        unparsed_refresh_token = self.settings["twitch"]["refresh_token"]
        encoded_refresh_token = urllib.parse.quote(unparsed_refresh_token)
        url = 'https://id.twitch.tv/oauth2/token'
        data = {
            'client_id': self.settings["twitch"]["client_id"],
            'client_secret': self.settings["twitch"]["client_secret"],
            'grant_type': 'refresh_token',
            'refresh_token': encoded_refresh_token
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logger.info('Access token refreshed')
            response_data = response.json()
            self.update_access_tokens(response_data)
            should_reconnect.set()
        else:
            logger.info('Failed to refresh access token.')
            logger.info(f'Status Code: {response.status_code}')
            logger.info(f'Response: {response.json()}')

    @staticmethod
    def update_access_tokens(response_data):
        """Update tokens in the config file."""
        try:
            with open("configs/twitch.json", 'r', encoding='utf-8') as file:
                data = json.load(file)
            data["channel_token"] = response_data.get('access_token')
            data["refresh_token"] = response_data.get('refresh_token')
            data["token_expires_at"] = int(time.time()) + response_data.get('expires_in')
            with open("configs/twitch.json", 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            return True
        except Exception as e:
            logger.info(f"Error updating JSON file: {e}")
            return False

    async def check_token_expiry(self):
        """Check token expiry and refresh if needed."""
        while True:
            try:
                with open("configs/twitch.json", 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if int(time.time()) >= data.get("token_expires_at", 0):
                    logger.info("Access token expired, refreshing...")
                    await self.refresh_token()
            except Exception as e:
                logger.info(f"Error checking token expiry: {e}")
            await asyncio.sleep(60)

    async def start(self):
        """Start the event listener and token checker."""
        await asyncio.gather(
            self.check_token_expiry(),
            self.handle_websocket()
        )

class CustomDiscordUser:
    """Allows setting arbitrary discord user ids for the queue to work with since twitch has none"""
    def __init__(self, user):
        self.id = 666
        self.user = user

    def __str__(self):
        return self.user
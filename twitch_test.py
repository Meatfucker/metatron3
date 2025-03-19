import asyncio
import aiohttp
import json
from loguru import logger
import urllib.parse
import requests
from modules.settings_loader import SettingsLoader

TWITCH_EVENTSUB_WS = "wss://eventsub.wss.twitch.tv/ws"
should_reconnect = asyncio.Event()


async def handle_websocket():
    """Handle Twitch EventSub WebSocket connection with automatic reconnection."""
    global should_reconnect  # Use the global event for signaling

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(TWITCH_EVENTSUB_WS) as ws:
                    logger.info("Connected to Twitch EventSub WebSocket")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)

                            # Handle welcome message & subscribe to event
                            if data.get("metadata", {}).get("message_type") == "session_welcome":
                                session_id = data["payload"]["session"]["id"]
                                await subscribe_to_event(session, session_id)

                            # Handle channel point redemptions
                            elif data.get("metadata", {}).get("message_type") == "notification":
                                event = data["payload"]["event"]
                                logger.info(f"Redemption: {event['reward']['title']} by {event['user_name']}")
                                logger.info(event)

                        elif msg.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                            logger.info("WebSocket connection closed, reconnecting...")
                            break  # Exit loop to trigger reconnection

                        # Check if we need to refresh the connection
                        if should_reconnect.is_set():
                            logger.info("Token refreshed, restarting WebSocket connection...")
                            should_reconnect.clear()
                            break  # Break to force reconnection

        except Exception as e:
            logger.info(f"WebSocket error: {e}, reconnecting in 5 seconds...")

        await asyncio.sleep(5)  # Wait before attempting to reconnect


async def subscribe_to_event(session, session_id):
    """Send subscription request to Twitch EventSub API with a retry on failure."""

    url = "https://api.twitch.tv/helix/eventsub/subscriptions"

    async def attempt_subscription():
        settings = SettingsLoader("configs")
        headers = {
            "Authorization": f"Bearer {settings['twitch']['channel_token']}",
            "Client-Id": settings["twitch"]["client_id"],
            "Content-Type": "application/json",
        }
        payload = {
            "type": "channel.channel_points_custom_reward_redemption.add",
            "version": "1",
            "condition": {"broadcaster_user_id": settings["twitch"]["channel_id"]},
            "transport": {"method": "websocket", "session_id": session_id},
        }

        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 202:
                logger.info("Successfully subscribed to channel point redemptions!")
                return True
            else:
                error_message = await response.text()
                logger.info(f"Failed to subscribe: {error_message}")
                return False

    # First attempt
    if not await attempt_subscription():
        logger.info("Attempting to refresh tokens")
        await refresh_token()
        # Retry subscription after refreshing token
        await attempt_subscription()


import time  # Add this import

async def refresh_token():
    """Refreshes auth tokens, reauthorizes with Twitch, and signals reconnection."""
    settings = SettingsLoader("configs")
    unparsed_refresh_token = settings["twitch"]["refresh_token"]
    encoded_refresh_token = urllib.parse.quote(unparsed_refresh_token)
    url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'client_id': settings["twitch"]["client_id"],
        'client_secret': settings["twitch"]["client_secret"],
        'grant_type': 'refresh_token',
        'refresh_token': encoded_refresh_token
    }
    response = requests.post(url, data=data)

    if response.status_code == 200:
        logger.info('Access token refreshed')
        response_data = response.json()
        new_access_token = response_data.get('access_token')
        new_refresh_token = response_data.get('refresh_token')
        token_lifetime = response_data.get('expires_in')  # Lifetime in seconds
        expiration_timestamp = int(time.time()) + token_lifetime  # Calculate expiration time

        update_access_tokens(new_access_token, new_refresh_token, expiration_timestamp)
        logger.info(f"Tokens updated. Expires at {expiration_timestamp} (Unix timestamp)")

        # Signal the WebSocket to reconnect
        should_reconnect.set()

    else:
        logger.info('Failed to refresh access token.')
        logger.info(f'Status Code: {response.status_code}')
        logger.info(f'Response: {response.json()}')

    return new_access_token



def update_access_tokens(token, new_refresh_token, expiration_timestamp):
    """Update the access and refresh tokens along with expiration time."""
    try:
        with open("configs/twitch.json", 'r', encoding='utf-8') as file:
            data = json.load(file)

        data["channel_token"] = token
        data["refresh_token"] = new_refresh_token
        data["token_expires_at"] = expiration_timestamp  # Store absolute expiration time

        with open("configs/twitch.json", 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

        return True
    except Exception as e:
        logger.info(f"Error updating JSON file: {e}")
        return False

async def check_token_expiry():
    """Periodically checks if the token has expired and refreshes if necessary."""
    while True:
        try:
            with open("configs/twitch.json", 'r', encoding='utf-8') as file:
                data = json.load(file)

            expiration_timestamp = data.get("token_expires_at", 0)
            current_time = int(time.time())

            if current_time >= expiration_timestamp:
                logger.info("Access token expired, refreshing...")
                await refresh_token()


        except Exception as e:
            logger.info(f"Error checking token expiry: {e}")

        await asyncio.sleep(60)  # Check every 60 seconds

async def start_threads():
    """Starts up threads"""
    await asyncio.gather(
        check_token_expiry(),
        handle_websocket()
    )

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_threads())
    except KeyboardInterrupt:
        logger.info("Twitch SHUTDOWN")
    finally:
        loop.close()

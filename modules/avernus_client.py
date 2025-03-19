import httpx
from loguru import logger
from modules.settings_loader import SettingsLoader

class AvernusClient:
    """This is the client for the avernus API server"""
    def __init__(self):
        self.settings = SettingsLoader("configs")
        self.url = self.settings["avernus"]["ip"]
        self.port = self.settings["avernus"]["port"]
        self.base_url = f"{self.url}:{self.port}"

    async def llm_chat(self, prompt, model_name=None, messages=None):
        url = f"http://{self.base_url}/llm_chat"
        data = {"prompt": prompt, "model_name": model_name, "messages": messages}

        try:
            async with httpx.AsyncClient(timeout=3600.0) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.info(f"STATUS ERROR: {response.status_code}, Response: {response.text}")
                return {"ERROR": response.text}
        except Exception as e:
            logger.info(f"EXCEPTION ERROR: {e}")
            return {"ERROR": str(e)}

    async def sdxl_image(self, prompt, negative_prompt=None, model_name=None, lora_name=None, width=1024, height=1024,
                         steps=30,
                         batch_size=4):
        url = f"http://{self.base_url}/sdxl_generate"
        data = {"prompt": prompt,
                "negative_prompt": negative_prompt,
                "model_name": model_name,
                "lora_name": lora_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.info(f"ERROR: {response.status_code}")
        except Exception as e:
            logger.info(f"ERROR: {e}")
            return {"ERROR": str(e)}

    async def flux_image(self, prompt, negative_prompt=None, model_name=None, width=1024, height=1024, steps=30,
                         batch_size=1):
        url = f"http://{self.base_url}/flux_generate"
        data = {"prompt": prompt,
                "negative_prompt": negative_prompt,
                "model_name": model_name,
                "width": width,
                "height": height,
                "steps": steps,
                "batch_size": batch_size}
        try:
            async with httpx.AsyncClient(timeout=3600) as client:
                response = await client.post(url, json=data)
            if response.status_code == 200:
                return response.json()
            else:
                logger.info(f"ERROR: {response.status_code}")
        except Exception as e:
            logger.info(f"ERROR: {e}")
            return {"ERROR": str(e)}
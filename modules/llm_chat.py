import json
import os
import time


from loguru import logger

from modules.settings_loader import SettingsLoader

class LlmChat:
    """This is the queue object to generate chat."""
    def __init__(self, discord_client, prompt, channel, user):
        self.settings: SettingsLoader = SettingsLoader("configs")
        self.prompt: str = prompt
        self.discord_client = discord_client
        self.channel = channel
        self.user = user

    async def run(self):
        start_time = time.time()
        try:
            rag_results = await self.discord_client.avernus_client.rag_retrieve(self.prompt)
            logger.info(rag_results)
            combined_rag_result = ""
            for result in rag_results:
                combined_rag_result = combined_rag_result + result + " . "
            self.rag_prompt = self.prompt + f". The following information was retrieved by RAG for supplemental information to the previous sentence. Only consider this information if its directly relevant to the chat: {combined_rag_result}"
            history = await self.get_history()
            if history is None:
                response = await self.discord_client.avernus_client.llm_chat(self.rag_prompt,
                                                                         self.settings["avernus"]["llm_model"])
            else:
                response = await self.discord_client.avernus_client.llm_chat(self.rag_prompt,
                                                                             self.settings["avernus"]["llm_model"],
                                                                             history)
            await self.add_history("user", self.prompt)
            await self.add_history("assistant", response)
            end_time = time.time()
            elapsed_time = end_time - start_time
            await self.channel.send(f"{self.user.mention}  Time:`{elapsed_time:.2f} seconds`")
            for i in range(0, len(response), 2000):
                chunk = response[i:i + 2000]
                await self.channel.send(content=chunk, mention_author=True)
            generate_chat_logger = logger.bind(user=self.user, channel=self.channel)
            generate_chat_logger.info("Chat Success")
        except Exception as e:
            await self.channel.send(f"{self.user.mention} LLM Error: {e}")
            llm_logger = logger.bind(user=self.user, channel=self.channel)
            llm_logger.error(f"LLM FAILURE: {e}")


    async def add_history(self, role, content):
        """Adds each message to a JSON file named after the user's ID."""
        history_file = f"configs/users/{self.user.id}.json"
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as file:
                try:
                    history = json.load(file)
                except json.JSONDecodeError:
                    history = {"history": []}
        else:
            history = {"history": []}

        if "history" not in history:
            history["history"] = []

        history["history"].append({"role": role, "content": content})

        history["history"] = history["history"][-self.settings["discord"]["max_user_history_messages"]:]
        with open(history_file, "w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=4)

    async def get_history(self):
        history_file = f"configs/users/{self.user.id}.json"
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as file:
                try:
                    history = json.load(file)
                except json.JSONDecodeError:
                    history = None
                finally:
                    return history.get("history", [])
        else:
            return None


class LlmChatClear:
    """This is the queue object to clear a users chat history."""
    def __init__(self, discord_client, channel, user):
        self.discord_client = discord_client
        self.channel = channel
        self.user = user

    async def run(self):
        try:
            await self.forget_history()
            await self.channel.send(content=f"{self.user} chat history cleared.", delete_after=5)
            clear_chat_logger = logger.bind(user=self.user)
            clear_chat_logger.info("LLM History Cleared")
        except Exception as e:
            await self.channel.send(f"{self.user.mention} LLM Error: {e}")
            logger.info(f"LLM CLEAR HISTORY FAILURE: {e}")

    async def forget_history(self):
        history_file = f"configs/users/{self.user.id}.json"
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as file:
                try:
                    history = json.load(file)
                except json.JSONDecodeError:
                    history = {"history": []}
        else:
            history = {"history": []}

        history["history"] = []
        with open(history_file, "w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=4)
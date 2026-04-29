"""
对话历史管理与 API 调用封装
"""
from cgitb import handler

from src.main.api.api_manager import get_completion, SYSTEM_PROMPT, get_completion_stream


class MessageHandler:

    def __init__(self, system_prompt: str = None):
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.history = [{"role": "system", "content": self.system_prompt}]

    def add_user_message(self, text: str):
        self.history.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str):
        self.history.append({"role": "assistant", "content": text})

    def get_response(self, user_input: str = None) -> str:
        if user_input:
            self.add_user_message(user_input)

        reply = get_completion(self.history)
        self.add_assistant_message(reply)
        return reply

    def reset(self):
        self.history = [{"role": "system", "content": self.system_prompt}]

    def get_last_user_message(self) -> str | None:
        for msg in reversed(self.history):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def get_last_assistant_message(self) -> str | None:
        for msg in reversed(self.history):
            if msg["role"] == "assistant":
                return msg["content"]
        return None

    def get_response(self, user_input: str = None) -> str:
        if user_input:
            self.add_user_message(user_input)
        reply = get_completion(self.history)
        self.add_assistant_message(reply)
        return reply

    def get_response_stream(self, user_input: str = None) -> str:
        if user_input:
            self.add_user_message(user_input)
        full_reply = ""
        for chunk in get_completion_stream(self.history):
            full_reply += chunk
            yield chunk

        self.add_assistant_message(full_reply)
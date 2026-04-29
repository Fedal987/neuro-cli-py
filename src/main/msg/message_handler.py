"""
对话历史管理与 API 调用封装
"""
# from cgitb import handler

from src.main.api.api_manager import get_completion, SYSTEM_PROMPT, get_completion_stream, STREAM

class MessageHandler:

    def __init__(self, system_prompt: str = None):
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.use_stream = STREAM

    def add_user_message(self, text: str):
        self.history.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str):
        self.history.append({"role": "assistant", "content": text})

    def get_response(self, user_input: str = None) -> str:
        if user_input:
            self.add_user_message(user_input)
        if self.use_stream:
            full_reply = ""
            for chunk in self.get_response_stream_internal():
                full_reply += chunk
            reply = full_reply
        else:
            reply = get_completion(self.history)
        self.add_assistant_message(reply)
        return reply

    def get_response_stream(self, user_input: str = None):
        if user_input:
            self.add_user_message(user_input)
        full_reply = ""
        for chunk in get_completion_stream(self.history):
            full_reply += chunk
            yield chunk
        self.add_assistant_message(full_reply)

    def get_response_stream_internal(self, user_input: str = None):
        if user_input:
            self.add_user_message(user_input)
        result = get_completion(self.history, stream=True)

        if hasattr(result, "__iter__") and not isinstance(result, str):
            full_reply = ""
            for chunk in result:
                full_reply += chunk
                yield chunk
            self.add_assistant_message(full_reply)
        else:
            yield result
            self.add_assistant_message(result)
        # reply = get_completion(self.history)
        # self.add_assistant_message(reply)
        # return reply

    def reset(self):
        self.history = [{"role": "system", "content": self.system_prompt}]

    def set_stream_mode(self, enabled: bool):
        self.use_stream = enabled

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

    # def get_response(self, user_input: str = None) -> str:
    #     if user_input:
    #         self.add_user_message(user_input)
    #     reply = get_completion(self.history)
    #     self.add_assistant_message(reply)
    #     return reply

    # def get_response_stream(self, user_input: str = None) -> str:
    #     if user_input:
    #         self.add_user_message(user_input)
    #     full_reply = ""
    #     for chunk in get_completion_stream(self.history):
    #         full_reply += chunk
    #         yield chunk

            # self.add_assistant_message(full_reply)
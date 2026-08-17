"""
    Neuro-cli
    author@Fedal987
    Powered by HeronStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

from pathlib import Path

from src.main.api.api_manager import (
    API_KEY,
    BASE_URL,
    MODEL,
    REASONING_AUTO_APPROVE,
    REASONING_COMMAND_TIMEOUT,
    REASONING_EFFORT,
    REASONING_ENABLED,
    REASONING_MAX_STEPS,
    REASONING_THINKING,
    STREAM,
    SYSTEM_PROMPT,
    TEMPERATURE,
    get_completion,
    get_completion_stream,
)
from src.main.tool.reasoning import Agent, StreamEvent

class MessageHandler:

    def __init__(self, system_prompt: str = None, reasoning_enabled: bool = REASONING_ENABLED):
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.reasoning_enabled = reasoning_enabled
        self.agent = None
        if self.reasoning_enabled:
            self.agent = Agent(
                api_key=API_KEY,
                workspace=Path.cwd(),
                model=MODEL,
                base_url=BASE_URL,
                thinking=REASONING_THINKING,
                reasoning_effort=REASONING_EFFORT,
                auto_approve=REASONING_AUTO_APPROVE,
                max_steps=REASONING_MAX_STEPS,
                temperature=TEMPERATURE,
                command_timeout=REASONING_COMMAND_TIMEOUT,
            )
            self.history = self.agent.messages
        else:
            self.history = [{"role": "system", "content": self.system_prompt}]
        self.use_stream = STREAM

    def add_user_message(self, text: str):
        if self.agent:
            self.agent.add_user_message(text)
        else:
            self.history.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str):
        self.history.append({"role": "assistant", "content": text})

    def get_response(self, user_input: str = None) -> str:
        if self.agent:
            return self.agent.run(user_input)
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
        if self.agent:
            yield from self.agent.run_stream(user_input)
            return
        if user_input:
            self.add_user_message(user_input)
        full_reply = ""
        for chunk in get_completion_stream(self.history):
            full_reply += chunk
            yield chunk
        self.add_assistant_message(full_reply)

    def get_response_events(self, user_input: str = None):
        if self.agent:
            yield from self.agent.run_stream_events(user_input)
            return
        for chunk in self.get_response_stream(user_input):
            yield StreamEvent("content", chunk)

    def get_response_stream_internal(self, user_input: str = None):
        if self.agent:
            yield from self.agent.run_stream(user_input)
            return
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

    def reset(self):
        if self.agent:
            self.agent.reset()
            self.history = self.agent.messages
        else:
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

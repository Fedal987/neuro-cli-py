"""
    Neuro-cli
    author@Fedal987
    Powered by SigmaStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

import tomli
from openai import OpenAI
from pathlib import Path

from . import prompt_builder

def _load_config():
    config_path = Path(__file__).parents[3] / "config.toml"
    if not config_path.exists():
        config_path = Path.cwd() / "config.toml"
    if not config_path.exists():
        raise FileNotFoundError("未找到 config.toml 配置文件")
    with open(config_path, "r", encoding="utf-8") as f:
        return tomli.loads(f.read())

_config = _load_config()
BASE_URL = _config["API_MANAGER"]["BASE_URL"]
API_KEY = _config["API_MANAGER"]["API_KEY"]
MODEL = _config["API_MANAGER"]["MODEL"]
STREAM = _config["API_MANAGER"]["STREAM"]
TEMPERATURE = _config["API_MANAGER"]["TEMPREATURE"]
SYSTEM_PROMPT = prompt_builder.prompt_building

_client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

def get_completion(messages, stream=False, temperature=None):
    use_stream = stream if stream is not None else STREAM
    try:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=use_stream,
            temperature=temperature if temperature is not None else TEMPERATURE,
        )
        if use_stream:
            def generator():
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return generator()
        else:
            return response.choices[0].message.content
    except Exception as e:
        if use_stream:
            def error_gen():
                yield f"API Error: {str(e)}"
            return error_gen()
        else:
            return f"API Error: {str(e)}"

def get_completion_stream(messages, temperature=None):
    try:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
            temperature=temperature if temperature is not None else TEMPERATURE,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"API Error: {str(e)}"

if __name__ == "__main__":
    print("System Prompt:", SYSTEM_PROMPT)
    test_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "你好，可以给我做个自我介绍吗?"}
    ]
    reply = get_completion(test_messages)
    print(reply)
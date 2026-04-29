"""
    Neuro-cli
    author@Fedal987
    Powered by SigmaStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

import os
import json
from json_repair import repair_json

def get_current_path():
    return os.getcwd()
    # return os.path.dirname(os.path.abspath(__file__))

def llm_msg_reader():
    pass

def parse():

    try:
        return json.loads(raw_text)
    except json.decoder.JSONDecodeError:
        try:
            fixed_str = repair_json(raw_text)
            return json.loads(fixed_str)
        except json.decoder.JSONDecodeError as e:
            print(e)
            return None

# def editor(fixed_str):
#     try:
#         return json.loads(fixed_str)
#     except json.decoder.JSONDecodeError:

if __name__ == "__main__":
    data = parse(
    """
    故事發生在一塊肉，掉下去肉掉下。然後鼠標開始變得奇怪故事發生在海上的輪船 要推理哪個人顯示爸爸姐姐，我哥哥剛開始一塊肉，掉下去肉掉哪個先海上的輪船\n
    要推理哪個人顯示哪個先死 媽媽爸爸姐姐，我哥哥剛開始死 媽媽下。然後鼠標開始變得奇怪??故事發生在一塊肉，\n
    {
        "action": "read",
        "path": "filename",
        "content": "new content or patch"
    }
    掉下去肉掉下。然後鼠標開始變得奇怪故事發生在海上的輪船\n
    """
    )
    print(data)


"""
    Neuro-cli
    author@Fedal987
    Powered by SigmaStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

import os
import json
import difflib
from pathlib import Path
from json_repair import repair_json
from typing import Dict, Any, Optional, Tuple


def get_current_path() -> str:
    return os.getcwd()

def extract_json_from_text(raw_text: str) -> str:
    if "```json" in raw_text:
        start = raw_text.find("```json") + 7
        end = raw_text.find("```", start)
        if end != -1:
            return raw_text[start:end].strip()
    elif "```" in raw_text:
        start = raw_text.find("```") + 3
        end = raw_text.find("```", start)
        if end != -1:
            return raw_text[start:end].strip()
    start_brace = raw_text.find('{')
    end_brace = raw_text.rfind('}')
    if start_brace != -1 and end_brace != -1:
        return raw_text[start_brace:end_brace + 1].strip()
    return raw_text.strip()

def parse(raw_text: str) -> Optional[Dict[str, Any]]:
    try:
        json_str = extract_json_from_text(raw_text)
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            fixed_str = repair_json(json_str)
            return json.loads(fixed_str)
        except Exception as e:
            print(f"[JSON 解析错误] {e}")
            return None

def read_file(file_path: Path) -> Tuple[str, str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), ""
    except Exception as e:
        return "", str(e)


def write_file(file_path: Path, content: str) -> Tuple[bool, str]:
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, f"成功写入 {file_path}"
    except Exception as e:
        return False, str(e)


def append_file(file_path: Path, content: str) -> Tuple[bool, str]:
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)
        return True, f"成功追加内容到 {file_path}"
    except Exception as e:
        return False, str(e)


def replace_in_file(file_path: Path, old_content: str, new_content: str) -> Tuple[bool, str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original = f.read()
        if old_content and new_content:
            updated = original.replace(old_content, new_content)
        else:
            updated = new_content

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated)
        return True, f"成功替换内容到 {file_path}"
    except Exception as e:
        return False, str(e)

def ask_permission(action: str, file_path: str) -> bool:
    print(f"\n[权限请求] LLM 想要执行 {action} 操作于文件: {file_path}")
    response = input("是否允许？(y/n): ").strip().lower()
    return response in ('y', 'yes', '是')


def show_diff_and_confirm(original_content: str, new_content: str, file_path: str) -> bool:
    print(f"\n[修改预览] 文件: {file_path}")
    diff = difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"原文件 {file_path}",
        tofile=f"新文件 {file_path}"
    )
    diff_text = ''.join(diff)
    if diff_text:
        print("差异如下：")
        print(diff_text)
    else:
        print("内容无变化。")
    response = input("确认执行此修改吗？(y/n): ").strip().lower()
    return response in ('y', 'yes', '是')

def editor(raw_text: str, workspace_root: str = None) -> str:
    """
    Args:
        raw_text: LLM 输出的原始文本
        workspace_root: 工作区根目录（防止越权），默认当前目录
    Returns:
        给 LLM 的反馈信息（字符串）
    """
    if workspace_root is None:
        workspace_root = get_current_path()
    workspace_path = Path(workspace_root).resolve()
    action_data = parse(raw_text)
    if not action_data:
        return "无法从回复中解析出有效的 JSON 指令，请确保按照规定的 JSON 格式输出文件操作。"
    action = action_data.get("action")
    path = action_data.get("path")
    content = action_data.get("content", "")
    old_content = action_data.get("old_content", "")  # 可选，用于 replace
    if not action or not path:
        return "JSON 缺少必要字段 (action/path)，请补充完整。"
    try:
        req_path = Path(path)
        if not req_path.is_absolute():
            full_path = (workspace_path / req_path).resolve()
        else:
            full_path = req_path.resolve()

        full_path.relative_to(workspace_path)
    except ValueError:
        return f"路径 '{path}' 超出允许的工作区范围，操作被拒绝。"
    except Exception as e:
        return f"路径解析出错: {e}"

    if action == "read":
        if not ask_permission("读取", str(full_path)):
            return "用户拒绝了文件读取操作。请礼貌地告知用户，或者尝试其他方式。"

        file_content, err = read_file(full_path)
        if err:
            return f"读取文件失败: {err}"
        else:
            return f"文件读取成功，内容如下:\n```\n{file_content}\n```"
    elif action in ("write", "append", "replace"):
        if not ask_permission(action, str(full_path)):
            return f"用户拒绝了 {action} 操作。请停止文件修改，或询问用户是否需要其他帮助。"
        original = ""
        if full_path.exists():
            original, _ = read_file(full_path)
        new_content = ""
        if action == "write":
            new_content = content
        elif action == "append":
            new_content = original + content
        elif action == "replace":
            if old_content:
                new_content = original.replace(old_content, content)
            else:
                new_content = content

        if not show_diff_and_confirm(original, new_content, str(full_path)):
            return "用户取消了文件修改。请询问用户是否需要调整修改方案。"
        success, msg = False, ""
        if action == "write":
            success, msg = write_file(full_path, content)
        elif action == "append":
            success, msg = append_file(full_path, content)
        elif action == "replace":
            success, msg = replace_in_file(full_path, old_content, content)

        if success:
            return f"{msg}\n操作已完成。请告知用户结果。"
        else:
            return f"操作失败: {msg}"
    else:
        return f"不支持的操作类型: {action}，支持 read/write/append/replace。"

def llm_msg_reader(raw_text: str) -> str:
    return editor(raw_text)


if __name__ == "__main__":
    test_input = """
    故事發生在一塊肉，掉下去肉掉下。然後鼠標開始變得奇怪故事發生在海上的輪船 要推理哪個人顯示爸爸姐姐，我哥哥剛開始一塊肉，掉下去肉掉哪個先海上的輪船\n
    要推理哪個人顯示哪個先死 媽媽爸爸姐姐，我哥哥剛開始死 媽媽下。然後鼠標開始變得奇怪??故事發生在一塊肉，\n
    {
        "action": "read",
        "path": "config.toml"
    }
    掉下去肉掉下。然後鼠標開始變得奇怪故事發生在海上的輪船
    """
    result = editor(test_input)
    print("编辑器返回:", result)
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
from typing import Dict, Any, Optional, Tuple, List

debug_mode = False

def contains_json(text: str) -> bool:
    try:
        start = text.find('{')
        if start == -1:
            start = text.find('[')
        if start == -1:
            return False
        end = text.rfind('}')
        if end == -1:
            end = text.rfind(']')
        if end <= start:
            return False
        candidate = text[start:end+1]
        json.loads(candidate)
        return True
    except:
        return False

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
    if start_brace == -1:
        return raw_text.strip()
    depth = 0
    for i in range(start_brace, len(raw_text)):
        if raw_text[i] == "{":
            depth += 1
        elif raw_text[i] == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start_brace:i+1].strip()
    end_brace = raw_text.rfind('}')
    if end_brace != -1:
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
            if debug_mode:
                print(f"[JSON 解析错误] {e}")
            else:
                pass
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

def extract_all_json(text: str) -> List[str]:
    """
    从原始文本中提取所有完整的 JSON 对象或数组。
    支持嵌套 JSON 和字符串内的括号（简单转义处理）。
    返回 JSON 字符串列表。
    """
    results = []
    i = 0
    n = len(text)
    while i < n:
        start = -1
        for j in range(i, n):
            if text[j] == '{' or text[j] == '[':
                start = j
                break
        if start == -1:
            break

        open_char = text[start]
        close_char = '}' if open_char == '{' else ']'
        depth = 0
        in_string = False
        escape = False
        end = start
        for k in range(start, n):
            ch = text[k]
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if ch == open_char:
                    depth += 1
                elif ch == close_char:
                    depth -= 1
                    if depth == 0:
                        end = k
                        break
        if end > start:
            json_candidate = text[start:end+1]
            results.append(json_candidate)
            i = end + 1
        else:
            i = start + 1
    return results

def editor(raw_text: str, workspace_root: str = None) -> str:
    """
    解析 LLM 输出中的多个 JSON 指令，并依次执行文件操作。
    Args:
        raw_text: LLM 输出的原始文本
        workspace_root: 工作区根目录，默认当前目录
    Returns:
        给 LLM 的反馈信息，多个操作的结果用分隔线隔开
    """
    if workspace_root is None:
        workspace_root = get_current_path()
    workspace_path = Path(workspace_root).resolve()

    json_strings = extract_all_json(raw_text)
    if not json_strings:
        return "无法从回复中解析出任何有效的 JSON 指令，请确保按照规定的 JSON 格式输出文件操作。"

    all_feedbacks = []
    for idx, json_str in enumerate(json_strings, 1):
        try:
            fixed_str = repair_json(json_str)
            action_data = json.loads(fixed_str)
        except Exception as e:
            all_feedbacks.append(f"[操作 {idx}] JSON 解析失败: {e}")
            continue

        action = action_data.get("action")
        path = action_data.get("path")
        content = action_data.get("content", "")
        old_content = action_data.get("old_content", "")  # 用于 replace

        if not action or not path:
            all_feedbacks.append(f"[操作 {idx}] JSON 缺少必要字段 (action/path)，已跳过。")
            continue

        try:
            req_path = Path(path)
            if not req_path.is_absolute():
                full_path = (workspace_path / req_path).resolve()
            else:
                full_path = req_path.resolve()
            full_path.relative_to(workspace_path)
        except ValueError:
            all_feedbacks.append(f"[操作 {idx}] 路径 '{path}' 超出允许的工作区范围，操作被拒绝。")
            continue
        except Exception as e:
            all_feedbacks.append(f"[操作 {idx}] 路径解析出错: {e}")
            continue

        if action == "read":
            if not ask_permission("读取", str(full_path)):
                all_feedbacks.append(f"[操作 {idx}] 用户拒绝了文件读取操作。")
                continue

            file_content, err = read_file(full_path)
            if err:
                all_feedbacks.append(f"[操作 {idx}] 读取文件失败: {err}")
            else:
                all_feedbacks.append(f"[操作 {idx}] 文件读取成功，内容如下:\n```\n{file_content}\n```")
        elif action in ("write", "append", "replace"):
            if not ask_permission(action, str(full_path)):
                all_feedbacks.append(f"[操作 {idx}] 用户拒绝了 {action} 操作。")
                continue

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
                all_feedbacks.append(f"[操作 {idx}] 用户取消了文件修改。")
                continue

            success, msg = False, ""
            if action == "write":
                success, msg = write_file(full_path, content)
            elif action == "append":
                success, msg = append_file(full_path, content)
            elif action == "replace":
                success, msg = replace_in_file(full_path, old_content, content)

            if success:
                all_feedbacks.append(f"[操作 {idx}] {msg}")
            else:
                all_feedbacks.append(f"[操作 {idx}] 操作失败: {msg}")
        else:
            all_feedbacks.append(f"[操作 {idx}] 不支持的操作类型: {action}，支持 read/write/append/replace。")

    if not all_feedbacks:
        return "未执行任何有效操作。"
    return "\n---\n".join(all_feedbacks)

def llm_msg_reader(raw_text: str) -> str:
    return editor(raw_text)


if __name__ == "__main__":
    test_input = """
    故事發生在一塊肉，掉下去肉掉下。然後鼠標開始變得奇怪故事發生在海上的輪船 要推理哪個人顯示爸爸姐姐，我哥哥剛開始一塊肉，掉下去肉掉哪個先海上的輪船\n
    要推理哪個人顯示哪個先死 媽媽爸爸姐姐，我哥哥剛開始死 媽媽下。然後鼠標開始變得奇怪??故事發生在一塊肉，\n
    {
        "action": "write",
        "path": "test.toml",
        "content": "伊地知虹夏は、浜路晶による漫画『ぼっち・ざ・ろっく！』およびその派生作品に登場するキャラクターで、アニメ版の声優は鈴代紗弓、実写版では大竹美希が演じている。バンド「結束バンド」のドラマー兼リーダーとして、下北沢高校在学中にバンドを結成し、後藤ひとり、山田リョウ、喜多郁代とともに結束バンドを組む。キャラクターの原型はASIAN KUNG-FU GENERATIONのドラマー、伊地知潔。\n幼少期に母親を亡くし、姉の星歌と二人で支え合って育つ。星歌のバンドライブに影響を受け、ドラムを始める。小学校時代に山田リョウと知り合い、高校時代にバンドを結成したことで生活の困難を乗り越える。ライブハウス「STARRY」で働きながら演奏技術を磨く。大学は芳文大学に進学し、バンド活動を続ける中で録音の壁に直面するが、姉の助言を受け、バンドの核として導く役割を自覚する。\n虹夏は、金髪のサイドポニーテールと赤いヘアバンドがトレードマーク。明るい性格で責任感が強く、メンバー間の調整に優れる。バンド運営の実質的な組織者として、学業のプレッシャーに対処しつつチームの諸問題を処理し、補習授業のサポートや衝突の調和などを通じてバンドの発展を支えている。"
    }
    掉下去肉掉下。然後鼠標開始變得奇怪故事發生在海上的輪船
    {
        "action": "write",
        "path": "test.toml",
        "content": "测试2"
    }
    """
    result = editor(test_input)
    print("编辑器返回:", result)
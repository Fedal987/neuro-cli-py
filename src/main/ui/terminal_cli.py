from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import time

from src.main.api.api_manager import get_completion, SYSTEM_PROMPT, BASE_URL, MODEL
from src.main.msg.message_handler import MessageHandler

# kb = KeyBindings()
#
# @kb.add('enter')
# def _(event):
#     event.current_buffer.validate_and_handle()
#
# @kb.add('shift-enter')
# def _(event):
#     event.current_buffer.insert_text('\n')

HISTORY_FILE = ".neuro_cli_history"
session = PromptSession(
    history=FileHistory(HISTORY_FILE),
    auto_suggest=AutoSuggestFromHistory(),
    lexer=PygmentsLexer(PythonLexer),
    # key_bindings=kb,
    multiline=True,
)
console = Console()

# conversation_history = [
#     {"role": "system", "content": SYSTEM_PROMPT}
# ]

def show_help():
    help_text = f"""
## NEURO-CLI 命令帮助

| 命令 | 说明 |
|------|------|
| `/help` | 显示本帮助 |
| `/exit` | 退出程序 |
| `/clear` | 清屏并重置对话历史 |
| `/reset` | 仅重置对话历史（不清屏） |
| `/echo <内容>` | 回显内容（测试用） |

**多行输入**：按 `Esc` 然后按 `Enter` 提交。  
**历史记录**：上下键浏览。  
**语法高亮**：输入 Python 代码时会自动高亮。
    """
    console.print(Markdown(help_text))

def handle_echo(arg: str):
    if not arg.strip():
        console.print("[yellow]请在 /echo 后面写一些内容[/yellow]")
    else:
        console.print(Panel(arg.strip(), title="[bold]ECHO[/bold]", border_style="cyan"))

def clear_screen():
    console.clear()

# def reset_conversation():
#     global conversation_history
#     conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
#     console.print("[green]对话历史已重置。[/green]")

def main():
    console.clear()
    logo = r"""
███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗      ██████╗██╗     ██╗
████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗    ██╔════╝██║     ██║
██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║    ██║     ██║     ██║
██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║    ██║     ██║     ██║
██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝    ╚██████╗███████╗██║
╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝      ╚═════╝╚══════╝╚═╝
"""
    content = f"""[cyan]{logo}[/cyan]\n\nAn Open-source AI Agent Application With High Performance based on Python \nUse [bold]/help[/bold] to see details...\n\n\nBASE_URL: {BASE_URL} \nMODEL: {MODEL} \n"""
    console.print(Panel.fit(content, border_style="cyan"))
    print("TIP: 默认情况下您处于多行输入环境下，若需要提交文本，请按 Esc 后再按 Enter 来提交")

    msg_handler = MessageHandler()
    while True:
        try:
            user_input = session.prompt("You > ", prompt_continuation="    > ")
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                parts = user_input.strip().split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                if cmd == "/exit":
                    console.print("[bold yellow]再见！[/bold yellow]")
                    break
                elif cmd == "/help":
                    show_help()
                elif cmd == "/clear":
                    clear_screen()
                    msg_handler.reset()  # 重置对话历史
                elif cmd == "/reset":
                    msg_handler.reset()
                elif cmd == "/echo":
                    handle_echo(arg)
                else:
                    console.print(f"[red]未知命令: {cmd}[/red] 输入 /help 查看帮助")
                continue
            with console.status("[bold blue]Neuro祈祷中...[/bold blue]"):
                time.sleep(0.1)
                # reply = msg_handler.get_response(user_input)  # 核心调用
            console.print("\n[bold magenta]Neuro[/bold magenta] > ", end="")
            full_reply = ""
            for chunk in msg_handler.get_response_stream(user_input):
                print(chunk, end='', flush=True)
                full_reply += chunk
            console.print()
            # if "```" in reply:
            #     console.print(Markdown(reply))
            # else:
            #     console.print(Text(reply, style="bright_white"))
            # console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]按 Ctrl+C 再次退出，或输入 /exit[/dim]")
            continue
        except EOFError:
            console.print("\n[bold yellow]检测到退出信号，再见！[/bold yellow]")
            break

if __name__ == "__main__":
    main()
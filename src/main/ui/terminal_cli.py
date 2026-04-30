"""
    Neuro-cli
    author@Fedal987
    Powered by SigmaStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import time

from src.main.api.api_manager import BASE_URL, MODEL
from src.main.msg.message_handler import MessageHandler
from src.main.tool.file_editor import editor, get_current_path

HISTORY_FILE = ".neuro_cli_history"
session = PromptSession(
    history=FileHistory(HISTORY_FILE),
    auto_suggest=AutoSuggestFromHistory(),
    lexer=PygmentsLexer(PythonLexer),
    # key_bindings=kb,
    multiline=True,
)
console = Console()

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
    content = f"""[cyan]{logo}[/cyan]\n\nAn Open-source AI Agent Application With High Performance(迫真) based on Python \nUse [bold]/help[/bold] to see details...\n\n\nBASE_URL: {BASE_URL} \nMODEL: {MODEL} \nCURRENT_DIR: {get_current_path()} \n"""
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
            console.print("\n[bold magenta]Neuro[/bold magenta] > ", end="")

            if msg_handler.use_stream:
                full_stream_reply = ""
                for chunk in msg_handler.get_response_stream(user_input):
                    print(chunk, end="", flush=True)
                    full_stream_reply += chunk
                console.print()
                # TODO: 在此注释下的代码添加条件 判断llm输出的文本是否有json 避免token浪费
                feedback = editor(full_stream_reply)
                if feedback and not feedback.startswith("无法从您的回复中解析"):
                    msg_handler.add_user_message(feedback)
                    console.print("[bold magenta]Neuro[/bold magenta] > ", end="")
                    final_reply = msg_handler.get_response()
                    console.print(final_reply)
                    console.print()
            else:
                with console.status("[bold blue]Neuro祈祷中...[/bold blue]"):
                    reply = msg_handler.get_response(user_input)
                console.print(reply)
                console.print()
                # TODO: 在此注释下的代码添加条件 判断llm输出的文本是否有json 避免token浪费
                feedback = editor(reply)
                if feedback and not feedback.startswith("无法从您的回复中解析"):
                    msg_handler.add_user_message(feedback)
                    console.print("[bold magenta]Neuro[/bold magenta] > ", end="")
                    with console.status("[bold blue]Neuro处理中...[/bold blue]"):
                        final_reply = msg_handler.get_response()
                    console.print(final_reply)
                    console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]按 Ctrl+C 再次退出，或输入 /exit[/dim]")
            continue
        except EOFError:
            console.print("\n[bold yellow]检测到退出信号，再见！[/bold yellow]")
            break

if __name__ == "__main__":
    main()
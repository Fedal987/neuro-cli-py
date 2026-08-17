"""
    Neuro-cli
    author@Fedal987
    Powered by HeronStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from itertools import chain
import time

from src.main.api.api_manager import BASE_URL, MODEL
from src.main.msg.message_handler import MessageHandler
from src.main.tool.file_editor import editor, get_current_path, parse

HISTORY_FILE = ".neuro_cli_history"
session = PromptSession(
    history=FileHistory(HISTORY_FILE),
    auto_suggest=AutoSuggestFromHistory(),
    lexer=PygmentsLexer(PythonLexer),
    multiline=True,
)
console = Console()


class MarkdownStreamRenderer:
    """Re-render accumulated Markdown whenever a new stream chunk arrives."""

    def __init__(self, target_console: Console, refresh_interval: float = 0.08):
        self.console = target_console
        self.parts: list[str] = []
        self.live: Live | None = None
        self.refresh_interval = refresh_interval
        self.last_rendered_at = 0.0
        self.dirty = False

    def update(self, chunk: str) -> None:
        self.parts.append(chunk)
        self.dirty = True
        now = time.monotonic()
        if self.live is None:
            self._render(now, start=True)
        elif now - self.last_rendered_at >= self.refresh_interval:
            self._render(now)

    def _render(self, now: float, start: bool = False, refresh: bool = False) -> None:
        renderable = Markdown("".join(self.parts))
        if start:
            self.live = Live(
                renderable,
                console=self.console,
                refresh_per_second=12,
                transient=False,
                redirect_stdout=False,
                redirect_stderr=False,
            )
            self.live.start()
        elif self.live is not None:
            self.live.update(renderable, refresh=refresh)
        self.last_rendered_at = now
        self.dirty = False

    def stop(self) -> str:
        if self.live is not None:
            if self.dirty:
                self._render(time.monotonic(), refresh=True)
            self.live.stop()
            self.live = None
        return "".join(self.parts)

def contains_json(text: str) -> bool:
    return parse(text) is not None

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
        markdown_renderer = None
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
                    msg_handler.reset()
                elif cmd == "/reset":
                    msg_handler.reset()
                elif cmd == "/echo":
                    handle_echo(arg)
                else:
                    console.print(f"[red]未知命令: {cmd}[/red] 输入 /help 查看帮助")
                continue
            if msg_handler.use_stream:
                full_stream_reply = ""
                if msg_handler.reasoning_enabled:
                    displayed_kind = None
                    markdown_renderer = MarkdownStreamRenderer(console)
                    events = iter(msg_handler.get_response_events(user_input))
                    with console.status("[bold blue]Neuro 等待模型响应...[/bold blue]"):
                        first_event = next(events, None)
                    event_stream = chain((first_event,), events) if first_event is not None else ()
                    for event in event_stream:
                        if event.kind == "reasoning":
                            if displayed_kind != "reasoning":
                                if displayed_kind == "content":
                                    markdown_renderer.stop()
                                    markdown_renderer = MarkdownStreamRenderer(console)
                                if displayed_kind is not None:
                                    console.print()
                                leading_newline = "\n" if displayed_kind is None else ""
                                console.print(
                                    f"{leading_newline}[dim italic cyan]Neuro 思考[/dim italic cyan] > ",
                                    end="",
                                )
                                displayed_kind = "reasoning"
                            console.print(
                                event.content,
                                end="",
                                style="dim italic cyan",
                                markup=False,
                            )
                        elif event.kind == "content":
                            if displayed_kind != "content":
                                if displayed_kind is not None:
                                    console.print()
                                leading_newline = "\n" if displayed_kind is None else ""
                                console.print(
                                    f"{leading_newline}[bold magenta]Neuro[/bold magenta] >"
                                )
                                displayed_kind = "content"
                            markdown_renderer.update(event.content)
                            full_stream_reply += event.content
                        elif event.kind in {"tool", "tool_result"}:
                            if displayed_kind == "content":
                                markdown_renderer.stop()
                                markdown_renderer = MarkdownStreamRenderer(console)
                            if displayed_kind is not None:
                                console.print()
                            label = "Neuro 工具" if event.kind == "tool" else "工具结果"
                            style = "dim yellow" if event.kind == "tool" else "dim green"
                            console.print(f"[{style}]{label}[/] > ", end="")
                            console.print(event.content, style=style, markup=False)
                            displayed_kind = event.kind
                        else:
                            if displayed_kind == "content":
                                markdown_renderer.stop()
                                markdown_renderer = MarkdownStreamRenderer(console)
                            if displayed_kind is not None:
                                console.print()
                            leading_newline = "\n" if displayed_kind is None else ""
                            console.print(
                                f"{leading_newline}[bold red]Neuro 错误[/bold red] > ",
                                end="",
                            )
                            console.print(
                                event.content,
                                style="bold red",
                                markup=False,
                            )
                            displayed_kind = "error"
                            full_stream_reply += event.content
                    markdown_renderer.stop()
                    if displayed_kind is None:
                        console.print("\n[bold magenta]Neuro[/bold magenta] > ", end="")
                else:
                    console.print("\n[bold magenta]Neuro[/bold magenta] >")
                    markdown_renderer = MarkdownStreamRenderer(console)
                    chunks = iter(msg_handler.get_response_stream(user_input))
                    with console.status("[bold blue]Neuro 等待模型响应...[/bold blue]"):
                        first_chunk = next(chunks, None)
                    chunk_stream = chain((first_chunk,), chunks) if first_chunk is not None else ()
                    for chunk in chunk_stream:
                        markdown_renderer.update(chunk)
                        full_stream_reply += chunk
                    markdown_renderer.stop()
                console.print()
                if not msg_handler.reasoning_enabled and contains_json(full_stream_reply):
                    feedback = editor(full_stream_reply)
                    if not feedback.startswith("无法从您的回复中解析"):
                        msg_handler.add_user_message(feedback)
                        console.print("[bold magenta]Neuro[/bold magenta] >")
                        final_reply = msg_handler.get_response()
                        console.print(Markdown(final_reply))
                        console.print()
            else:
                with console.status("[bold blue]Neuro祈祷中...[/bold blue]"):
                    reply = msg_handler.get_response(user_input)
                console.print("\n[bold magenta]Neuro[/bold magenta] >")
                console.print(Markdown(reply))
                console.print()
                if not msg_handler.reasoning_enabled and contains_json(reply):
                    feedback = editor(reply)
                    if not feedback.startswith("无法从您的回复中解析"):
                        msg_handler.add_user_message(feedback)
                        console.print("[bold magenta]Neuro[/bold magenta] >")
                        with console.status("[bold blue]Neuro处理中...[/bold blue]"):
                            final_reply = msg_handler.get_response()
                        console.print(Markdown(final_reply))
                        console.print()

        except KeyboardInterrupt:
            if markdown_renderer is not None:
                markdown_renderer.stop()
            console.print("\n[dim]按 Ctrl+C 再次退出，或输入 /exit[/dim]")
            continue
        except EOFError:
            if markdown_renderer is not None:
                markdown_renderer.stop()
            console.print("\n[bold yellow]检测到退出信号，再见！[/bold yellow]")
            break

if __name__ == "__main__":
    main()

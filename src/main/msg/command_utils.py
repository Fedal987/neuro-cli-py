
from __future__ import annotations
from collections.abc import Callable
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from src.main.msg.session_manager import SessionManager


class CommandManager:
    def __init__(self, console: Console, session_manager: SessionManager) -> None:
        self.console = console
        self.session_manager = session_manager
        self._commands: dict[str, Callable[[str], bool]] = {
            "/help": self._show_help,
            "/exit": self._exit,
            "/clear": self._clear,
            "/reset": self._reset,
            "/echo": self._echo,
            "/session": self._session,
        }

    def execute(self, user_input: str) -> bool:
        parts = user_input.strip().split(maxsplit=1)
        command = parts[0].lower()
        argument = parts[1] if len(parts) > 1 else ""
        handler = self._commands.get(command)
        if handler is None:
            self.console.print(
                f"[red]未知命令: {command}[/red] 输入 /help 查看帮助"
            )
            return False
        return handler(argument)

    def _show_help(self, _argument: str) -> bool:
        help_text = """
## NEURO-CLI 命令帮助

| 命令 | 说明 |
|------|------|
| `/help` | 显示本帮助 |
| `/exit` | 退出程序 |
| `/clear` | 清屏并重置当前 session |
| `/reset` | 重置当前 session（不清屏） |
| `/echo <内容>` | 回显内容（测试用） |
| `/session` | 查看当前目录的 session |
| `/session list` | 查看当前目录的 session |
| `/session <名称或编号>` | 切换 session |
| `/session new [名称]` | 创建并切换；省略名称时首轮对话后由 LLM 命名 |

**输入方式**：按 `Enter` 提交，按 `Shift+Enter` 换行（兼容 `Esc+Enter`）。
**历史记录**：上下键浏览。
**语法高亮**：输入 Python 代码时会自动高亮。
        """
        self.console.print(Markdown(help_text))
        return False

    def _exit(self, _argument: str) -> bool:
        self.console.print("[bold yellow]再见！[/bold yellow]")
        return True

    def _clear(self, _argument: str) -> bool:
        self.console.clear()
        self.session_manager.reset_current_session()
        return False

    def _reset(self, _argument: str) -> bool:
        if not self.session_manager.has_current_session:
            self.console.print("[dim]当前没有活动的 session[/dim]")
            return False
        self.session_manager.reset_current_session()
        self.console.print(
            f"[green]session {self.session_manager.current_name!r} 已重置[/green]"
        )
        return False

    def _echo(self, argument: str) -> bool:
        if not argument.strip():
            self.console.print("[yellow]请在 /echo 后面写一些内容[/yellow]")
        else:
            self.console.print(
                Panel(
                    argument.strip(),
                    title="[bold]ECHO[/bold]",
                    border_style="cyan",
                )
            )
        return False

    def _session(self, argument: str) -> bool:
        argument = argument.strip()
        if not argument or argument.lower() == "list":
            self._show_sessions()
            return False

        subcommand = argument.split(maxsplit=1)
        if subcommand[0].lower() == "new":
            name = subcommand[1] if len(subcommand) > 1 else None
            try:
                selected = self.session_manager.create_session(name)
            except (OSError, TypeError, ValueError) as exc:
                self.console.print(f"[red]创建 session 失败：{exc}[/red]")
                return False
            self.console.print(
                f"[green]已创建并切换到 session {selected.name!r}[/green]"
            )
            return False

        target: str | int = int(argument) if argument.isdigit() else argument
        try:
            selected = self.session_manager.switch_session(
                target,
                workspace=self.session_manager.current_workspace,
            )
        except (OSError, TypeError, ValueError, IndexError, KeyError) as exc:
            self.console.print(f"[red]切换 session 失败：{exc}[/red]")
            return False
        self.console.print(f"[green]已切换到 session {selected.name!r}[/green]")
        return False

    def _show_sessions(self) -> None:
        workspace = self.session_manager.current_workspace
        sessions = self.session_manager.list_sessions(workspace=workspace)
        self.console.print(f"[bold]当前目录的 sessions：[/bold] {workspace}")
        if not sessions:
            self.console.print("[dim]当前目录还没有 session[/dim]")
            return
        for index, session in enumerate(sessions, start=1):
            temporary = " [yellow](临时)[/yellow]" if session.temporary else ""
            marker = " [green](当前)[/green]" if (
                session.name == self.session_manager.current_name
            ) else ""
            self.console.print(f"  {index}. {session.name}{temporary}{marker}")

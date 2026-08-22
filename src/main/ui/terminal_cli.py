"""
    Neuro-cli
    author@Fedal987
    Powered by HeronStudio
    GitHub: https://github.com/Fedal987/neuro-cli-py
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers import PythonLexer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from itertools import chain
import os
import sys
import time
from typing import TextIO

from src.main.api.api_manager import (
    BASE_URL,
    MODEL,
    REASONING_EFFORT,
    REASONING_ENABLED,
)
from src.main.ui.i18n import LANGUAGE_NAMES, get_language, set_language, tr
from src.main.msg.command_utils import CommandManager
from src.main.msg.session_manager import SessionManager
from src.main.tool.file_editor import editor, get_current_path, parse

for shift_enter_sequence in ("\x1b[27;2;13~", "\x1b[13;2u"):
    ANSI_SEQUENCES[shift_enter_sequence] = (Keys.Escape, Keys.ControlM)
for letter_index, letter in enumerate("abcdefghijklmnopqrstuvwxyz", start=1):
    control_key = getattr(Keys, f"Control{letter.upper()}")
    ANSI_SEQUENCES[f"\x1b[{ord(letter)};5u"] = control_key
    ANSI_SEQUENCES[f"\x1b[{ord(letter)};6u"] = control_key
ANSI_SEQUENCES["\x1b[27u"] = Keys.Escape
ANSI_SEQUENCES["\x1b[32;5u"] = Keys.ControlAt
ANSI_SEQUENCES["\x1b[91;5u"] = Keys.Escape
ANSI_SEQUENCES["\x1b[92;5u"] = Keys.ControlBackslash
ANSI_SEQUENCES["\x1b[93;5u"] = Keys.ControlSquareClose
input_key_bindings = KeyBindings()

@input_key_bindings.add("enter")

def submit_input(event) -> None:
    event.current_buffer.validate_and_handle()

@input_key_bindings.add("escape", "enter")
@input_key_bindings.add("c-j")

def insert_line_break(event) -> None:
    event.current_buffer.insert_text("\n")

def enable_enhanced_keyboard_protocol(
    stream: TextIO | None = None,
) -> str | None:
    output = stream or sys.stdout
    if not output.isatty():
        return None

    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    kitty_protocol = (
        any(name in term for name in ("kitty", "foot", "ghostty", "wezterm"))
        or term_program in {"kitty", "foot", "ghostty", "wezterm"}
        or any(
            variable in os.environ
            for variable in ("KITTY_WINDOW_ID", "WEZTERM_PANE", "GHOSTTY_RESOURCES_DIR")
        )
    )
    if kitty_protocol:
        output.write("\x1b[>1u")
        protocol = "kitty"
    elif term and term != "dumb":
        output.write("\x1b[>4;2m")
        protocol = "xterm"
    else:
        return None
    output.flush()
    return protocol

def disable_enhanced_keyboard_protocol(
    protocol: str | None,
    stream: TextIO | None = None,
) -> None:
    if protocol is None:
        return
    output = stream or sys.stdout
    output.write("\x1b[<u" if protocol == "kitty" else "\x1b[>4;0m")
    output.flush()
console = Console()
LOGO = r"""
███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗      ██████╗██╗     ██╗
████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗    ██╔════╝██║     ██║
██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║    ██║     ██║     ██║
██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║    ██║     ██║     ██║
██║ ╚████║███████╗╚██████╔╝██║  ██║╚██████╔╝    ╚██████╗███████╗██║
╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝      ╚═════╝╚══════╝╚═╝
"""

class MarkdownStreamRenderer:
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

def build_bottom_toolbar() -> str:
    reasoning_effort = REASONING_EFFORT or tr("reasoning_default")
    if not REASONING_ENABLED:
        reasoning_effort = tr("reasoning_off")
    return (
        f" {MODEL} {reasoning_effort} · {get_current_path()}"
    )


def render_welcome() -> None:
    """Clear the terminal and redraw the startup panel in the active language."""
    console.clear()
    content = (
        f"[cyan]{LOGO}[/cyan]\n\n{tr('tagline')}\n"
        f"{tr('help_hint')}\n\n\n"
        f"{tr('base_url')}: {BASE_URL}\n"
        f"{tr('model')}: {MODEL}\n"
        f"{tr('current_dir')}: {get_current_path()}\n"
    )
    console.print(Panel.fit(content, border_style="cyan"))
    console.print()


def main():
    render_welcome()

    session_manager = SessionManager()
    command_manager = CommandManager(
        console,
        session_manager,
        translator=tr,
        language_getter=get_language,
        language_setter=set_language,
        language_names=LANGUAGE_NAMES,
        language_changed_callback=render_welcome,
    )
    session = PromptSession(
        history=session_manager.prompt_history,
        auto_suggest=AutoSuggestFromHistory(),
        key_bindings=input_key_bindings,
        lexer=PygmentsLexer(PythonLexer),
        multiline=True,
    )
    while True:
        markdown_renderer = None
        try:
            keyboard_protocol = enable_enhanced_keyboard_protocol()
            try:
                user_input = session.prompt(
                    tr("user_prompt"),
                    prompt_continuation="    > ",
                    bottom_toolbar=build_bottom_toolbar,
                )
            finally:
                disable_enhanced_keyboard_protocol(keyboard_protocol)
            if not user_input.strip():
                continue
            if user_input.startswith("/"):
                if command_manager.execute(user_input):
                    break
                continue
            session_manager.ensure_current_session()
            session_manager.activate_current_session()
            msg_handler = session_manager.current_handler
            if msg_handler.use_stream:
                full_stream_reply = ""
                if msg_handler.reasoning_enabled:
                    displayed_kind = None
                    markdown_renderer = MarkdownStreamRenderer(console)
                    events = iter(msg_handler.get_response_events(user_input))
                    with console.status(f"[bold blue]{tr('waiting')}[/bold blue]"):
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
                                    f"{leading_newline}[dim italic cyan]{tr('thinking')}[/dim italic cyan]\n > ",
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
                            label = tr("tool_call") if event.kind == "tool" else tr("tool_result")
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
                                f"{leading_newline}[bold red]{tr('error')}: [/bold red] > ",
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
                    with console.status(f"[bold blue]{tr('waiting')}[/bold blue]"):
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
                with console.status(f"[bold blue]{tr('waiting')}[/bold blue]"):
                    reply = msg_handler.get_response(user_input)
                console.print("\n[bold magenta]Neuro[/bold magenta] >")
                console.print(Markdown(reply))
                console.print()
                if not msg_handler.reasoning_enabled and contains_json(reply):
                    feedback = editor(reply)
                    if not feedback.startswith("无法从您的回复中解析"):
                        msg_handler.add_user_message(feedback)
                        console.print("[bold magenta]Neuro[/bold magenta] >")
                        with console.status(f"[bold blue]{tr('processing')}[/bold blue]"):
                            final_reply = msg_handler.get_response()
                        console.print(Markdown(final_reply))
                        console.print()

        except KeyboardInterrupt:
            if markdown_renderer is not None:
                markdown_renderer.stop()
            console.print(f"\n[dim]{tr('interrupt_hint')}[/dim]")
            continue
        except EOFError:
            if markdown_renderer is not None:
                markdown_renderer.stop()
            console.print(f"\n[bold yellow]{tr('goodbye')}[/bold yellow]")
            break
        finally:
            try:
                session_manager.save_current_session()
            except (OSError, TypeError, ValueError) as exc:
                console.print(
                    f"[bold red]{tr('session_save_failed', error=exc)}[/bold red]"
                )

if __name__ == "__main__":
    main()

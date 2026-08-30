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
from rich.panel import Panel
import os
import sys
from typing import TextIO

from src.main.api.api_manager import (
    BASE_URL,
    MODEL,
    REASONING_EFFORT,
    REASONING_ENABLED,
    USAGE_TRACKER,
)
from src.main.ui.i18n import LANGUAGE_NAMES, get_language, set_language, tr
from src.main.ui.conversation_input import ConversationInput
from src.main.msg.command_utils import CommandManager
from src.main.msg.session_manager import SessionManager
from src.main.tool.toolcall_utils import get_current_path

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


def build_exit_message() -> str:
    usage = USAGE_TRACKER.snapshot()
    return tr(
        "exit_summary",
        total_tokens=f"{usage.total_tokens:,}",
        cached_tokens=f"{usage.cached_tokens:,}",
        cache_hit_rate=f"{usage.cache_hit_rate:.2f}%",
    )


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
        exit_message_getter=build_exit_message,
    )
    session = PromptSession(
        history=session_manager.prompt_history,
        auto_suggest=AutoSuggestFromHistory(),
        key_bindings=input_key_bindings,
        lexer=PygmentsLexer(PythonLexer),
        multiline=True,
    )
    while True:
        conversation_input = None
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
            conversation_input = ConversationInput(
                lambda: tr("user_prompt"),
                msg_handler.queue_user_message,
                lambda: conversation_input.append_output(
                    f"\n{tr('escape_interrupt_hint')}\n",
                    "class:interrupt",
                ),
                msg_handler.interrupt,
                bottom_toolbar=build_bottom_toolbar,
            )
            msg_handler.set_interaction_callbacks(
                conversation_input.stop,
                conversation_input.start,
            )
            conversation_input.start()
            if msg_handler.use_stream:
                if msg_handler.reasoning_enabled:
                    displayed_kind = None
                    for event in msg_handler.get_response_events(user_input):
                        if event.kind == "reasoning":
                            if displayed_kind != "reasoning":
                                conversation_input.append_output(
                                    f"\n{tr('thinking')}\n",
                                    "class:reasoning-title",
                                )
                                displayed_kind = "reasoning"
                            conversation_input.append_output(
                                event.content,
                                "class:reasoning",
                            )
                        elif event.kind == "content":
                            if displayed_kind != "content":
                                conversation_input.append_output(
                                    "\nNeuro >\n",
                                    "class:answer-title",
                                )
                                displayed_kind = "content"
                            conversation_input.append_markdown(event.content)
                        elif event.kind in {"tool", "tool_result"}:
                            label = tr("tool_call") if event.kind == "tool" else tr("tool_result")
                            conversation_input.append_output(
                                f"\n{label} > {event.content}\n",
                                "class:tool" if event.kind == "tool" else "class:tool-result",
                            )
                            displayed_kind = event.kind
                        elif event.kind == "interrupted":
                            conversation_input.append_output(
                                f"\n{event.content}\n",
                                "class:interrupt",
                            )
                            displayed_kind = "interrupted"
                        elif event.kind == "queued_user":
                            conversation_input.append_output(
                                f"\n{tr('user_prompt')}{event.content}\n",
                                "class:user",
                            )
                            displayed_kind = "queued_user"
                        else:
                            conversation_input.append_output(
                                f"\n{tr('error')} > {event.content}\n",
                                "class:error",
                            )
                            displayed_kind = "error"
                    if displayed_kind is None:
                        conversation_input.append_output(
                            "\nNeuro >\n",
                            "class:answer-title",
                        )
                else:
                    conversation_input.append_output(
                        "\nNeuro >\n",
                        "class:answer-title",
                    )
                    for chunk in msg_handler.get_response_stream(user_input):
                        conversation_input.append_markdown(chunk)
                conversation_input.append_output("\n")
            else:
                reply = msg_handler.get_response(user_input)
                conversation_input.append_output(
                    "\nNeuro >\n",
                    "class:answer-title",
                )
                conversation_input.append_markdown(reply)
                conversation_input.append_output("\n")
        except KeyboardInterrupt:
            if conversation_input is not None:
                conversation_input.append_output(f"\n{build_exit_message()}\n")
            else:
                console.print(f"\n[bold yellow]{build_exit_message()}[/bold yellow]")
            break
        except EOFError:
            console.print(f"\n[bold yellow]{build_exit_message()}[/bold yellow]")
            break
        finally:
            if conversation_input is not None:
                conversation_input.stop()
                msg_handler.set_interaction_callbacks(None, None)
                if conversation_input.transcript:
                    conversation_input.render_transcript(console)
            try:
                session_manager.save_current_session()
            except (OSError, TypeError, ValueError) as exc:
                console.print(
                    f"[bold red]{tr('session_save_failed', error=exc)}[/bold red]"
                )

if __name__ == "__main__":
    main()

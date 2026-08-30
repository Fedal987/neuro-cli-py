from __future__ import annotations

import os
import signal
import threading
from collections.abc import Callable
from io import StringIO
from typing import Any

from prompt_toolkit.application import Application, get_app
from prompt_toolkit.formatted_text import ANSI, FormattedText, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea
from rich.console import Console
from rich.markdown import Markdown
from src.main.ui.interrupt_handler import DoubleEscapeDetector


class ConversationInput:
    def __init__(
        self,
        prompt: Callable[[], str],
        on_submit: Callable[[str], None],
        on_first_escape: Callable[[], None],
        on_interrupt: Callable[[], None],
        bottom_toolbar: Callable[[], str] | None = None,
        toolkit_input: Any = None,
        toolkit_output: Any = None,
    ) -> None:
        self.prompt = prompt
        self.on_submit = on_submit
        self.on_first_escape = on_first_escape
        self.on_interrupt = on_interrupt
        self.bottom_toolbar = bottom_toolbar
        self.toolkit_input = toolkit_input
        self.toolkit_output = toolkit_output
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._application: Any = None
        self._application_lock = threading.Lock()
        self._draft = ""
        self._transcript = ""
        self._transcript_lock = threading.Lock()
        self._blocks: list[dict[str, Any]] = []
        self._input_area: TextArea | None = None
        self._output_area: Window | None = None
        self._escape_detector = DoubleEscapeDetector()
        self._render_condition = threading.Condition()
        self._revision = 0
        self._displayed_revision = 0
        self._rendered_revision = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._escape_detector.reset()
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._application_lock:
            application = self._application
            if self._input_area is not None:
                self._draft = self._input_area.text
        if application is not None:
            self._exit_application(application)
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1.5)
            if not thread.is_alive():
                self._thread = None
        self._escape_detector.reset()

    @property
    def transcript(self) -> str:
        with self._transcript_lock:
            return self._transcript

    def append_output(self, text: str, style: str = "") -> None:
        if not text:
            return
        self.finalize_markdown()
        with self._transcript_lock:
            self._transcript += text
            if (
                self._blocks
                and self._blocks[-1]["kind"] == "plain"
                and self._blocks[-1]["style"] == style
            ):
                self._blocks[-1]["text"] += text
            else:
                self._blocks.append(
                    {"kind": "plain", "style": style, "text": text}
                )
        self._publish_update()

    def append_markdown(self, text: str) -> None:
        if not text:
            return
        with self._transcript_lock:
            self._transcript += text
            if self._blocks and self._blocks[-1]["kind"] == "markdown":
                self._blocks[-1]["text"] += text
            else:
                self._blocks.append(
                    {
                        "kind": "markdown",
                        "text": text,
                        "rendered": [],
                        "rendered_text": "",
                    }
                )
        self._publish_update()

    def finalize_markdown(self) -> None:
        with self._transcript_lock:
            if not self._blocks or self._blocks[-1]["kind"] != "markdown":
                return
            index = len(self._blocks) - 1
            text = self._blocks[index]["text"]
            if self._blocks[index].get("rendered_text") == text:
                return
        rendered = self._markdown_fragments(text)
        with self._transcript_lock:
            if index < len(self._blocks) and self._blocks[index]["text"] == text:
                self._blocks[index]["rendered"] = rendered
                self._blocks[index]["rendered_text"] = text
        self._publish_update(wait=False)

    def render_transcript(self, console: Console) -> None:
        with self._transcript_lock:
            blocks = [dict(block) for block in self._blocks]
        rich_styles = {
            "class:reasoning": "dim italic cyan",
            "class:reasoning-title": "bold italic cyan",
            "class:answer-title": "bold magenta",
            "class:tool": "dim yellow",
            "class:tool-result": "dim green",
            "class:user": "bold cyan",
            "class:error": "bold red",
            "class:interrupt": "bold yellow",
        }
        for block in blocks:
            if block["kind"] == "markdown":
                console.print(Markdown(block["text"]))
            else:
                console.print(
                    block["text"],
                    style=rich_styles.get(block["style"]),
                    markup=False,
                    end="",
                )

    def _publish_update(self, wait: bool = True) -> None:
        with self._render_condition:
            self._revision += 1
            revision = self._revision
        active = self._invalidate()
        if not wait or not active or threading.current_thread() is self._thread:
            return
        with self._render_condition:
            self._render_condition.wait_for(
                lambda: self._rendered_revision >= revision,
                timeout=0.15,
            )

    def _invalidate(self) -> bool:
        with self._application_lock:
            application = self._application
            output_area = self._output_area
        if application is None or output_area is None:
            return False

        loop = getattr(application, "loop", None)
        if loop is not None and loop.is_running():
            output_area.vertical_scroll = 10**9
            application.invalidate()
            return True
        return False

    def _formatted_output(self):
        with self._transcript_lock:
            blocks = [dict(block) for block in self._blocks]
        with self._render_condition:
            self._displayed_revision = self._revision
        fragments: list[tuple[str, str]] = []
        for index, block in enumerate(blocks):
            if block["kind"] == "plain":
                fragments.append((block["style"], block["text"]))
                continue
            text = block["text"]
            rendered_text = block.get("rendered_text", "")
            rendered = block.get("rendered", [])
            complete_length = text.rfind("\n") + 1
            complete_text = text[:complete_length]
            if complete_text != rendered_text and not rendered_text.startswith(complete_text):
                rendered = self._markdown_fragments(complete_text)
                rendered_text = complete_text
                with self._transcript_lock:
                    if index < len(self._blocks) and self._blocks[index]["text"] == text:
                        self._blocks[index]["rendered"] = rendered
                        self._blocks[index]["rendered_text"] = rendered_text
            fragments.extend(rendered)
            if len(rendered_text) < len(text):
                fragments.append(("", text[len(rendered_text):]))
        return FormattedText(fragments)

    @staticmethod
    def _markdown_fragments(text: str) -> list[tuple[str, str]]:
        target = StringIO()
        renderer = Console(
            file=target,
            force_terminal=True,
            color_system="truecolor",
            width=100,
        )
        renderer.print(Markdown(text), end="")
        raw_fragments = list(to_formatted_text(ANSI(target.getvalue())))
        compacted: list[tuple[str, str]] = []
        line: list[tuple[str, str]] = []
        for style, value in raw_fragments:
            for character in value:
                if character == "\n":
                    while line and line[-1][1].isspace():
                        line.pop()
                    compacted.extend(line)
                    compacted.append(("", "\n"))
                    line = []
                else:
                    line.append((style, character))
        while line and line[-1][1].isspace():
            line.pop()
        compacted.extend(line)
        merged: list[tuple[str, str]] = []
        for style, value in compacted:
            if merged and merged[-1][0] == style:
                merged[-1] = (style, merged[-1][1] + value)
            else:
                merged.append((style, value))
        return merged

    def _thread_main(self) -> None:
        try:
            self._run()
        finally:
            if self._thread is threading.current_thread():
                self._thread = None

    def _run(self) -> None:
        bindings = KeyBindings()

        @bindings.add("escape", eager=True)
        def handle_escape(_event) -> None:
            if self._escape_detector.press():
                self.on_interrupt()
            else:
                self.on_first_escape()

        @bindings.add("c-c", eager=True)
        def force_exit(_event) -> None:
            os.kill(os.getpid(), signal.SIGINT)

        def accept_input(buffer) -> bool:
            text = buffer.text
            buffer.reset()
            self._draft = ""
            self._escape_detector.reset()
            if text.strip():
                self.on_submit(text)
            return True

        output_area = Window(
            content=FormattedTextControl(self._formatted_output),
            wrap_lines=True,
            always_hide_cursor=True,
            height=Dimension(min=3, preferred=12),
        )
        input_area = TextArea(
            text=self._draft,
            prompt=lambda: FormattedText([("class:user", self.prompt())]),
            multiline=False,
            accept_handler=accept_input,
            height=1,
        )
        toolbar = Window(
            content=FormattedTextControl(
                lambda: FormattedText(
                    [
                        (
                            "class:bottom-toolbar",
                            self.bottom_toolbar() if self.bottom_toolbar else "",
                        )
                    ]
                )
            ),
            height=1,
            style="class:bottom-toolbar",
        )
        application = Application(
            layout=Layout(
                HSplit([output_area, input_area, toolbar]),
                focused_element=input_area,
            ),
            key_bindings=bindings,
            full_screen=False,
            erase_when_done=True,
            max_render_postpone_time=None,
            refresh_interval=0.03,
            after_render=self._after_render,
            input=self.toolkit_input,
            output=self.toolkit_output,
            style=Style.from_dict(
                {
                    "reasoning": "fg:#5fafd7 italic",
                    "reasoning-title": "fg:#5fafd7 bold italic",
                    "answer-title": "fg:#d75fd7 bold",
                    "tool": "fg:#d7af5f",
                    "tool-result": "fg:#5faf87",
                    "user": "fg:#5fd7d7 bold",
                    "error": "fg:#ff5f5f bold",
                    "interrupt": "fg:#d7af5f bold",
                    "bottom-toolbar": "reverse",
                }
            ),
        )
        application.ttimeoutlen = 0.05
        with self._application_lock:
            self._input_area = input_area
            self._output_area = output_area
        try:
            application.run(pre_run=self._capture_application, handle_sigint=False)
        except (EOFError, KeyboardInterrupt):
            return
        finally:
            with self._application_lock:
                self._application = None
                self._input_area = None
                self._output_area = None

    def _capture_application(self) -> None:
        application = get_app()
        with self._application_lock:
            self._application = application
        if self._stop_event.is_set():
            application.exit(result="")

    def _after_render(self, _application) -> None:
        with self._render_condition:
            self._rendered_revision = max(
                self._rendered_revision,
                self._displayed_revision,
            )
            self._render_condition.notify_all()

    @staticmethod
    def _exit_application(application: Any) -> None:
        def exit_now() -> None:
            if not application.is_done:
                application.exit(result="")

        future = getattr(application, "future", None)
        loop = future.get_loop() if future is not None else None
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(exit_now)
        elif future is not None:
            exit_now()

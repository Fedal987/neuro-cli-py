"""
    NeuroCode
    author@Fedal987
    Powered by HeronStudio
    08/17/2026  Ij1chi-Nijika
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from prompt_toolkit.history import History
from src.main.ui.i18n import tr

if TYPE_CHECKING:
    from src.main.msg.message_handler import MessageHandler


SESSION_FORMAT_VERSION = 1


@dataclass
class Session:
    name: str
    handler: MessageHandler
    workspace: Path = field(default_factory=lambda: Path.cwd().resolve())
    input_history: list[str] = field(default_factory=list)
    auto_name_pending: bool = False
    temporary: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)


class SessionPromptHistory(History):
    def __init__(self, manager: SessionManager) -> None:
        super().__init__()
        self.manager = manager

    def load_history_strings(self) -> Iterable[str]:
        if not self.manager.has_current_session:
            return
        yield from reversed(self.manager.current_session.input_history)

    def store_string(self, string: str) -> None:
        if (
            self.manager.current_session.temporary
            and string.lstrip().startswith("/")
        ):
            return
        self.manager.append_input_history(string)

    def select_current_session(self) -> None:
        self._loaded = False
        self._loaded_strings = []


class SessionManager:
    def __init__(
        self,
        session_factory: Callable[[], MessageHandler] | None = None,
        default_name: str = "default",
        workspace_provider: Callable[[], Path] = Path.cwd,
        storage_root: str | Path | None = None,
        name_generator: Callable[[list[dict[str, Any]]], str | None] | None = None,
    ) -> None:
        if session_factory is None:
            from src.main.msg.message_handler import MessageHandler
            session_factory = MessageHandler
        self._session_factory = session_factory
        self._workspace_provider = workspace_provider
        self._name_generator = name_generator or self._generate_name_with_llm
        self._default_name = default_name
        self.storage_root = Path(storage_root or Path.cwd()).expanduser().resolve()
        self.session_directory = self.storage_root / "session"
        self._sessions: dict[str, Session] = {}
        self._current_name: str | None = None
        self.prompt_history = SessionPromptHistory(self)
        self.load_errors: list[str] = []
        self.naming_errors: list[str] = []
        self._load_sessions()
        self._create_temporary_session()

    @property
    def has_current_session(self) -> bool:
        return self._current_name is not None

    @property
    def current_name(self) -> str | None:
        return self._current_name

    @property
    def current_session(self) -> Session:
        if self._current_name is None:
            raise RuntimeError(tr("session_none_available"))
        return self._sessions[self._current_name]

    @property
    def current_handler(self) -> MessageHandler:
        return self.current_session.handler

    @property
    def current_workspace(self) -> Path:
        return Path(self._workspace_provider()).expanduser().resolve()

    def list_sessions(
        self,
        workspace: str | Path | None = None,
    ) -> tuple[Session, ...]:
        sessions = tuple(
            sorted(self._sessions.values(), key=lambda item: item.created_at)
        )
        if workspace is None:
            return sessions
        resolved_workspace = Path(workspace).expanduser().resolve()
        return tuple(
            session
            for session in sessions
            if session.workspace == resolved_workspace
        )

    def create_session(
        self,
        name: str | None = None,
        *,
        switch: bool = True,
        save: bool = True,
        auto_name: bool | None = None,
        temporary: bool = False,
    ) -> Session:
        replace_temporary = (
            switch
            and not temporary
            and self.has_current_session
            and self.current_session.temporary
        )
        if name is not None:
            session_name = self._normalise_name(name)
            duplicate = session_name in self._sessions and not (
                replace_temporary and session_name == self.current_name
            )
            if duplicate:
                raise ValueError(tr("session_exists", name=session_name))
        if replace_temporary:
            self._discard_current_temporary()
        if name is None:
            session_name = self._normalise_name(self._next_name())
        if session_name in self._sessions:
            raise ValueError(tr("session_exists", name=session_name))

        new_session = Session(
            name=session_name,
            handler=self._session_factory(),
            workspace=self.current_workspace,
            auto_name_pending=name is None if auto_name is None else auto_name,
            temporary=temporary,
        )
        self._sessions[session_name] = new_session
        if switch:
            self._current_name = session_name
            self.prompt_history.select_current_session()
        if save and not temporary:
            self.save_session(new_session)
        return new_session

    def ensure_current_session(self) -> Session:
        if self.has_current_session:
            return self.current_session
        return self._create_temporary_session()

    def activate_current_session(self) -> Session:
        session = self.ensure_current_session()
        if session.temporary:
            session.temporary = False
            session.last_used_at = datetime.now()
            self.save_session(session)
        return session

    def switch_session(
        self,
        target: str | int,
        *,
        workspace: str | Path | None = None,
    ) -> Session:
        name = self._resolve_target(target, workspace=workspace)
        if (
            self.has_current_session
            and self.current_session.temporary
            and self.current_name != name
        ):
            self._discard_current_temporary()
        selected = self._sessions[name]
        selected.last_used_at = datetime.now()
        self._current_name = name
        self.prompt_history.select_current_session()
        self.save_session(selected)
        return selected

    def select_session(
        self,
        choice: str | int | None = None,
        *,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> Session | None:
        if choice is not None:
            return self.switch_session(choice)
        output_func(tr("sessions_available"))
        for index, session in enumerate(self.list_sessions(), start=1):
            marker = " *" if session.name == self.current_name else ""
            output_func(f"  {index}. {session.name}{marker}")
        selected = input_func(tr("session_select_prompt")).strip()
        if not selected or selected.lower() == "q":
            return None
        target: str | int = int(selected) if selected.isdigit() else selected
        try:
            return self.switch_session(target)
        except (IndexError, KeyError, ValueError) as exc:
            raise ValueError(tr("session_select_failed", selected=selected)) from exc

    def append_input_history(self, text: str) -> None:
        self.activate_current_session()
        self.current_session.input_history.append(text)
        self.current_session.last_used_at = datetime.now()
        self.save_current_session()

    def reset_current_session(self) -> None:
        if not self.has_current_session:
            return
        self.current_handler.reset()
        self.current_session.last_used_at = datetime.now()
        self.save_current_session()

    def auto_name_current_session(self) -> str | None:
        if not self.has_current_session:
            return None
        session = self.current_session
        if not session.auto_name_pending:
            return None
        roles = {
            message.get("role")
            for message in session.handler.history
            if isinstance(message, dict)
        }
        if not {"user", "assistant"}.issubset(roles):
            return None
        try:
            generated = self._name_generator(session.handler.history)
            title = self._clean_generated_name(generated)
        except Exception as exc:  # Naming must never interrupt the conversation.
            self.naming_errors.append(str(exc))
            return None
        if not title:
            return None
        unique_title = self._unique_name(title, exclude=session.name)
        old_name = session.name
        self._rename_session(old_name, unique_title)
        session.auto_name_pending = False
        self.save_session(session)
        old_path = self._session_path(old_name)
        if old_path != self._session_path(unique_title) and old_path.exists():
            try:
                old_path.unlink()
            except OSError as exc:
                self.naming_errors.append(str(exc))
        return unique_title

    def save_current_session(self) -> None:
        if not self.has_current_session:
            return
        if self.current_session.auto_name_pending:
            self.auto_name_current_session()
        self.save_session(self.current_session)

    def save_all(self) -> None:
        for session in self._sessions.values():
            self.save_session(session)

    def save_session(self, session: Session) -> None:
        if session.temporary:
            return
        self.session_directory.mkdir(parents=True, exist_ok=True)
        target = self._session_path(session.name)
        temporary = target.with_suffix(".session.tmp")
        payload = {
            "version": SESSION_FORMAT_VERSION,
            "name": session.name,
            "workspace": str(session.workspace),
            "created_at": session.created_at.isoformat(),
            "last_used_at": session.last_used_at.isoformat(),
            "messages": session.handler.history,
            "input_history": session.input_history,
            "auto_name_pending": session.auto_name_pending,
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)

    def _load_sessions(self) -> None:
        if not self.session_directory.is_dir():
            return
        for session_path in sorted(self.session_directory.glob("*.session")):
            try:
                data = json.loads(session_path.read_text(encoding="utf-8"))
                session = self._session_from_data(data)
                if session.name in self._sessions:
                    raise ValueError(tr("session_duplicate_name", name=session.name))
                self._sessions[session.name] = session
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
                self.load_errors.append(f"{session_path.name}: {exc}")

    def _session_from_data(self, data: Any) -> Session:
        if not isinstance(data, dict):
            raise ValueError(tr("session_json_object_required"))
        name = self._normalise_name(data.get("name", ""))
        messages = data.get("messages", [])
        input_history = data.get("input_history", [])
        if not isinstance(messages, list) or not all(
            isinstance(message, dict) for message in messages
        ):
            raise ValueError(tr("session_messages_invalid"))
        if not isinstance(input_history, list) or not all(
            isinstance(item, str) for item in input_history
        ):
            raise ValueError(tr("session_history_invalid"))
        handler = self._session_factory()
        if messages:
            handler.history[:] = messages
        return Session(
            name=name,
            handler=handler,
            workspace=Path(data.get("workspace") or self.storage_root).resolve(),
            input_history=list(input_history),
            auto_name_pending=bool(
                data.get(
                    "auto_name_pending",
                    name == "default" or bool(re.fullmatch(r"session-\d+", name)),
                )
            ),
            temporary=False,
            created_at=self._parse_datetime(data.get("created_at")),
            last_used_at=self._parse_datetime(data.get("last_used_at")),
        )

    def _resolve_target(
        self,
        target: str | int,
        *,
        workspace: str | Path | None = None,
    ) -> str:
        sessions = self.list_sessions(workspace=workspace)
        if isinstance(target, bool):
            raise ValueError(tr("session_number_positive"))
        if isinstance(target, int):
            if target < 1 or target > len(sessions):
                raise IndexError(tr("session_number_out_of_range", target=target))
            return sessions[target - 1].name
        if isinstance(target, str):
            name = self._normalise_name(target)
            if not any(session.name == name for session in sessions):
                raise KeyError(tr("session_not_found", name=name))
            return name
        raise TypeError(tr("session_selection_type"))

    def _session_path(self, name: str) -> Path:
        return self.session_directory / f"{quote(name, safe='')}.session"

    def _create_temporary_session(self) -> Session:
        name = None if self._sessions else self._default_name
        return self.create_session(
            name,
            switch=True,
            save=False,
            auto_name=True,
            temporary=True,
        )

    def _discard_current_temporary(self) -> None:
        if not self.has_current_session or not self.current_session.temporary:
            return
        temporary_name = self.current_session.name
        del self._sessions[temporary_name]
        self._current_name = None
        self.prompt_history.select_current_session()

    def _rename_session(self, old_name: str, new_name: str) -> None:
        session = self._sessions[old_name]
        session.name = new_name
        self._sessions = {
            (new_name if name == old_name else name): item
            for name, item in self._sessions.items()
        }
        if self._current_name == old_name:
            self._current_name = new_name

    def _unique_name(self, requested: str, *, exclude: str | None = None) -> str:
        existing = set(self._sessions)
        if exclude is not None:
            existing.discard(exclude)
        if requested not in existing:
            return requested
        index = 2
        while f"{requested}-{index}" in existing:
            index += 1
        return f"{requested}-{index}"

    @staticmethod
    def _generate_name_with_llm(messages: list[dict[str, Any]]) -> str | None:
        from src.main.api.api_manager import get_completion

        excerpts: list[str] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if role not in {"user", "assistant"} or not isinstance(content, str):
                continue
            label = "用户" if role == "user" else "助手"
            excerpts.append(f"{label}: {content}")
        conversation = "\n".join(excerpts)[:6000]
        result = get_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "你是会话标题生成器。根据对话生成一个准确、简短的中文标题，"
                        "建议 2 到 12 个汉字。只输出标题，不要引号、标点、解释或前缀。"
                    ),
                },
                {"role": "user", "content": conversation},
            ],
            stream=False,
            temperature=0.2,
        )
        if not isinstance(result, str) or result.startswith("API Error:"):
            return None
        return result

    @staticmethod
    def _clean_generated_name(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value:
            return None
        title = value.splitlines()[0].strip(" `\"'“”‘’《》")
        title = re.sub(r"^(会话)?标题\s*[:：]\s*", "", title)
        title = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "", title)
        title = re.sub(r"\s+", "-", title).strip(" .-")
        return title[:40] or None

    def _next_name(self) -> str:
        index = 1
        while f"session-{index}" in self._sessions:
            index += 1
        return f"session-{index}"

    @staticmethod
    def _normalise_name(name: str) -> str:
        if not isinstance(name, str):
            raise TypeError(tr("session_name_string"))
        normalised = name.strip()
        if not normalised:
            raise ValueError(tr("session_name_empty"))
        return normalised

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.now()

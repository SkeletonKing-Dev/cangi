import logging
import threading
from typing import Callable, Dict, Optional

from ..presenter import OverlayPresenter
from ..protocol import IDLE
from ..schema import Event
from ..walkthrough import WalkthroughController
from . import prompts
from .catalog import CATALOGS
from .context import ContextTracker
from .llm import ChatClient, LLMError
from .plan import GuidePlan, PlanError, parse_plan
from .session import GuideSession

log = logging.getLogger("cangi.guide")

Executor = Callable[[Callable[[], None]], None]


def thread_executor(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, name="cangi-guide", daemon=True).start()


def _status(state: str, text: str = "") -> dict:
    return {"state": state, "text": text}


class GuideService:
    """Handles guide messages from plugins: asks the model for a plan, then steps through it."""

    def __init__(self, client: ChatClient, controller: WalkthroughController,
                 presenter: OverlayPresenter, catalogs: Optional[Dict[str, Dict[str, str]]] = None,
                 executor: Executor = thread_executor):
        self.client = client
        self.controller = controller
        self.presenter = presenter
        self.catalogs = CATALOGS if catalogs is None else catalogs
        self.context = ContextTracker()
        self._executor = executor
        self._lock = threading.RLock()
        self._session: Optional[GuideSession] = None
        self._token = 0

    def handle_message(self, msg: dict) -> None:
        if msg.get("op") != "guide":
            return
        action = msg.get("action")
        if action == "ask":
            self._ask(str(msg.get("platform", "")), str(msg.get("text", "")).strip())
        elif action in ("next", "back", "stop"):
            self._navigate(action)

    def on_event(self, event: Event) -> None:
        self.context.update(event)
        with self._lock:
            if self._session and self._session.matches(event):
                self._advance_locked()

    def _ask(self, platform: str, text: str) -> None:
        if not text:
            return
        with self._lock:
            self._token += 1
            token = self._token
            self._end_locked()
        self.presenter.refresh(_status("thinking", "Thinking..."))
        self._executor(lambda: self._run_ask(token, platform, text))

    def _run_ask(self, token: int, platform: str, text: str) -> None:
        try:
            plan = self._request_plan(platform, text)
        except (LLMError, PlanError) as exc:
            log.warning("guide request failed: %s", exc)
            self._finish_ask(token, None, str(exc))
            return
        except Exception:
            log.exception("guide request crashed")
            self._finish_ask(token, None, "unexpected error")
            return
        self._finish_ask(token, GuideSession(plan, platform), "")

    def _request_plan(self, platform: str, text: str) -> GuidePlan:
        catalog = self.catalogs.get(platform, {})
        messages = [
            {"role": "system", "content": prompts.system_prompt(platform, catalog)},
            {"role": "user", "content": prompts.user_prompt(text, self.context.summary(platform))},
        ]
        reply = self.client.complete(messages)
        try:
            return parse_plan(reply, catalog)
        except PlanError as exc:
            messages += [{"role": "assistant", "content": reply},
                         {"role": "user", "content": prompts.repair_prompt(str(exc))}]
        return parse_plan(self.client.complete(messages), catalog)

    def _finish_ask(self, token: int, session: Optional[GuideSession], error: str) -> None:
        with self._lock:
            if token != self._token:
                return
            if session is None:
                self.presenter.refresh(_status("error", error))
                return
            self._session = session
            self._show_locked()

    def _navigate(self, action: str) -> None:
        with self._lock:
            if action == "stop":
                self._token += 1
                self._end_locked()
                self.presenter.refresh(IDLE)
            elif self._session is None:
                return
            elif action == "next":
                self._advance_locked()
            elif self._session.back():
                self._show_locked()

    def _advance_locked(self) -> None:
        session = self._session
        if session.advance():
            self._show_locked()
            return
        title = session.plan.title
        self._end_locked()
        self.presenter.refresh(_status("done", "Finished: " + title))

    def _show_locked(self) -> None:
        self.controller.show_guide(self._session.overlay_steps())
        self.presenter.refresh(IDLE)

    def _end_locked(self) -> None:
        self._session = None
        self.controller.clear_guide()

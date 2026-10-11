"""One action menu shared by the toolbar, keyboard, and mouse."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType


@dataclass(frozen=True)
class WorkspaceAction:
    label: Callable[[], str]
    run: Callable[[], None]


class ActionMenu:
    def __init__(
        self, actions: list[WorkspaceAction], close: Callable[[], None]
    ) -> None:
        self.actions = actions
        self.close = close
        self.selected = 0
        bindings = KeyBindings()

        @bindings.add("up")
        @bindings.add("down")
        @bindings.add("pageup")
        @bindings.add("pagedown")
        @bindings.add("home")
        @bindings.add("end")
        def move(event: KeyPressEvent) -> None:
            key = event.key_sequence[0].key
            if key == "home":
                self.selected = 0
            elif key == "end":
                self.selected = len(self.actions) - 1
            else:
                amount = (
                    -1
                    if key == "up"
                    else 1
                    if key == "down"
                    else -5
                    if key == "pageup"
                    else 5
                )
                self.move(amount)

        @bindings.add("enter")
        def choose(event: KeyPressEvent) -> None:
            self.activate()

        self.control = FormattedTextControl(
            self.fragments,
            focusable=True,
            key_bindings=bindings,
            get_cursor_position=lambda: Point(0, self.selected),
        )
        self.control.mouse_handler = self.mouse_handler  # type: ignore[method-assign, assignment]
        self.window = Window(
            self.control,
            right_margins=[ScrollbarMargin(display_arrows=True)],
            wrap_lines=False,
            style="class:actions",
        )

    def move(self, amount: int) -> None:
        self.selected = max(0, min(len(self.actions) - 1, self.selected + amount))

    def activate(self) -> None:
        action = self.actions[self.selected]
        self.close()
        action.run()

    def mouse_handler(self, event: MouseEvent) -> None:
        get_app().layout.focus(self.window)
        if event.event_type in {MouseEventType.SCROLL_UP, MouseEventType.SCROLL_DOWN}:
            self.move(-3 if event.event_type == MouseEventType.SCROLL_UP else 3)
        elif 0 <= event.position.y < len(self.actions):
            self.selected = event.position.y
            if event.event_type == MouseEventType.MOUSE_UP:
                self.activate()

    def fragments(self) -> StyleAndTextTuples:
        return [
            (
                "class:action-selected" if i == self.selected else "class:action",
                ("> " if i == self.selected else "  ") + action.label() + "\n",
            )
            for i, action in enumerate(self.actions)
        ]

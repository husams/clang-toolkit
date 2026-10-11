"""Isolated prompt_toolkit feasibility probe; does not import or alter CTK."""
import asyncio
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, HSplit, Layout, VSplit
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.widgets import Label, MenuContainer, MenuItem, TextArea


async def main():
    state = {"files_visible": False, "status": "Ready"}
    editor = TextArea(multiline=True)
    files = TextArea(text="src/\n  sample.cpp", read_only=True, width=24)
    transcript = TextArea(text="Results", read_only=True, height=8)
    footer = Label(lambda: state["status"])
    bindings = KeyBindings()

    def toggle_files():
        state["files_visible"] = not state["files_visible"]
        app.layout.focus(files if state["files_visible"] else editor)
        app.invalidate()

    @bindings.add("f3")
    def toggle(event):
        toggle_files()

    @bindings.add("c-q")
    def quit_app(event):
        event.app.exit(result="complete")

    sidebar = ConditionalContainer(files, Condition(lambda: state["files_visible"]))
    body = HSplit([VSplit([sidebar, HSplit([transcript, editor])]), footer])
    root = MenuContainer(body, [MenuItem("View", children=[MenuItem("Files", handler=toggle_files)])])
    checks = []

    async def until(predicate):
        for _ in range(100):
            if predicate():
                return
            await asyncio.sleep(0.005)
        raise AssertionError("input processing timed out")

    with create_pipe_input() as pipe:
        app = Application(layout=Layout(root, focused_element=editor), key_bindings=bindings,
                          input=pipe, output=DummyOutput(), full_screen=True)

        async def drive():
            await until(lambda: app.is_running)
            pipe.send_text("draft")
            await until(lambda: editor.text == "draft")
            pipe.send_text("\x1bOR")
            await until(lambda: state["files_visible"])
            assert app.layout.has_focus(files)
            checks.append("F3 opens sidebar and focuses files")
            pipe.send_text("\x1bOR")
            await until(lambda: not state["files_visible"])
            assert app.layout.has_focus(editor)
            assert editor.text == "draft"
            checks.append("F3 closes sidebar and restores input with draft preserved")
            state["status"] = "Running"
            app.invalidate()
            assert footer.text() == "Running"
            checks.append("footer reads updated application state")
            root.menu_items[0].children[0].handler()
            assert state["files_visible"]
            checks.append("menu action opens the same sidebar")
            pipe.send_text("\x11")

        task = asyncio.create_task(drive())
        result = await asyncio.wait_for(app.run_async(), timeout=5)
        await task
        assert result == "complete"
        checks.append("async application exits cleanly")
    text = ("Source: Isolated public API layout probe using pipe input and DummyOutput\n"
            "Fetched: 2026-10-10\nDescription: Widget composition and focus feasibility on prompt_toolkit 3.0.53\n"
            "Scope: No CTK integration or visual terminal rendering validation\n\n"
            + "\n".join("PASS: " + check for check in checks) + "\n")
    target = Path(__file__).parent / "wiki/raw/2026-10-10-prompt-toolkit-layout-probe.md"
    target.write_text(text)
    print(text)


if __name__ == "__main__":
    asyncio.run(main())

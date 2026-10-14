"""Contextual help as Rich Markdown with grammar-colored CTK examples."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from clang_toolkit.cli.help import COMMAND_HELP, MATCHER_HELP, help_entry
from clang_toolkit.cli.callable_help import CallableHelp
from clang_toolkit.cli.language import lex
from clang_toolkit.cli.workspace_markdown import MarkdownPanel


class CommandContext(MarkdownPanel):
    def __init__(
        self,
        function_help: Mapping[str, CallableHelp]
        | Callable[[], Mapping[str, CallableHelp]]
        | None = None,
    ) -> None:
        super().__init__()
        self.function_help = function_help

    def update(self, source: str, root: str, *, completion: str | None = None) -> None:
        words = [str(token) for token in lex(source) if token.type != "WS"]
        functions = (
            self.function_help()
            if callable(self.function_help)
            else self.function_help or {}
        )
        matcher = completion.removesuffix("(") if completion else None
        if completion is None and words and words[0] == "help":
            matcher = " ".join(words[1:])
        if matcher not in MATCHER_HELP and matcher not in functions:
            calls: list[str | None] = []
            for i, word in enumerate(words):
                if word == "(":
                    name = words[i - 1] if i else ""
                    calls.append(
                        name if name in MATCHER_HELP or name in functions else None
                    )
                elif word == ")" and calls:
                    calls.pop()
            matcher = calls[-1] if calls else (words[-1] if words else None)
        if matcher in functions:
            self.set_markdown(functions[matcher].markdown())
            return
        if matcher in MATCHER_HELP:
            entry = MATCHER_HELP[matcher]
            self.set_markdown(
                "\n\n".join(
                    (
                        "## " + entry.topic,
                        entry.purpose,
                        "### Signatures",
                        "```text\n" + "\n".join(entry.usage) + "\n```",
                        "### Notes",
                        "\n".join("- " + note for note in entry.arguments[:3]),
                        "More: `help " + entry.topic + "` or `" + entry.topic + "?`",
                    )
                )
            )
            return
        operational = {
            "parse",
            "match",
            "cfg",
            "callgraph",
            "traverse",
            "cursor",
            "file",
            "session",
            "server",
            "bindings",
            "resource",
        }
        index = next((i for i, word in enumerate(words) if word in operational), 0)
        topic = words[index] if words else ""
        if words and words[0] == "help":
            topic = " ".join(words[1:])
        if index + 1 < len(words) and topic + " " + words[index + 1] in COMMAND_HELP:
            topic += " " + words[index + 1]
        entry = help_entry(topic)
        if entry is None:
            markdown = (
                "## Workspace\n\nWrite a command below. **Ctrl+Enter** runs the whole draft; "
                "**Ctrl+J** also runs it. **Enter** executes complete input at its end; "
                "otherwise it adds an indented line. **Actions → Run command** also executes.\n\n"
                "## Panels\n\n- **F3** Local files\n- **F4** Command help\n"
                "- **F7** Binding outline\n- **F8** Resources\n"
                "- **F9** Live server status\n\n"
                "Close a panel with its **×** button. **F6** changes focus.\n\n"
                "**Ctrl+R** searches; **F10** quits.\n\n"
                "## Resource commands\n\n```ctk\nfile list\nsession list\nbindings\nserver status\n```"
            )
        else:
            markdown = "\n\n".join(
                [
                    "## " + entry.topic,
                    entry.purpose,
                    "### Usage",
                    "```ctk\n" + "\n".join(entry.usage[:3]) + "\n```",
                    "### Examples",
                    *("```ctk\n" + example + "\n```" for example in entry.examples[:2]),
                    "### Notes",
                    "\n".join("- " + note for note in entry.arguments[:3]),
                    "More: `help " + entry.topic + "`",
                ]
            )
            if entry.topic == "match":
                markdown += (
                    "\n\n### Large results\n\nHeader declarations count toward the server's row budget. "
                    "For main-file functions, use:\n\n```ctk\n"
                    "functionDecl(isExpansionInMainFile(), unless(isImplicit()))\n```\n\n"
                    "The outline pages through long lists **50 items at a time**. "
                    "Select **Next page** or **Previous page**, then press **Enter**. "
                    "**Right** expands/enters a branch; **Left** collapses/goes to its parent. "
                    "**Ctrl+Left/Right** or the horizontal scrollbar reveals long properties; **Enter** toggles a branch."
                )
        self.set_markdown(markdown)

"""Contextual help as Rich Markdown with grammar-colored CTK examples."""

from __future__ import annotations

from clang_toolkit.cli.help import COMMAND_HELP
from clang_toolkit.cli.language import lex
from clang_toolkit.cli.workspace_markdown import MarkdownPanel


class CommandContext(MarkdownPanel):
    def update(self, source: str, root: str) -> None:
        words = [str(token) for token in lex(source) if token.type != "WS"]
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
        if index + 1 < len(words) and topic + " " + words[index + 1] in COMMAND_HELP:
            topic += " " + words[index + 1]
        entry = COMMAND_HELP.get(topic)
        if entry is None:
            markdown = (
                "## Workspace\n\nWrite a command below. **Enter** continues incomplete syntax; "
                "complete input runs as one command.\n\n"
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

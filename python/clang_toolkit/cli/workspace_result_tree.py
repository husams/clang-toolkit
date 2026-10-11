"""Expandable typed values embedded in the existing searchable transcript."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import Any

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout.processors import (
    Processor,
    Transformation,
    TransformationInput,
)
from prompt_toolkit.widgets import TextArea

from clang_toolkit.cli.workspace_state import PanelEntry, compact
from clang_toolkit.cli.workspace_output import MAX_TRANSCRIPT_CHARS
from clang_toolkit.cli.workspace_transcript import StyledBlock, TranscriptLexer
from clang_toolkit.cli.workspace_tree import entry_text, navigate_tree
from clang_toolkit.cli.runtime.progress import BatchProgress

SnapshotReader = Callable[
    [str, Any, frozenset[str], dict[str, int]], Awaitable[list[PanelEntry] | None]
]
MAX_RESULT_TREES = 20


class TreeSelection(Processor):
    """Reuse the outline's selection style without changing transcript text."""

    def __init__(self, selected: Callable[[int], bool]) -> None:
        self.selected = selected

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        if ti.lineno == ti.document.cursor_position_row and self.selected(ti.lineno):
            return Transformation(
                [
                    (fragment[0] + " class:tree-selected", *fragment[1:])
                    for fragment in ti.fragments
                ]
            )
        return Transformation(ti.fragments)


@dataclass
class ResultTree:
    kind: str
    value: Any
    start: int
    entries: list[PanelEntry]
    text: str = ""
    expanded: set[str] = field(default_factory=set)
    pages: dict[str, int] = field(default_factory=dict)
    refreshing: bool = False

    def render(self) -> str:
        # Preserve all rows and pagers while keeping a fully expanded preview
        # below the transcript budget. F7 retains longer property labels.
        lines = []
        for item in self.entries:
            label = compact(item.label, 512)
            if (
                self.kind != "bindings_list"
                and item.depth == 0
                and item.identity in {"$Matches", "$Files", "$Sessions", "$List", "$Dictionary"}
            ):
                label = label.removeprefix("$")
            lines.append(entry_text(replace(item, label=label), self.expanded))
        return "\n".join(lines)

    def styled(self) -> list[StyleAndTextTuples]:
        return [[("class:tree" + (" class:source-link" if item.source else ""), line)] for item, line in zip(self.entries, self.text.splitlines(), strict=True)]


class ResultTrees:
    def __init__(
        self,
        results: TextArea,
        lexer: TranscriptLexer,
        append: Callable[..., None],
        reader: SnapshotReader,
        replaced: Callable[[int, int, int], None],
    ) -> None:
        self.results = results
        self.lexer = lexer
        self.append = append
        self.reader = reader
        self.replaced = replaced
        self.trees: list[ResultTree] = []
        self.navigation_lock = asyncio.Lock()

    def trim(self, cut: int, shift: int) -> None:
        self.trees = [tree for tree in self.trees if tree.start >= cut]
        for tree in self.trees:
            tree.start -= shift

    def shift(self, start: int, end: int, length: int) -> None:
        self.trees = [
            tree
            for tree in self.trees
            if tree.start + len(tree.text) <= start or tree.start >= end
        ]
        for tree in self.trees:
            if tree.start >= end:
                tree.start += length - (end - start)

    async def show(self, kind: str, value: Any) -> bool:
        entries = await self.reader(kind, value, frozenset(), {})
        if entries is None:
            return False
        entries = entries or [PanelEntry(":empty", "No bindings")]
        self.add(kind, value, entries)
        return True

    def progress(self, value: BatchProgress) -> None:
        entries = [PanelEntry(":batch:" + value.run_id, value.label())]
        tree = next((tree for tree in self.trees if tree.kind == "batch_progress" and tree.value.run_id == value.run_id), None)
        if tree is not None and value.durable and value.revision < tree.value.revision:
            return
        if tree is None:
            self.add("batch_progress", value, entries)
        elif not value.active and tree.start + len(tree.text) + 1 < len(self.results.text):
            # Put the final counters after any body output without leaving a
            # second progress log or hiding completion above a long transcript.
            tree.entries = []
            self.replace(tree)
            self.trees.remove(tree)
            self.add("batch_progress", value, entries)
        else:
            tree.value, tree.entries = value, entries
            self.replace(tree)

    def add(self, kind: str, value: Any, entries: list[PanelEntry]) -> None:
        # Older previews remain searchable, without retaining unbounded values.
        if len(self.trees) >= MAX_RESULT_TREES:
            oldest = self.trees[0]
            oldest.entries = [
                replace(item, expandable=False, page=None, source=None) for item in oldest.entries
            ]
            oldest.entries[0] = replace(
                oldest.entries[0],
                label=oldest.entries[0].label + " · preview; print again to expand",
            )
            self.replace(oldest)
            self.trees = [tree for tree in self.trees if tree is not oldest]
        tree = ResultTree(kind, value, len(self.results.text), entries)
        tree.text = tree.render()
        self.trees.append(tree)
        self.append(tree.text, tree.styled())

    def at(self, line: int) -> tuple[ResultTree, int] | None:
        document = self.results.buffer.document
        if not 0 <= line < document.line_count:
            return None
        offset = document.translate_row_col_to_index(line, 0)
        for tree in self.trees:
            if tree.start <= offset < tree.start + len(tree.text):
                first, _ = document.translate_index_to_position(tree.start)
                index = line - first
                if 0 <= index < len(tree.entries):
                    return tree, index
        return None

    async def navigate(self, direction: str) -> bool:
        # Preserve rapidly repeated arrow keys while a local snapshot loads.
        async with self.navigation_lock:
            return await self._navigate(direction)

    async def _navigate(self, direction: str) -> bool:
        found = self.at(self.results.buffer.document.cursor_position_row)
        if found is None:
            return False
        tree, selected = found
        if tree.refreshing:
            return True
        current = tree.entries[selected]
        changed = False
        if direction == "enter":
            if current.page is not None:
                reference, page = current.page
                tree.pages[reference] = page
                changed = True
            elif current.expandable:
                if current.identity in tree.expanded:
                    tree.expanded.remove(current.identity)
                else:
                    tree.expanded.add(current.identity)
                changed = True
        else:
            selected, changed = navigate_tree(
                tree.entries, selected, tree.expanded, direction
            )
        identity = tree.entries[selected].identity
        if changed:
            tree.refreshing = True
            try:
                entries = await self.reader(
                    tree.kind, tree.value, frozenset(tree.expanded), dict(tree.pages)
                )
            except Exception as exc:  # noqa: BLE001 - optional display boundary
                entries = [PanelEntry(":error", f"Cannot expand: {exc}")]
            finally:
                tree.refreshing = False
            # A concurrent clear/trim may have removed this preview.
            if not any(candidate is tree for candidate in self.trees):
                return True
            tree.entries = entries or [PanelEntry(":empty", "No bindings")]
            selected = next(
                (i for i, item in enumerate(tree.entries) if item.identity == identity),
                min(selected, len(tree.entries) - 1),
            )
            self.replace(tree)
        if not any(candidate is tree for candidate in self.trees):
            return True
        first, _ = self.results.buffer.document.translate_index_to_position(tree.start)
        self.results.buffer.cursor_position = (
            self.results.buffer.document.translate_row_col_to_index(first + selected, 0)
        )
        return True

    def replace(self, tree: ResultTree) -> None:
        old = self.results.buffer.document
        start, end = tree.start, tree.start + len(tree.text)
        tree.text = tree.render()
        self.lexer.replace(start, end, len(tree.text))
        self.lexer.blocks.append(
            StyledBlock(
                start,
                tree.text,
                tree.styled(),
            )
        )
        for other in self.trees:
            if other is not tree and other.start >= end:
                other.start += len(tree.text) - (end - start)
        self.replaced(start, end, len(tree.text))
        text = old.text[:start] + tree.text + old.text[end:]
        cursor = old.cursor_position
        if cursor >= end:
            cursor += len(tree.text) - (end - start)
        elif cursor >= start:
            cursor = start
        removed = max(0, len(text) - MAX_TRANSCRIPT_CHARS)
        if removed:
            marker = "[Earlier display output trimmed; use save for full results]\n"
            cut = removed + len(marker)
            self.trim(cut, removed)
            self.lexer.trim(cut, removed)
            self.replaced(0, cut, len(marker))
            text = marker + text[cut:]
            cursor = max(0, cursor - removed)
        self.results.buffer.set_document(
            Document(text, min(cursor, len(text))), bypass_readonly=True
        )

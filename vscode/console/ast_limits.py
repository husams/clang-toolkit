"""AST browser bounds shared by inspection and source selection."""

from __future__ import annotations

# Non-TU navigation counts candidates before applying filters. File-root
# queries filter direct declarations before collecting their rows.
MAX_AST_CHILDREN: int = 100000
# Leave room to expand children after opening a wide file or namespace.
MAX_RETAINED_NODES: int = 2 * MAX_AST_CHILDREN

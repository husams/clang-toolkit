"""AST browser bounds shared by inspection and source selection."""

from __future__ import annotations

# Navigation counts candidates before applying file filters, including header
# declarations. Use the SDK's supported ceiling rather than a UI row cap.
MAX_AST_CHILDREN: int = 100000
# Leave room to expand children after opening a wide file or namespace.
MAX_RETAINED_NODES: int = 2 * MAX_AST_CHILDREN

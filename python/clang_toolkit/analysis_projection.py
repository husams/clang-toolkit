"""Independent semantic projection limits for graph operations."""
from __future__ import annotations

from clang_toolkit._generated.analysis.v1.value_projection_pb2 import ValueProjection


def value_projection(mode: str = "shallow", *, payload_depth: int = 24,
                     payload_nodes: int = 10000) -> ValueProjection:
    if mode not in {"shallow", "recursive"}:
        raise ValueError("projection must be shallow or recursive")
    if not 1 <= payload_depth <= 64:
        raise ValueError("payload_depth must be 1..64")
    if not 1 <= payload_nodes <= 100000:
        raise ValueError("payload_nodes must be 1..100000")
    return ValueProjection(
        mode=ValueProjection.SHALLOW if mode == "shallow" else ValueProjection.RECURSIVE,
        max_depth=payload_depth, max_nodes=payload_nodes,
    )

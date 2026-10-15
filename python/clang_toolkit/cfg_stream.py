"""Constant-space validation of the ordered CFG event protocol."""
from __future__ import annotations

import grpc
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1.cfg_stream_pb2 import CfgStreamEvent


class CfgStreamState:
    def __init__(self) -> None:
        self.graphs = self.blocks = self.elements = 0
        self.graph_blocks = self.graph_elements = 0
        self.last_block: int | None = None
        self.active = self.completed = False

    def consume(self, event: CfgStreamEvent) -> None:
        def require(condition: bool) -> None:
            if not condition:
                raise AnalysisError(grpc.StatusCode.DATA_LOSS, "invalid CFG stream ordering or counts")

        require(not self.completed)
        kind = event.WhichOneof("event")
        if kind == "graph_started":
            value = event.graph_started
            require(not self.active and value.graph_index == self.graphs and
                    value.HasField("graph") and not value.graph.blocks)
            self.active = True
            self.graph_blocks = self.graph_elements = 0
            self.last_block = None
        elif kind == "block":
            value = event.block
            require(self.active and value.graph_index == self.graphs and value.HasField("block"))
            require(self.last_block is None or value.block.block_index > self.last_block)
            self.last_block = value.block.block_index
            self.graph_blocks += 1
            self.graph_elements += len(value.block.elements)
        elif kind == "graph_completed":
            value = event.graph_completed
            require(self.active and value.graph_index == self.graphs)
            require(value.block_count == self.graph_blocks and value.element_count == self.graph_elements)
            self.graphs += 1
            self.blocks += self.graph_blocks
            self.elements += self.graph_elements
            self.active = False
        elif kind == "completed":
            value = event.completed
            require(not self.active and value.graph_count == self.graphs and
                    value.block_count == self.blocks and value.element_count == self.elements)
            self.completed = True
        else:
            require(False)

    def finish(self) -> None:
        if not self.completed:
            raise AnalysisError(grpc.StatusCode.DATA_LOSS, "CFG stream ended without completion")

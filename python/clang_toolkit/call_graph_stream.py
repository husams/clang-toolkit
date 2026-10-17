"""Bounded-memory validation of streamed call-graph events and references."""

import grpc

from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1.call_graph_stream_pb2 import (
    CallGraphStreamEvent,
)


class CallGraphStreamState:
    def __init__(self, *, expect_unlimited_depth: bool = False,
                 expect_exclude_system_headers: bool = False,
                 expect_node_filter: str = "",
                 expect_strict_node_filter: bool = False) -> None:
        self.graphs = self.nodes = self.edges = self.call_sites = 0
        self.active = self.completed = False
        self.graph_nodes = self.graph_edges = self.graph_call_sites = 0
        self._node_ids: set[int] = set()
        self._referenced_nodes: set[int] = set()
        self._root_node: int | None = None
        self._focus_node: int | None = None
        self._expect_unlimited_depth = expect_unlimited_depth
        self._expect_exclude_system_headers = expect_exclude_system_headers
        self._expect_node_filter = expect_node_filter
        self._expect_strict_node_filter = expect_strict_node_filter

    def consume(self, event: CallGraphStreamEvent) -> None:
        def require(condition: bool) -> None:
            if not condition:
                raise AnalysisError(
                    grpc.StatusCode.DATA_LOSS,
                    "invalid call-graph stream ordering or counts",
                )

        require(not self.completed)
        kind = event.WhichOneof("event")
        if kind == "graph_started":
            value = event.graph_started
            require(
                self.graphs == 0
                and value.graph_index == self.graphs
                and value.HasField("graph")
                and not value.graph.nodes
                and not value.graph.edges
                and not value.graph.call_sites
            )
            if self._expect_unlimited_depth and not (
                value.graph.HasField("selection_unlimited_depth")
                and value.graph.selection_unlimited_depth
            ):
                raise AnalysisError(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    "server did not confirm unlimited call-graph depth support",
                )
            if (value.graph.exclude_system_headers != self._expect_exclude_system_headers
                    or value.graph.node_filter != self._expect_node_filter
                    or value.graph.strict_node_filter != self._expect_strict_node_filter):
                raise AnalysisError(
                    grpc.StatusCode.FAILED_PRECONDITION,
                    "server did not confirm call-graph boundary filters",
                )
            self.active = True
            self.graph_nodes = self.graph_edges = self.graph_call_sites = 0
            self.graphs += 1
            self._root_node = value.graph.root_node
            self._focus_node = (
                value.graph.focus_node if value.graph.HasField("focus_node") else None
            )
        elif kind == "node":
            require(
                self.active
                and event.node.graph_index == self.graphs - 1
                and event.node.HasField("node")
            )
            require(event.node.node.node_index == self.graph_nodes)
            require(event.node.node.node_index not in self._node_ids)
            self._node_ids.add(event.node.node.node_index)
            self.graph_nodes += 1
            self.nodes += 1
        elif kind == "edge":
            require(
                self.active
                and event.edge.graph_index == self.graphs - 1
                and event.edge.HasField("edge")
            )
            self._referenced_nodes.update(
                (
                    event.edge.edge.caller_node,
                    event.edge.edge.callee_node,
                )
            )
            self.graph_edges += 1
            self.edges += 1
        elif kind == "call_site":
            require(
                self.active
                and event.call_site.graph_index == self.graphs - 1
                and event.call_site.HasField("call_site")
            )
            site = event.call_site.call_site
            self._referenced_nodes.add(site.caller_node)
            if site.HasField("callee_node"):
                self._referenced_nodes.add(site.callee_node)
            self.graph_call_sites += 1
            self.call_sites += 1
        elif kind == "completed":
            value = event.completed
            require(
                self.graphs == 1
                and value.graph_count == self.graphs
                and value.node_count == self.nodes
                and value.edge_count == self.edges
                and value.call_site_count == self.call_sites
            )
            require(self._referenced_nodes <= self._node_ids)
            require(self._root_node in self._node_ids)
            require(self._focus_node is None or self._focus_node in self._node_ids)
            self.active = False
            self.completed = True
        else:
            require(False)
            return

    def finish(self) -> None:
        if not self.completed or self.active:
            raise AnalysisError(
                grpc.StatusCode.DATA_LOSS,
                "call-graph stream ended without completion",
            )

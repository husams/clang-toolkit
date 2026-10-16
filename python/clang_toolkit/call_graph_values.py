"""Cycle-safe local queries over a collected static call graph."""

from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Literal

from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2
from clang_toolkit._generated.analysis.v1.call_graph_node_pb2 import CallGraphNode
from clang_toolkit._generated.analysis.v1 import call_graph_request_pb2
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit.match_values import BindingSelection


class CallGraphError(ValueError):
    """A local call-graph selection is missing or ambiguous."""


@dataclass(frozen=True)
class GroupedCall:
    """Calls between a caller/callee pair, retaining every site in source order."""

    caller: Any
    callee: Any | None
    call_sites: tuple[Any, ...]
    call_site_count: int
    unresolved_count: int


@dataclass(frozen=True)
class CallRouteStep:
    """One edge in a shortest route and the sites witnessing that edge."""

    caller: Any
    callee: Any
    call_sites: tuple[Any, ...]


def is_unresolved_call_site(site: Any) -> bool:
    """Classify indirect calls apart from known targets omitted by scope."""
    if site.HasField("callee_node"):
        return False
    if not site.HasField("facts"):
        # Older servers did not return call-dispatch facts.
        return True
    dispatch = site.facts.dispatch
    if dispatch == match_result_pb2.CALL_DISPATCH_INDIRECT:
        return True
    if dispatch in {
        match_result_pb2.CALL_DISPATCH_DIRECT,
        match_result_pb2.CALL_DISPATCH_VIRTUAL,
    }:
        return False
    return not (
        site.facts.static_callee_symbol_identity or site.facts.static_callee_name
    )


class CallGraph:
    """A convenient query wrapper that keeps the original protobuf available."""

    __slots__ = (
        "response",
        "_selector",
        "_nodes",
        "_edges",
        "_outgoing",
        "_incoming",
        "_sites_by_pair",
    )

    def __init__(
        self,
        response: call_graph_response_pb2.CallGraphResponse,
        *,
        selector: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(response, call_graph_response_pb2.CallGraphResponse):
            raise TypeError("CallGraph requires a CallGraphResponse")
        self.response = response
        self._selector = selector
        self._nodes = {
            node.node_index: node
            for node in response.nodes
            if not _synthetic_root(response, node)
        }
        self._edges = tuple(
            edge
            for edge in response.edges
            if edge.caller_node in self._nodes and edge.callee_node in self._nodes
        )
        self._outgoing = {node: [] for node in self._nodes}
        self._incoming = {node: [] for node in self._nodes}
        self._sites_by_pair: dict[tuple[int, int], list[Any]] = {}
        for edge in self._edges:
            self._outgoing[edge.caller_node].append(edge.callee_node)
            self._incoming[edge.callee_node].append(edge.caller_node)
        for site in response.call_sites:
            if site.HasField("callee_node"):
                self._sites_by_pair.setdefault(
                    (site.caller_node, site.callee_node), []
                ).append(site)

    @property
    def proto(self) -> call_graph_response_pb2.CallGraphResponse:
        """Return the underlying protobuf response."""
        return self.response

    def __getattr__(self, name: str) -> Any:
        # Keep raw response fields such as is_complete and availability easy to inspect.
        return getattr(self.response, name)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._nodes.values())

    def function(
        self, qualified_name: str | Any, *, signature: str | None = None,
        depth: int = 1
    ) -> Any:
        """Find one function by qualified name and optional exact type spelling."""
        if isinstance(qualified_name, BindingSelection):
            return self._function_for_binding(qualified_name, depth=depth)
        if not isinstance(qualified_name, str):
            raise TypeError("function requires a qualified name or retained binding")
        if not isinstance(qualified_name, str) or not qualified_name:
            raise ValueError("qualified_name must be a non-empty string")
        if signature is not None and (not isinstance(signature, str) or not signature):
            raise ValueError("signature must be a non-empty string")
        matches = [
            node
            for node in self._nodes.values()
            if node.HasField("function")
            and node.function.qualified_name == qualified_name
            and (signature is None or _signature(node) == signature)
        ]
        if not matches:
            raise CallGraphError(f"call graph has no function {qualified_name!r}")
        if len(matches) > 1:
            raise CallGraphError(
                f"function {qualified_name!r} is ambiguous; supply its signature"
            )
        return matches[0]

    def callers(
        self, target: int | str | Any, *, depth: int | Literal["all"] = 1
    ) -> CallGraph:
        """Return the bounded incoming neighborhood containing target."""
        if isinstance(target, BindingSelection):
            return self._select_binding(target, direction="in", depth=depth)
        return self._neighborhood(target, depth, reverse=True)

    def callees(
        self, target: int | str | Any, *, depth: int | Literal["all"] = 1
    ) -> CallGraph:
        """Return the bounded outgoing neighborhood containing target."""
        if isinstance(target, BindingSelection):
            return self._select_binding(target, direction="out", depth=depth)
        return self._neighborhood(target, depth, reverse=False)

    def shortest_path(
        self, source: int | str | Any, target: int | str | Any
    ) -> tuple[Any, ...] | None:
        """Return one shortest directed path, or None when no path is present."""
        start = self._node_index(source)
        finish = self._node_index(target)
        parents: dict[int, int | None] = {start: None}
        queue = deque([start])
        while queue and finish not in parents:
            current = queue.popleft()
            for neighbor in self._outgoing[current]:
                if neighbor in parents:
                    continue
                parents[neighbor] = current
                queue.append(neighbor)
        if finish not in parents:
            return None
        path: list[int] = []
        cursor: int | None = finish
        while cursor is not None:
            path.append(cursor)
            cursor = parents[cursor]
        path.reverse()
        return tuple(self._nodes[index] for index in path)

    def shortest_route(
        self, source: int | str | Any, target: int | str | Any
    ) -> tuple[CallRouteStep, ...] | None:
        """Return a shortest path with the call sites witnessing every step."""
        path = self.shortest_path(source, target)
        if path is None:
            return None
        steps: list[CallRouteStep] = []
        for caller, callee in zip(path, path[1:]):
            sites = tuple(
                self._sites_by_pair.get((caller.node_index, callee.node_index), ())
            )
            steps.append(CallRouteStep(caller, callee, sites))
        return tuple(steps)

    def grouped_calls(self) -> tuple[GroupedCall, ...]:
        """Group call sites by caller and resolved callee, preserving multiplicity."""
        grouped: dict[tuple[int, int | None], list[Any]] = {}
        for site in self.response.call_sites:
            if site.caller_node not in self._nodes:
                continue
            callee = site.callee_node if site.HasField("callee_node") else None
            if callee is not None and callee not in self._nodes:
                callee = None
            grouped.setdefault((site.caller_node, callee), []).append(site)
        return tuple(
            GroupedCall(
                self._nodes[caller],
                self._nodes.get(callee),
                tuple(sites),
                len(sites),
                sum(is_unresolved_call_site(site) for site in sites),
            )
            for (caller, callee), sites in sorted(
                grouped.items(),
                key=lambda item: (item[0][0], -1 if item[0][1] is None else item[0][1]),
            )
        )

    def recursive_components(self) -> tuple[tuple[Any, ...], ...]:
        """Return recursive strongly connected components without recursion limits."""
        seen: set[int] = set()
        finish: list[int] = []
        for start in sorted(self._nodes):
            if start in seen:
                continue
            seen.add(start)
            stack: list[tuple[int, Iterator[int]]] = [
                (start, iter(self._outgoing[start]))
            ]
            while stack:
                node, neighbors = stack[-1]
                neighbor = next(neighbors, None)
                if neighbor is None:
                    finish.append(node)
                    stack.pop()
                elif neighbor not in seen:
                    seen.add(neighbor)
                    stack.append((neighbor, iter(self._outgoing[neighbor])))

        assigned: set[int] = set()
        components: list[tuple[Any, ...]] = []
        for start in reversed(finish):
            if start in assigned:
                continue
            component: list[int] = []
            stack = [start]
            assigned.add(start)
            while stack:
                node = stack.pop()
                component.append(node)
                for neighbor in self._incoming[node]:
                    if neighbor not in assigned:
                        assigned.add(neighbor)
                        stack.append(neighbor)
            if len(component) > 1 or start in self._outgoing[start]:
                components.append(
                    tuple(self._nodes[item] for item in sorted(component))
                )
        return tuple(sorted(components, key=lambda part: part[0].node_index))

    def recursion_components(self) -> tuple[tuple[Any, ...], ...]:
        """Backward-compatible alias for recursive_components()."""
        return self.recursive_components()

    def _neighborhood(
        self, target: int | str | Any, depth: int, *, reverse: bool
    ) -> CallGraph:
        unlimited = depth == "all"
        if not unlimited and (type(depth) is not int or not 0 <= depth <= 32):
            raise ValueError("depth must be 0..32 or 'all'")
        start = self._node_index(target)
        distances = {start: 0}
        queue = deque([start])
        adjacency = self._incoming if reverse else self._outgoing
        while queue:
            current = queue.popleft()
            if not unlimited and distances[current] == depth:
                continue
            for neighbor in adjacency[current]:
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)
        selected = set(distances)
        response = call_graph_response_pb2.CallGraphResponse()
        response.CopyFrom(self.response)
        del response.nodes[:]
        del response.edges[:]
        del response.call_sites[:]
        response.ClearField("availability")
        completion_known = True
        is_complete = True
        record_count = 0

        def copy_record(source: Any, destination: Any) -> None:
            nonlocal completion_known, is_complete, record_count
            destination.CopyFrom(source)
            for availability in source.availability:
                response.availability.add().CopyFrom(availability)
            record_count += 1
            if source.HasField("is_complete"):
                is_complete = is_complete and source.is_complete
            else:
                completion_known = False

        ordered_nodes = sorted(selected)
        remap = {source: index for index, source in enumerate(ordered_nodes)}
        for source in ordered_nodes:
            node = response.nodes.add()
            copy_record(self._nodes[source], node)
            node.node_index = remap[source]
        for edge in self._edges:
            if edge.caller_node not in selected or edge.callee_node not in selected:
                continue
            source = edge.callee_node if reverse else edge.caller_node
            if not unlimited and distances[source] >= depth:
                continue
            output_edge = response.edges.add()
            copy_record(edge, output_edge)
            output_edge.caller_node = remap[edge.caller_node]
            output_edge.callee_node = remap[edge.callee_node]
        boundary_edges = 0
        for edge in self._edges:
            traversed = (
                edge.caller_node in selected
                and edge.callee_node in selected
                and (
                    unlimited
                    or distances[edge.callee_node if reverse else edge.caller_node]
                    < depth
                )
            )
            if not traversed and (
                edge.caller_node in selected or edge.callee_node in selected
            ):
                boundary_edges += 1
        boundary_call_sites = 0
        for call_site in self.response.call_sites:
            caller_selected = call_site.caller_node in selected
            callee_selected = (
                call_site.HasField("callee_node") and call_site.callee_node in selected
            )
            if call_site.HasField("callee_node"):
                source = call_site.callee_node if reverse else call_site.caller_node
                traversed = (
                    caller_selected
                    and callee_selected
                    and (unlimited or distances[source] < depth)
                )
            else:
                traversed = (
                    not reverse
                    and caller_selected
                    and (unlimited or distances[call_site.caller_node] < depth)
                )
            if not traversed:
                if caller_selected or callee_selected:
                    boundary_call_sites += 1
                continue
            output_site = response.call_sites.add()
            copy_record(call_site, output_site)
            output_site.caller_node = remap[call_site.caller_node]
            if call_site.HasField("callee_node"):
                if call_site.callee_node in remap:
                    output_site.callee_node = remap[call_site.callee_node]
                else:
                    output_site.ClearField("callee_node")
                    boundary_call_sites += 1
        response.root_node = (1 << 64) - 1
        response.focus_node = remap[start]
        response.selection_direction = (
            call_graph_request_pb2.CALL_GRAPH_DIRECTION_IN
            if reverse
            else call_graph_request_pb2.CALL_GRAPH_DIRECTION_OUT
        )
        if unlimited:
            response.ClearField("selection_max_depth")
            response.selection_unlimited_depth = True
        else:
            response.selection_max_depth = depth
            response.ClearField("selection_unlimited_depth")
        response.selection_boundary_edges += boundary_edges
        response.selection_boundary_call_sites += boundary_call_sites
        if completion_known and record_count:
            response.is_complete = is_complete
        else:
            response.ClearField("is_complete")
        return CallGraph(response, selector=self._selector)

    def _adjacency(self, *, reverse: bool) -> dict[int, list[int]]:
        return self._incoming if reverse else self._outgoing

    def _select_binding(
        self, target: Any, *, direction: str = "out",
        depth: int | Literal["all"] = 1
    ) -> CallGraph:
        if self._selector is None:
            raise CallGraphError(
                "exact retained selections are available on graphs returned by the console"
            )
        if depth != "all" and (
            type(depth) is not int or not 0 <= depth <= 32
        ):
            raise ValueError("depth must be 0..32 or 'all'")
        response = self._selector(target, direction=direction, max_depth=depth)
        return CallGraph(response, selector=self._selector)

    def _function_for_binding(
        self, target: BindingSelection[Any], *, depth: int
    ) -> Any:
        if type(depth) is not int or not 0 <= depth <= 32:
            raise ValueError("depth must be 0..32")
        target._owner.check(target._owner.client)
        identity = target.value.symbol_identity
        if identity:
            matches = [
                node
                for node in self._nodes.values()
                if node.symbol_identity == identity
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise CallGraphError(
                    "call-graph symbol identity is duplicated; select the call-graph overload"
                )
        if self._selector is None:
            raise CallGraphError(
                "binding has no call-graph identity; exact lookup needs a live console graph"
            )
        focused = self._selector(target, direction="out", max_depth=0)
        if (
            self.response.snapshot_generation
            and focused.snapshot_generation
            and self.response.snapshot_generation != focused.snapshot_generation
        ):
            raise CallGraphError("binding and call graph come from different snapshots")
        focus = next(
            (node for node in focused.nodes if node.node_index == focused.focus_node),
            None,
        )
        if focus is None or not focus.symbol_identity:
            raise CallGraphError(
                "native binding did not provide a stable call-graph identity"
            )
        matches = [
            node
            for node in self._nodes.values()
            if node.symbol_identity == focus.symbol_identity
        ]
        if len(matches) != 1:
            raise CallGraphError("binding is not a unique function in this call graph")
        return matches[0]

    def _node_index(self, target: int | str | Any) -> int:
        if isinstance(target, str):
            return self.function(target).node_index
        if isinstance(target, int) and not isinstance(target, bool):
            if target in self._nodes:
                return target
            raise CallGraphError(f"call graph has no node {target}")
        if isinstance(target, CallGraphNode):
            index = target.node_index
            local = self._nodes.get(index)
            if local is not None and target.SerializeToString() == local.SerializeToString():
                return index
            raise CallGraphError(
                "node does not belong to this call graph; select it from this graph"
            )
        raise TypeError(
            "target must be a node index, qualified name or call-graph node"
        )


def _synthetic_root(response: Any, node: Any) -> bool:
    return node.is_virtual_root or node.node_index == response.root_node


def _signature(node: Any) -> str:
    symbol = node.function
    if symbol.HasField("type") and symbol.type.spelling:
        return symbol.type.spelling
    return ""

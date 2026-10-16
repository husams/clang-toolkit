"""Real native ownership, focused callgraphs and compiled console acceptance."""

from __future__ import annotations

import asyncio
from contextlib import aclosing
from pathlib import Path
import subprocess
import sys

import grpc
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit import AsyncClient, CallGraph
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import analysis_service_pb2_grpc
from clang_toolkit.client import _call_graph_value_request
from clang_toolkit.cursors import CursorError
from clang_toolkit.match_values import MatchValueError
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("callgraph_refinement.feature")

SHOP = """void chargeCard() {}
void saveOrder() {}
void sendReceipt() {}
void checkout() { chargeCard(); saveOrder(); sendReceipt(); }
void apiRequest() { checkout(); }
void retryPayment() { chargeCard(); }
void indirect(void (*fn)()) { fn(); }
int not_callable = 7;
"""


def relationships(graph):
    """Retain multiplicity while excluding synthetic-root edges."""
    return [
        (
            graph.nodes[edge.caller_node].function.qualified_name,
            graph.nodes[edge.callee_node].function.qualified_name,
        )
        for edge in graph.edges
        if not edge.is_virtual_root_edge
    ]


@given(
    parsers.parse("an isolated callgraph server using {transport}"),
    target_fixture="callgraph_server",
)
def callgraph_server(transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server(transport, tmp_path, request)
    source = tmp_path / "shop.cc"
    source.write_text(SHOP, encoding="utf-8")
    return server, source


@when(
    "I inspect callgraphs from files trees handles and matched nodes",
    target_fixture="retained_callgraph_evidence",
)
def retained_callgraphs(callgraph_server):
    server, source = callgraph_server

    async def run():
        async with AsyncClient(server.endpoint) as client:
            baseline = await client.callgraph(source)
            assert baseline.is_complete
            assert len(relationships(baseline)) == 5
            tree = await client.parse(source)
            payments = await client.match_in(
                'functionDecl(isDefinition(), hasName("chargeCard")).bind("f")', tree
            )
            checkouts = await client.match_in(
                'functionDecl(isDefinition(), hasName("checkout")).bind("f")', tree
            )
            indirects = await client.match_in(
                'functionDecl(isDefinition(), hasName("indirect")).bind("f")', tree
            )
            calls = await client.match_in(
                'callExpr().bind("c")', checkouts[0].binding("f")
            )
            unresolved = await client.match_in(
                'callExpr().bind("c")', indirects[0].binding("f")
            )
            literals = await client.match_in('integerLiteral().bind("n")', tree)
            empty = await client.match_in(
                'functionDecl(hasName("absent")).bind("f")', tree
            )
            manifest = await client.discover_files([str(source)])
            described = await client.callgraph(manifest.inputs[0])
            assert relationships(described) == relationships(baseline)
            handle = await client.open_file(manifest.inputs[0])
            revision = payments._owner.revision
            stub = analysis_service_pb2_grpc.AnalysisServiceStub(client._channel)
            stale = _call_graph_value_request(client, payments[0].binding("f"))
            stale.binding.expected_result_revision += 1
            with pytest.raises(grpc.aio.AioRpcError) as error:
                async for _ in stub.StreamCallGraph(stale):
                    pass
            assert error.value.code() == grpc.StatusCode.ABORTED
            for options in ({}, {"projection": "recursive", "payload_depth": 1}):
                request = _call_graph_value_request(client, tree, **options)
                collected = await client.callgraph(tree, **options)
                unary = await stub.CallGraph(request)
                assert collected == unary, (
                    options,
                    [
                        field.name
                        for field in unary.DESCRIPTOR.fields
                        if getattr(collected, field.name) != getattr(unary, field.name)
                    ],
                )
                if options:
                    assert not collected.is_complete
            cycle_source = source.with_name("cycles.cc")
            cycle_source.write_text(
                "void b(); void a(){b();} void b(){a();} void self(){self();}\n"
                "void external(); void unused(); void use_external(){external();}\n"
                "void overloaded(int){} void overloaded(double){}\n"
                "template<class T> void dependent(T value){value();}\n",
                encoding="utf-8",
            )
            cycle_tree = await client.parse(cycle_source)
            cycle_graph = CallGraph(await client.callgraph(cycle_tree))
            for name in ("a", "self"):
                cycle_rows = await client.match_in(
                    f'functionDecl(isDefinition(), hasName("{name}")).bind("f")',
                    cycle_tree,
                )
                for direction, operation in (
                    ("out", cycle_graph.callees),
                    ("in", cycle_graph.callers),
                ):
                    for depth in (0, 1, 2):
                        native = await client.callgraph(
                            cycle_rows[0].binding("f"),
                            direction=direction,
                            max_depth=depth,
                        )
                        local = operation(name, depth=depth)
                        assert relationships(native) == relationships(local)
                        assert [
                            (s.facts.caller_name, s.facts.static_callee_name)
                            for s in native.call_sites
                        ] == [
                            (s.facts.caller_name, s.facts.static_callee_name)
                            for s in local.call_sites
                        ]
                        assert (
                            native.selection_boundary_edges
                            == local.selection_boundary_edges
                        )
                        assert (
                            native.selection_boundary_call_sites
                            == local.selection_boundary_call_sites
                        )
                        assert (
                            native.nodes[native.focus_node].function.qualified_name
                            == name
                        )
            declaration = await client.match_in(
                'functionDecl(hasName("external")).bind("f")', cycle_tree
            )
            callers = await client.callgraph(
                declaration[0].binding("f"), direction="in"
            )
            assert relationships(callers) == [("use_external", "external")]
            assert not callers.nodes[callers.focus_node].has_definition
            unused = await client.match_in(
                'functionDecl(hasName("unused")).bind("f")', cycle_tree
            )
            unused_graph = await client.callgraph(unused[0].binding("f"))
            assert not relationships(unused_graph)
            assert not unused_graph.nodes[unused_graph.focus_node].has_definition
            forward = await client.match_in(
                'functionDecl(hasName("b"), unless(isDefinition())).bind("f")',
                cycle_tree,
            )
            assert relationships(await client.callgraph(forward[0].binding("f"))) == [
                ("b", "a")
            ]
            with pytest.raises(AnalysisError):
                await client.callgraph(cycle_tree, "overloaded")
            dependent = await client.match_in(
                'functionDecl(hasName("dependent")).bind("f")', cycle_tree
            )
            with pytest.raises(AnalysisError) as error:
                await client.callgraph(dependent[0].binding("f"))
            assert error.value.code == grpc.StatusCode.FAILED_PRECONDITION
            default_source = source.with_name("default_argument.cc")
            default_source.write_text(
                "void leaf(){} void sink(int value=(leaf(),0)){} void invoke(){sink();}\n",
                encoding="utf-8",
            )
            default_tree = await client.parse(default_source)
            default_calls = await client.match_in(
                'callExpr(callee(functionDecl(hasName("leaf")))).bind("c")',
                default_tree,
            )
            exact_default = await client.callgraph(default_calls[0].binding("c"))
            assert relationships(exact_default) == [("invoke", "leaf")]
            assert exact_default.call_sites[0].facts.caller_name == "invoke"
            source.write_text("void replacement() {}\n", encoding="utf-8")
            refreshed = await client.callgraph(source)
            assert {
                n.function.qualified_name
                for n in refreshed.nodes
                if not n.is_virtual_root
            } == {"replacement"}
            source.unlink()

            for retained in (tree, handle):
                graph = await client.callgraph(retained)
                assert relationships(graph) == relationships(baseline)
                assert graph.snapshot_generation > 0
                assert graph.source_file == str(source)
                assert graph.source_revision
                assert graph.compilation_profile_id

            outgoing = await client.callgraph(checkouts[0].binding("f"))
            assert set(relationships(outgoing)) == {
                ("checkout", "chargeCard"),
                ("checkout", "saveOrder"),
                ("checkout", "sendReceipt"),
            }
            incoming = await client.callgraph(
                payments[0].binding("f"), direction="in", max_depth=2
            )
            assert set(relationships(incoming)) == {
                ("checkout", "chargeCard"),
                ("retryPayment", "chargeCard"),
                ("apiRequest", "checkout"),
            }
            assert incoming.HasField("focus_node")
            assert (
                incoming.nodes[incoming.focus_node].function.qualified_name
                == "chargeCard"
            )
            assert incoming.selection_max_depth == 2
            seed = await client.callgraph(payments[0].binding("f"), max_depth=0)
            assert not relationships(seed)
            assert any(n.function.qualified_name == "chargeCard" for n in seed.nodes)

            exact = await client.callgraph(calls[0].binding("c"))
            assert len(exact.call_sites) == 1 and len(relationships(exact)) == 1
            unknown = await client.callgraph(unresolved[0].binding("c"))
            assert len(unknown.call_sites) == 1
            assert not unknown.call_sites[0].HasField("callee_node")
            assert not relationships(unknown)
            assert payments._owner.revision == revision
            assert (
                len(await client.match_in("compoundStmt()", payments[0].binding("f")))
                == 1
            )
            assert len((await client.cfg(checkouts[0].binding("f"))).graphs) == 1

            for invalid in (
                literals[0].binding("n"),
                empty.binding("f"),
                calls.binding("c"),
            ):
                with pytest.raises((AnalysisError, MatchValueError, ValueError)):
                    await client.callgraph(invalid)
            for invalid, kwargs in (
                (tree, {"direction": "in", "max_depth": 2}),
                (calls[0].binding("c"), {"max_depth": 0}),
            ):
                with pytest.raises((AnalysisError, ValueError)):
                    await client.callgraph(invalid, **kwargs)
            async with AsyncClient(server.endpoint) as foreign:
                with pytest.raises(MatchValueError):
                    await foreign.callgraph(tree)
            await client.close_file(handle)
            with pytest.raises((AnalysisError, CursorError, MatchValueError)):
                await client.callgraph(handle)
            await client.close_file(tree)
            with pytest.raises((AnalysisError, CursorError, MatchValueError)):
                await client.callgraph(tree)
            # Closing the parsed tree does not invalidate independent matched values.
            assert relationships(await client.callgraph(checkouts[0].binding("f")))
            return len(incoming.nodes), len(incoming.edges)

    return asyncio.run(run())


@then("exact graph selections preserve their native snapshot and static coverage")
def retained_graphs_are_exact(retained_callgraph_evidence):
    nodes, edges = retained_callgraph_evidence
    assert nodes >= 4 and edges >= 3


@when(
    "I run the practical retained callgraph console script",
    target_fixture="callgraph_console",
)
def callgraph_console(callgraph_server, tmp_path):
    server, _ = callgraph_server
    root = Path(__file__).resolve().parents[2]
    libraries = tmp_path / "empty-libraries"
    libraries.mkdir()
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "clang_toolkit.cli.app",
            "--server",
            server.endpoint,
            "--script-engine",
            "compiled",
            "--lib-dir",
            str(libraries),
            "--script",
            str(root / "examples/callgraph_reuse.ctk"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
    )


@then("the console returns shallow graph values and the selected caller edges")
def console_graph_values(callgraph_console):
    run = callgraph_console
    assert run.returncode == 0, run.stdout + run.stderr
    assert "COMPLETE=true" in run.stdout
    assert "LOCAL_EDGES=3" in run.stdout
    assert "Call graph: 4 functions, 3 calls, 3 call sites, 0 unresolved; complete" in run.stdout
    assert "[seed]" in run.stdout
    for evidence in (
        "REACHABLE_FUNCTIONS=5",
        "REACHABLE_CALLS=4",
        "ROUTE_STEPS=2",
        "CALL_GROUPS=6",
        "SELECTED_SITES=1",
        "UNRESOLVED_SITES=1",
        "CFG_GRAPHS=1",
    ):
        assert evidence in run.stdout
    for edge in (
        "demo::checkout -> demo::chargeCard",
        "demo::retryPayment -> demo::chargeCard",
        "demo::apiRequest -> demo::checkout",
    ):
        assert edge in run.stdout
    assert "demo::checkout -> demo::saveOrder" not in run.stdout
    assert "demo::checkout -> demo::sendReceipt" not in run.stdout


@when(
    "I select all reachable calls from retained callable bindings",
    target_fixture="unlimited_graph_evidence",
)
def unlimited_callgraph(callgraph_server):
    server, source = callgraph_server
    chain_source = source.with_name("chain.cc")
    definitions = [f"void f{index}();" for index in range(37)]
    for index in range(37):
        calls = [f"f{index + 1}();"] if index < 36 else ["f1();"]
        if index == 0:
            calls.append("f1();")
        definitions.append(f"void f{index}() {{ {' '.join(calls)} }}")
    definitions.append("void disconnected() {}")
    chain_source.write_text("\n".join(definitions), encoding="utf-8")

    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(chain_source)
            seeds = await client.match_in(
                'functionDecl(isDefinition(), hasName("f0")).bind("f")', tree
            )
            tail = await client.match_in(
                'functionDecl(isDefinition(), hasName("f36")).bind("f")', tree
            )
            middle = await client.match_in(
                'functionDecl(isDefinition(), hasName("f18")).bind("f")', tree
            )
            seed = seeds[0].binding("f")
            default = await client.callgraph(seed)
            bounded = await client.callgraph(seed, max_depth=32)
            outgoing = await client.callgraph(seed, max_depth="all")
            incoming = await client.callgraph(
                tail[0].binding("f"), direction="in", max_depth="all"
            )
            both = await client.callgraph(
                middle[0].binding("f"), direction="both", max_depth="all"
            )
            events = [
                event
                async for event in client.callgraph_stream(seed, max_depth="all")
            ]
            assert events[0].graph_started.graph.selection_unlimited_depth
            assert sum(event.HasField("edge") for event in events) == len(outgoing.edges)
            assert sum(event.HasField("call_site") for event in events) == len(outgoing.call_sites)

            def cancel_after_header(event):
                if event.HasField("graph_started"):
                    raise RuntimeError("stop unlimited stream after header")

            with pytest.raises(RuntimeError, match="stop unlimited stream"):
                await client.stream_callgraph(
                    seed, max_depth="all", on_event=cancel_after_header
                )
            chain_source.unlink()
            retained_after_removal = await client.callgraph(seed, max_depth="all")
            limited = []
            with pytest.raises(AnalysisError) as error:
                await client.stream_callgraph(
                    seed, max_depth="all", max_nodes=2, on_event=limited.append
                )
            assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            return (
                len(default.nodes),
                len(default.edges),
                len(bounded.nodes),
                len(outgoing.nodes),
                len(outgoing.edges),
                len(outgoing.call_sites),
                len(incoming.nodes),
                len(both.nodes),
                relationships(outgoing),
                {node.function.qualified_name for node in outgoing.nodes},
                relationships(retained_after_removal),
                bool(outgoing.selection_unlimited_depth),
            )

    return asyncio.run(run())


@then("unlimited callgraph depth crosses 32 hops and terminates on cycles")
def unlimited_callgraph_is_complete(unlimited_graph_evidence):
    (
        default_nodes,
        default_edges,
        bounded_nodes,
        all_nodes,
        all_edges,
        all_sites,
        incoming_nodes,
        both_nodes,
        relationships_all,
        names_all,
        relationships_retained,
        unlimited_metadata,
    ) = unlimited_graph_evidence
    assert (default_nodes, default_edges) == (3, 2)
    assert bounded_nodes == 34  # Synthetic root plus f0 through f32.
    assert all_nodes == incoming_nodes == both_nodes == 38
    assert all_edges == all_sites == 38
    assert len(relationships_all) == 38
    assert relationships_retained == relationships_all
    assert "disconnected" not in names_all
    assert unlimited_metadata


@given(
    "an isolated callgraph server with small messages", target_fixture="large_callgraph"
)
def large_callgraph(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server("unix", tmp_path, request, max_send_bytes=4096)
    source = tmp_path / "many_calls.cc"
    source.write_text(
        "void leaf() {}\n"
        + "\n".join(f"void caller_{i}() {{ leaf(); leaf(); }}" for i in range(80)),
        encoding="utf-8",
    )
    return server, source


@when(
    "I consume a callgraph larger than one message",
    target_fixture="callgraph_stream_evidence",
)
def stream_large_callgraph(large_callgraph):
    server, source = large_callgraph

    async def run():
        async with AsyncClient(server.endpoint) as client:
            seen = []

            async def consume(event):
                await asyncio.sleep(0)
                seen.append(event)

            completed = await client.stream_callgraph(source, on_event=consume)
            assert seen[-1].HasField("completed")
            assert completed.node_count == sum(e.HasField("node") for e in seen)
            assert completed.edge_count == sum(e.HasField("edge") for e in seen)
            assert completed.call_site_count == sum(
                e.HasField("call_site") for e in seen
            )
            failed = []
            with pytest.raises(AnalysisError) as error:
                await client.stream_callgraph(
                    source, max_nodes=1, on_event=failed.append
                )
            assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
            assert not any(e.HasField("completed") for e in failed)
            async with aclosing(client.callgraph_stream(source)) as events:
                first = await anext(events)
                assert not first.HasField("completed")

            def stop_consumer(event):
                raise RuntimeError("consumer stopped")

            with pytest.raises(RuntimeError, match="consumer stopped"):
                await client.stream_callgraph(source, on_event=stop_consumer)
            # Early close must release the native lane before another query.
            tree = await asyncio.wait_for(client.parse(source), timeout=10)
            assert tree is not None
            return sum(e.ByteSize() for e in seen), max(e.ByteSize() for e in seen)

    return asyncio.run(run())


@then("event bounds counts cancellation and completion remain explicit")
def stream_is_bounded(callgraph_stream_evidence):
    total, largest = callgraph_stream_evidence
    assert total > 4096
    assert largest < 4096

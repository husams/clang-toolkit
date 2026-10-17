"""Real native ownership, focused callgraphs and compiled console acceptance."""

from __future__ import annotations

import asyncio
from contextlib import aclosing
from pathlib import Path
import subprocess
import shutil
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
    "I filter system headers and custom callable boundaries from retained inputs",
    target_fixture="boundary_graphs",
)
def boundary_graphs(callgraph_server):
    server, source = callgraph_server
    own_header = source.with_name("project.hpp")
    own_header.write_text(
        "namespace app { inline void leaf() {} inline void behindSystem() {} "
        "inline void work() { leaf(); } }\n"
        "namespace vendor { inline void bridge() { app::leaf(); } }\n"
    )
    system_header = source.with_name("system.hpp")
    system_header.write_text(
        "#pragma GCC system_header\n"
        "namespace system_lib { inline void bridge() { app::behindSystem(); } }\n"
    )
    source.write_text(
        '#include "project.hpp"\n#include "system.hpp"\n'
        "void entry() { app::work(); vendor::bridge(); system_lib::bridge(); }\n"
    )
    matcher = 'functionDecl(unless(matchesName("(^|::)vendor::")))'

    async def run():
        async with AsyncClient(server.endpoint) as client:
            baseline = await client.callgraph(source)
            filename = await client.callgraph(source, exclude_system_headers=True)
            tree = await client.parse(source)
            rows = await client.match_in(
                'functionDecl(hasName("entry")).bind("f")', tree
            )
            binding = rows[0].binding("f")
            parsed = await client.callgraph(tree, exclude_system_headers=True)
            assert filename == parsed
            manifest = await client.discover_files([str(source)])
            handle = await client.open_file(manifest.inputs[0])
            assert await client.callgraph(handle, exclude_system_headers=True) == filename
            matched = await client.callgraph(
                binding, exclude_system_headers=True, max_depth="all"
            )
            custom = await client.callgraph(
                binding, exclude_system_headers=True, node_filter=matcher, max_depth="all"
            )
            stub = analysis_service_pb2_grpc.AnalysisServiceStub(client._channel)
            unary = await stub.CallGraph(_call_graph_value_request(
                client, binding, exclude_system_headers=True, node_filter=matcher,
                max_depth="all",
            ))
            assert unary == custom
            assert custom.exclude_system_headers and custom.node_filter == matcher
            paths = await client.callgraph(
                tree, node_filter='functionDecl(isExpansionInFileMatching("project[.]hpp$"))'
            )
            for rule in (
                'functionDecl(anyOf(matchesName("(^|::)app::"), hasName("entry")))',
                'functionDecl(anyOf(matchesName("(^|::)app::"), hasName("entry")), '
                'unless(isExpansionInFileMatching("/generated/")))',
                'functionDecl(unless(cxxMethodDecl()))',
            ):
                assert (await client.callgraph(tree, node_filter=rule)).is_complete
            small = await client.callgraph(
                tree, node_filter='functionDecl(hasName("entry"))',
                max_nodes=2, max_call_sites=3,
            )
            assert len(small.nodes) == 2 and len(small.call_sites) == 3
            assert all(site.caller_node != small.root_node for site in small.call_sites)
            for invalid in ("stmt()", "functionDecl(badMatcher())"):
                with pytest.raises(AnalysisError) as error:
                    await client.callgraph(tree, node_filter=invalid)
                assert error.value.code == grpc.StatusCode.INVALID_ARGUMENT
            with pytest.raises(AnalysisError) as error:
                await client.callgraph(binding, node_filter='functionDecl(hasName("absent"))')
            assert error.value.code == grpc.StatusCode.NOT_FOUND
            source.unlink()
            own_header.unlink()
            system_header.unlink()
            assert await client.callgraph(
                binding, exclude_system_headers=True, node_filter=matcher, max_depth="all"
            ) == custom
            await rows.aclose()
            await client.close_file(tree)
            await client.close_file(handle)
            status = await client.resource_status()
            assert status.explicit_file_leases == status.result_cursors == status.active_work == 0
            return baseline, filename, matched, custom, paths

    return asyncio.run(run())


@then("filtered callgraphs keep user headers and stop at excluded callables")
def boundaries_are_respected(boundary_graphs):
    baseline, filename, matched, custom, paths = boundary_graphs

    def names(graph):
        assert graph.is_complete
        return {
            n.function.qualified_name for n in graph.nodes
            if not n.is_virtual_root and n.HasField("function")
        }

    assert "system_lib::bridge" in names(baseline)
    assert names(filename) == {
        "entry", "app::leaf", "app::behindSystem", "app::work", "vendor::bridge"
    }
    assert names(matched) == {"entry", "app::work", "app::leaf", "vendor::bridge"}
    assert names(custom) == {"entry", "app::work", "app::leaf"}
    assert "entry" not in names(paths) and "app::work" in names(paths)
    assert filename.external_edges_omitted > 0
    assert ("entry", "app::work") in relationships(custom)
    assert ("app::work", "app::leaf") in relationships(custom)
    assert any(
        s.facts.static_callee_name == "system_lib::bridge" and not s.HasField("callee_node")
        for s in custom.call_sites
    )


@when(
    "I exclude system root call sites from filename parsed and matched inputs",
    target_fixture="root_site_graphs",
)
def root_site_graphs(callgraph_server):
    server, source = callgraph_server
    system_header = source.with_name("system_roots.hpp")
    system_header.write_text(
        "#pragma GCC system_header\n"
        "namespace system_lib { inline int leaf() { return 1; } }\n"
        "inline int system_global = system_lib::leaf();\n"
        "#define SYSTEM_ROOT_CALL() system_lib::leaf()\n"
    )
    own_header = source.with_name("user_roots.hpp")
    own_header.write_text(
        "namespace app { inline int leaf() { return 2; } "
        "inline int work() { system_lib::leaf(); return leaf(); } }\n"
        "inline int user_global = app::leaf();\n"
        "inline int user_macro_global = SYSTEM_ROOT_CALL();\n"
    )
    source.write_text(
        '#include "system_roots.hpp"\n#include "user_roots.hpp"\n'
        "int main_global = app::leaf();\n"
        "int entry() { return app::work(); }\n"
    )
    matcher = 'functionDecl(anyOf(matchesName("(^|::)app::"), hasName("entry")))'

    async def run():
        async with AsyncClient(server.endpoint) as client:
            baseline = await client.callgraph(source, node_filter=matcher)
            assert len(baseline.call_sites) == 7
            tree = await client.parse(source)
            rows = await client.match_in(
                'functionDecl(hasName("entry")).bind("f")', tree
            )
            binding = rows[0].binding("f")
            options = dict(exclude_system_headers=True, node_filter=matcher,
                           max_call_sites=6)
            filename = await client.callgraph(source, **options)
            parsed = await client.callgraph(tree, **options)
            matched = await client.callgraph(binding, max_depth="all", **options)
            assert filename == parsed
            stub = analysis_service_pb2_grpc.AnalysisServiceStub(client._channel)
            assert await stub.CallGraph(_call_graph_value_request(
                client, tree, **options
            )) == parsed
            source.unlink()
            own_header.unlink()
            system_header.unlink()
            assert await client.callgraph(tree, **options) == parsed
            assert await client.callgraph(binding, max_depth="all", **options) == matched
            await rows.aclose()
            await client.close_file(tree)
            status = await client.resource_status()
            assert (status.explicit_file_leases, status.result_cursors,
                    status.active_work, status.reserved_bytes) == (0, 0, 0, 0)
            return filename, parsed, matched

    return asyncio.run(run())


@then("system root facts are absent and user header calls keep their snapshot")
def system_root_facts_are_absent(root_site_graphs):
    filename, parsed, matched = root_site_graphs
    for graph in (filename, parsed, matched):
        assert graph.is_complete and graph.exclude_system_headers
        assert {n.function.qualified_name for n in graph.nodes if not n.is_virtual_root} == {
            "app::leaf", "app::work", "entry"
        }
        assert all(not s.location.file.endswith("system_roots.hpp") for s in graph.call_sites)
        assert any(s.facts.caller_name == "app::work" and
                   s.facts.static_callee_name == "system_lib::leaf" and
                   not s.HasField("callee_node") for s in graph.call_sites)
    for graph in (filename, parsed):
        assert len(graph.call_sites) == 6
        roots = [s for s in graph.call_sites if s.caller_node == graph.root_node]
        assert len(roots) == 3
        assert sum(s.location.file.endswith("user_roots.hpp") for s in roots) == 2
        assert any(s.facts.static_callee_name == "system_lib::leaf" for s in roots)
    assert len(matched.call_sites) == 3
    assert all(s.caller_node != matched.root_node for s in matched.call_sites)


@when(
    parsers.parse("I run the header boundary console example with {engine}"),
    target_fixture="boundary_console",
)
def boundary_console(callgraph_server, tmp_path, engine):
    server, _ = callgraph_server
    root = Path(__file__).resolve().parents[2]
    libraries = tmp_path / "empty-boundary-libraries"
    libraries.mkdir()
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
         "--script-engine", engine, "--lib-dir", str(libraries), "--script",
         str(root / "examples/callgraph_boundaries.ctk")],
        cwd=root, capture_output=True, text=True, timeout=60,
    )


@then("the console excludes standard library and custom namespace nodes")
def boundary_console_is_complete(boundary_console):
    run = boundary_console
    assert run.returncode == 0, run.stdout + run.stderr
    counts = {}
    for line in run.stdout.splitlines():
        name, _, value = line.partition("=")
        if name in {"FILENAME_NODES", "PARSED_NODES"}:
            counts[name] = int(value)
    # Whole-TU inventories can also contain source-less builtin callables;
    # their presence depends on the platform's C++ headers.
    assert counts["FILENAME_NODES"] == counts["PARSED_NODES"] >= 5
    for expected in (
        "MATCHED_DEFAULT_DEPTH_NODES=4",
        "MATCHED_NODES=5", "CUSTOM_NODES=4", "COMPLETE=true",
        "project::check -> project::leaf", "entry -> project::check",
        "entry -> vendor::trace",
    ):
        assert expected in run.stdout
    custom_output = run.stdout.split("CUSTOM_NODES=4", 1)[1]
    assert "vendor::" not in custom_output and "std::" not in run.stdout
    assert all(name in custom_output for name in ("project::leaf", "project::check", "entry"))


@when(
    "I inspect a header va_list callable through retained graph inputs",
    target_fixture="header_va_list_graphs",
)
def header_va_list_graphs(callgraph_server):
    server, source = callgraph_server
    header = source.with_name("va_list.hpp")
    header.write_text(
        "namespace demo { inline void copyVaList(__builtin_va_list) {} "
        "inline void chargeCard() { __builtin_va_list arguments; "
        "copyVaList(arguments); } }\n",
        encoding="utf-8",
    )
    source = source.with_name("va_list.cc")
    source.write_text(
        '#include "va_list.hpp"\nvoid entry() { demo::chargeCard(); }\n',
        encoding="utf-8",
    )
    target_cases = [
        ("x86_64-unknown-linux-gnu", "__va_list_tag::__va_list_tag", 1),
        ("aarch64-unknown-linux-gnu", "std::__va_list::__va_list", 2),
        ("armv7-unknown-linux-gnueabihf", "std::__va_list::__va_list", 2),
    ]

    async def run():
        async with AsyncClient(server.endpoint) as client:
            results = []
            for target, constructor, expected_constructors in target_cases:
                compile_arguments = [
                    "-std=c++20",
                    f"-I{source.parent}",
                    f"--target={target}",
                ]
                filename_graph = await client.callgraph(
                    source, compile_arguments=compile_arguments
                )
                repeated_graph = await client.callgraph(
                    source, compile_arguments=compile_arguments
                )
                tree = await client.parse(
                    source, compile_arguments=compile_arguments
                )
                tree_graph = await client.callgraph(tree)
                charge_card = await client.match_in(
                    'functionDecl(isDefinition(), hasName("chargeCard")).bind("f")',
                    tree,
                )
                matched_graph = await client.callgraph(
                    charge_card[0].binding("f"), max_depth="all"
                )
                main_file_graph = await client.callgraph(
                    source,
                    compile_arguments=compile_arguments,
                    main_file_only=True,
                )
                results.append(
                    (
                        target,
                        constructor,
                        expected_constructors,
                        filename_graph,
                        repeated_graph,
                        tree_graph,
                        matched_graph,
                        main_file_graph,
                    )
                )
            return results

    return asyncio.run(run())


@then("full-scope callgraphs preserve the header callable")
def header_va_list_callgraphs_are_complete(header_va_list_graphs):
    for (
        target,
        constructor,
        expected_constructors,
        filename,
        repeated,
        tree,
        matched,
        main_file,
    ) in header_va_list_graphs:
        for graph in (filename, tree):
            assert graph.is_complete, target
            names = {
                node.function.qualified_name
                for node in graph.nodes
                if not node.is_virtual_root and node.HasField("function")
            }
            assert {"entry", "demo::chargeCard", constructor}.issubset(names), target
            assert (
                sum(
                    node.HasField("function")
                    and node.function.qualified_name == constructor
                    for node in graph.nodes
                )
                >= expected_constructors
            ), target
            assert (
                relationships(graph).count(("demo::chargeCard", constructor))
                >= expected_constructors
            ), target
        assert matched.is_complete, target
        assert (
            matched.nodes[matched.focus_node].function.qualified_name
            == "demo::chargeCard"
        ), target
        assert (
            relationships(matched).count(("demo::chargeCard", constructor))
            >= expected_constructors
        ), target
        assert filename.SerializeToString() == repeated.SerializeToString(), target
        assert main_file.is_complete and main_file.main_file_only, target
        main_file_names = {
            node.function.qualified_name
            for node in main_file.nodes
            if not node.is_virtual_root and node.HasField("function")
        }
        assert "demo::chargeCard" not in main_file_names, target
        assert constructor not in main_file_names, target
        assert main_file.external_edges_omitted > 0, target


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


@given(parsers.parse("a callgraph server with node budget {budget:d} using {transport}"),
       target_fixture="node_budget_server")
def node_budget_server(budget, transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server(transport, tmp_path, request, call_graph_nodes=budget)
    source = tmp_path / "budget.cc"
    source.write_text(SHOP, encoding="utf-8")
    return server, source, budget


@when("I override callgraph node budgets through filename tree and matched inputs",
      target_fixture="node_budget_evidence")
def inspect_node_budgets(node_budget_server):
    server, source, budget = node_budget_server

    async def run():
        async with AsyncClient(server.endpoint) as client:
            async with await client.parse(source) as tree:
                async with await client.match_in(
                    'functionDecl(isDefinition(), hasName("apiRequest")).bind("f")', tree
                ) as rows:
                    targets = (source, tree, rows[0].binding("f"))
                    counts = []
                    for target in targets:
                        if budget:
                            with pytest.raises(AnalysisError) as error:
                                await client.callgraph(target)
                            assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
                        else:
                            assert (await client.callgraph(target)).is_complete
                        for maximum in (100001, "all", 0):
                            graph = await client.callgraph(target, max_nodes=maximum)
                            assert graph.is_complete
                            counts.append(len(graph.nodes))
                        with pytest.raises(AnalysisError) as error:
                            await client.callgraph(target, max_nodes=1)
                        assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
                        events = []
                        async for event in client.callgraph_stream(target, max_nodes="all"):
                            events.append(event)
                        assert events[-1].HasField("completed")
                        assert events[-1].completed.is_complete
                        assert sum(event.HasField("node") for event in events) == counts[-1]
                    before = await client.callgraph(rows[0].binding("f"), max_nodes="all", max_depth="all")
                    source.unlink()
                    after = await client.callgraph(rows[0].binding("f"), max_nodes="all", max_depth="all")
                    assert before.SerializeToString() == after.SerializeToString()
                    assert after.selection_unlimited_depth
                    assert len(after.nodes) == 6
            status = await client.resource_status()
            assert status.explicit_file_leases == status.result_cursors == status.active_work == 0
            return counts

    return asyncio.run(run())


@then("node budgets retain complete graphs and snapshot ownership")
def verify_node_budgets(node_budget_evidence):
    assert node_budget_evidence == [8, 8, 8, 8, 8, 8, 3, 3, 3]


@when("I use optional strict directory filters on all retained inputs",
      target_fixture="strict_graphs")
def strict_graphs(callgraph_server):
    server, source = callgraph_server
    fixture = source.parent / "strict-headers"
    root = Path(__file__).resolve().parents[2]
    shutil.copytree(root / "examples/callgraph_strict_filters", fixture)
    source = fixture / "main.cc"
    matcher = 'functionDecl(unless(isExpansionInFileMatching("(^|/)(vendor|generated)/")))'

    async def run():
        async with AsyncClient(server.endpoint) as client:
            options = dict(exclude_system_headers=True, node_filter=matcher)
            ordinary = await client.callgraph(source, **options)
            assert not ordinary.strict_node_filter and len(ordinary.call_sites) == 4
            tree = await client.parse(source)
            rows = await client.match_in(
                'functionDecl(hasName("entry"), isDefinition()).bind("f")', tree
            )
            binding = rows[0].binding("f")
            options.update(strict_node_filter=True, max_call_sites=2)
            filename = await client.callgraph(source, **options)
            parsed = await client.callgraph(tree, **options)
            matched = await client.callgraph(binding, max_depth="all", **options)
            assert filename == parsed
            assert len(filename.edges) == 5 and len(matched.edges) == 2
            stub = analysis_service_pb2_grpc.AnalysisServiceStub(client._channel)
            assert await stub.CallGraph(_call_graph_value_request(client, tree, **options)) == parsed
            seen = []
            completed = await client.stream_callgraph(tree, on_event=seen.append, **options)
            assert completed.call_site_count == 2
            assert seen[0].graph_started.graph.strict_node_filter
            streamed = [event async for event in client.callgraph_stream(binding, max_depth="all", **options)]
            assert streamed[-1].completed.call_site_count == 2
            for file in fixture.rglob("*"):
                if file.is_file():
                    file.unlink()
            assert await client.callgraph(tree, **options) == parsed
            assert await client.callgraph(binding, max_depth="all", **options) == matched
            await rows.aclose()
            await client.close_file(tree)
            status = await client.resource_status()
            assert (status.explicit_file_leases, status.result_cursors,
                    status.active_work, status.reserved_bytes) == (0, 0, 0, 0)
            return filename, parsed, matched

    return asyncio.run(run())


@then("strict graphs contain only the project calls without reparsing")
def strict_graphs_are_project_only(strict_graphs):
    for graph in strict_graphs:
        assert graph.strict_node_filter and graph.is_complete
        assert len(graph.nodes) == 4 and len(graph.call_sites) == 2
        assert {n.function.qualified_name for n in graph.nodes if not n.is_virtual_root} == {
            "project::leaf", "project::work", "entry"
        }
        assert {s.facts.static_callee_name for s in graph.call_sites} == {
            "project::leaf", "project::work"
        }
        assert all(s.HasField("callee_node") and s.caller_node != graph.root_node
                   for s in graph.call_sites)


@when(parsers.parse("I run the strict directory filter console example with {engine}"),
      target_fixture="strict_console")
def strict_console(callgraph_server, tmp_path, engine):
    server, _ = callgraph_server
    root = Path(__file__).resolve().parents[2]
    libraries = tmp_path / "empty-strict-libraries"
    libraries.mkdir()
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
         "--script-engine", engine, "--lib-dir", str(libraries), "--script",
         str(root / "examples/callgraph_strict_filters.ctk"),
         "source=examples/callgraph_strict_filters/main.cc", f"output={tmp_path}"],
        cwd=root, capture_output=True, text=True, timeout=60,
    )


@then("the strict console prints project-only sites for all three input forms")
def strict_console_is_project_only(strict_console):
    run = strict_console
    assert run.returncode == 0, run.stdout + run.stderr
    assert "DEFAULT: sites=4, strict=false" in run.stdout
    for label, edges in (("FILENAME", 5), ("PARSED", 5), ("MATCHED", 2)):
        assert f"{label}: nodes=4, edges={edges}, sites=2, root_sites=0, strict=true, complete=true" in run.stdout
        assert f"{label}_CALL: project::work -> project::leaf" in run.stdout
        assert f"{label}_CALL: entry -> project::work" in run.stdout
    assert "third_party::trace" not in run.stdout
    assert "project::generated_call" not in run.stdout

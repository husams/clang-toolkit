# Streaming CFGs and reusing native trees

`StreamCfg` builds a native Clang CFG for each selected function and sends its blocks one at a time. A parsed tree, opened file handle or retained function binding reuses its pinned AST. Changing CFG build options rebuilds the CFG without reparsing that tree. This phase does not cache CFGs or implement local-variable dataflow analysis.

## Console

Run [the example script](../examples/cfg_reuse.ctk) from the repository root:

```text
ctk --script-engine compiled --script examples/cfg_reuse.ctk
```

The script parses [cfg_reuse.cc](../examples/cfg_reuse.cc) once, matches its function and uses both forms:

```ctk
let tree = parse "examples/cfg_reuse.cc"
let functions = match functionDecl(isDefinition(), hasName("demo::work")).bind("f") in tree
cfg "demo::work" in tree
cfg in functions[0].f
let flow = cfg in functions[0].f
print flow.graphs[0].blocks.length
```

A standalone command prints `graph_started`, `block`, `graph_completed` and `completed` events as ProtoJSON. Assignment collects the graph into the usual `graphs`, `blocks` and `elements` value. A binding selects the exact concrete function or method; omit the function name for that form. A name on a tree or file selects all concrete definition overloads with that exact qualified name.

The full example was verified through a terminal console. After the two graph streams, its final printed lines are `1`, `5`, `1`: one collected graph, five blocks and one return-statement match from the still-reusable function binding.

## Python

```python
from contextlib import aclosing
from clang_toolkit import AsyncClient

async def inspect(address):
    async with AsyncClient(address) as client:
        tree = await client.parse("examples/cfg_reuse.cc")
        functions = await client.match_in(
            'functionDecl(isDefinition(), hasName("demo::work")).bind("f")', tree
        )
        async with aclosing(client.cfg_stream(functions[0].binding("f"))) as events:
            async for event in events:
                if event.HasField("block"):
                    print(event.block.graph_index, event.block.block.block_index)
        # Reaching here means completion counts and terminal status were checked.
        flow = await client.cfg(tree, "demo::work")  # Explicit collector.
        return len(flow.graphs[0].blocks)
```

For callbacks, use `await client.stream_cfg(tree, "demo::work", on_event=consume)`; callbacks may be asynchronous and are awaited before reading the next event. The synchronous equivalents are `client.stream_cfg("demo::work", path=tree, on_event=consume)` and `client.cfg(functions[0].binding("f"))`. Closing the async iterator early or raising from a callback cancels the RPC. Close retained values or the owning client when finished.

## Contract and limits

Each graph starts with a request-local index, snapshot generation and function/entry/exit/linearity metadata, followed by blocks sorted by native block ID and a graph completion containing block/element counts and semantic completeness. The final request completion contains only totals. Success also requires terminal gRPC OK. Earlier events remain provisional if the request fails, even when an earlier graph completed.

The server bounds each event, rather than the aggregate stream, by its configured response byte limit. Function, block and element budgets still apply across the entire request. A single oversized block fails explicitly with `RESOURCE_EXHAUSTED`; block chunking is not implemented. The legacy unary `Cfg` RPC additionally bounds the collected response. Python `cfg()` and console assignment explicitly collect data in client memory; use streaming for larger results.

Successor/predecessor order and unreachable/null edge slots are preserved. Edges may reference blocks that arrive later. Semantic `is_complete` describes available analysis fields and is separate from successful stream completion. Graph header availability covers function metadata; each block carries its own availability. Collectors combine them into the compatibility graph.

Streaming removes the accumulated serialized graph from the server's normal path. Clang still builds one native CFG before serializing its blocks. The native snapshot stays pinned and its execution lane stays locked while a consumer applies backpressure. Slow consumers therefore hold those resources until completion, cancellation or deadline. Finish or cancel the stream before issuing another native query on that same snapshot from a callback.

Retained references are checked for owner, lifetime, resource scope and result revision using the existing matcher machinery. CFG construction leaves the parsed tree and matched rows unchanged. Closed, expired or stale targets fail; they never fall back to reparsing. Detached JSON has no native identity. Non-function bindings and dependent or bodyless functions fail explicitly. Existing file-based calls continue to work.

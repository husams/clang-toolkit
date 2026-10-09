# C++ reasoning recipes

All examples use `Client` and typed matchers from [matchers-and-values.md](matchers-and-values.md). `source` is the user-selected file path and `working_directory` is the project root visible to the server.

## Inventory declarations in a translation unit

```python
from clang_toolkit import Client
from clang_toolkit.matchers import functionDecl, isDefinition, isExpansionInMainFile, unless, isImplicit

with Client() as client:
    with client.match_in(
        functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("fn"),
        source,
        working_directory=project_root,
    ) as functions:
        print(f"definitions: {len(functions)}")
        for row in functions:
            fn = row.binding("fn")
            print(row.source_file, fn.decl_name, fn.decl_type,
                  row.bindings["fn"].symbol_identity)
```

Include main-file matching to avoid counting header declarations as if they were defined in this file. If the question needs header declarations too, remove that predicate and label the result as translation-unit coverage. `symbol_identity` is a Clang USR for named declarations when available; empty values cannot distinguish unrelated declarations. A USR supports deduplicating declarations seen from multiple TUs, not a whole-program reference index.

For a project-wide inventory, use only a file set supplied by the user or an SDK operation that returns the intended source paths. Query one TU at a time and close each result before advancing. Do not search the filesystem for source files or open source files in Python. For example, replace `source_files` below with the supplied paths:

```python
summaries = []
with Client() as client:
    for path in source_files:
        with client.match_in(
            functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("fn"),
            path,
            working_directory=project_root,
        ) as functions:
            for row in functions:
                fn = row.binding("fn")
                summaries.append((row.source_file, fn.decl_name,
                                  row.bindings["fn"].symbol_identity))
```

This releases each TU's retained native result after copying the summary. It avoids retaining all native snapshots at once, but it does not create a cross-TU reference index. Keep the originating path with every copied row.

## Locate a symbol and inspect child nodes

Narrow by qualified name with `hasName`, then query child declarations from the selected native binding:

```python
from clang_toolkit.matchers import functionDecl, hasName, isDefinition, parmVarDecl, callExpr

with client.match_in(functionDecl(hasName("ns::Widget::run"), isDefinition()).bind("fn"), source) as found:
    for row in found:
        fn = row.binding("fn")
        print(fn.decl_name, fn.decl_type)
        with fn.match(parmVarDecl().bind("param")) as params:
            for child in params:
                param = child.binding("param")
                print(param.decl_name, param.decl_type)
        with fn.match(callExpr().bind("call")) as calls:
            for child in calls:
                call = child.bindings["call"]
                print(call.location, call.call_site)
```

The name matcher can select overloads; use the full signature/type metadata or symbol identity when the question needs one overload. `hasName` is a name filter, not a proof of overload uniqueness.

## Inspect callers and report call coverage

First collect all call expressions and inspect their static call-site classification. Do this before filtering by target, so indirect and virtual sites remain visible in coverage:

```python
from clang_toolkit.matchers import callExpr, isExpansionInMainFile

with client.match_in(callExpr(isExpansionInMainFile()).bind("call"), source) as calls:
    counts = {"DIRECT": 0, "INDIRECT": 0, "VIRTUAL": 0, "OTHER": 0}
    for row in calls:
        site = row.bindings["call"].call_site
        key = site.DESCRIPTOR.fields_by_name["dispatch"].enum_type.values_by_number[
            site.dispatch
        ].name.removeprefix("CALL_DISPATCH_")
        counts[key if key in counts else "OTHER"] += 1
        print(site.caller_name, "->", site.static_callee_name, key)
    print(counts)
```

To list likely direct callers of a known name, query `callExpr(callee(functionDecl(hasName("ns::target"))))`, then verify `call_site.dispatch` is `CALL_DISPATCH_DIRECT` and compare the static callee identity/name. Querying all sites first is still required for completeness reporting. Calls from global initializers may have an empty caller. Lambda calls are attributed to the lambda's `operator()` when one encloses the expression.

For graph-level native edges, use `client.callgraph(source, working_directory=project_root, main_file_only=True, projection="shallow")`. Each edge indexes nodes within that response. A call-graph virtual root is a structural entry node; root edges are not claims about an external caller's runtime behavior.

## Inspect type, base, and template relationships

Check the copied `MatchBinding` value branch before reading immediate type facts. A direct base specification has its own typed branch:

```python
from clang_toolkit.matchers import cxxRecordDecl, hasName, hasAnyBase, cxxBaseSpecifier

base_match = cxxRecordDecl(
    hasName("Derived"), hasAnyBase(cxxBaseSpecifier().bind("base"))
).bind("derived")
with client.match_in(base_match, source, working_directory=project_root) as records:
    for row in records:
        binding = row.bindings["base"]
        if binding.WhichOneof("value") == "base_specifier":
            base = binding.base_specifier
            print(base.type.description.spelling, base.access,
                  base.is_virtual, base.is_pack_expansion)
```

Base specifications advertise no continuation scope. To query a base record's members, retrieve its named declaration through the native type relation:

```python
from clang_toolkit.matchers import (
    cxxRecordDecl, hasName, hasAnyBase, cxxBaseSpecifier, hasType,
    recordType, hasDeclaration,
)

derived_match = cxxRecordDecl(
    hasName("Derived"),
    hasAnyBase(cxxBaseSpecifier(
        hasType(recordType(hasDeclaration(cxxRecordDecl().bind("base"))))
    )),
).bind("derived")
with client.match_in(derived_match, source, working_directory=project_root) as records:
    for row in records:
        print(row.binding("derived").decl_name, row.binding("base").decl_name)
```

This returns base declarations that satisfy the relation; it does not claim an exhaustive base list when the query or projection is incomplete. Shallow `definition_bases` data is intentionally unrequested. For parameters, template specializations, or other child constructs, prefer follow-up matches from the bound declaration and inspect each returned protobuf's availability. Do not infer template instantiation coverage from a pattern-only result: native traversal/callgraph visitation flags control instantiation visits, and matcher traversal policy is a separate setting.

Query native template-specialization types directly to inspect alias applicability
on a top-level binding. `has_alias` is an optional boolean; false is a present
value. A non-alias specialization marks `aliased_type` INAPPLICABLE.

```python
from clang_toolkit import Matcher

type_match = Matcher("templateSpecializationType").bind("type")
with client.match_in(type_match, source, working_directory=project_root) as types:
    for row in types:
        binding = row.bindings["type"]
        if (binding.WhichOneof("value") == "node"
                and binding.node.WhichOneof("payload") == "template_specialization_type"):
            specialization = binding.node.template_specialization_type
            if specialization.HasField("has_alias"):
                print("has alias:", specialization.has_alias)
            for entry in binding.availability:
                if entry.field_path.startswith("TemplateSpecializationType."):
                    print(entry.field_path, entry.state, entry.reason)
```

## Inspect source and macro locations

For a bound match, inspect `location.valid`, `location.file`, `location.line`, and `location.column`. When macros are involved, compare `range.spelling_begin` with `range.expansion_begin`; both are copied source metadata on `MatchBinding`, not AST node fields. Coordinates use one-based physical buffer positions. Do not treat an invalid location as line zero or use a macro expansion coordinate as the spelling location.

Declaration `documentation` contains attached raw documentation when available. Ordinary comments depend on compiler comment parsing and are not an exhaustive comments inventory.

## Inspect CFG and AST call graph

```python
from clang_toolkit import Client, CfgOptions

with Client() as client:
    cfg = client.cfg(
        "ns::Widget::run", path=source, working_directory=project_root,
        projection="shallow", main_file_only=True,
        options=CfgOptions(add_implicit_dtors=True),
    )
    for graph in cfg.graphs:
        print(graph.function.qualified_name, graph.entry_block, graph.exit_block)
        for block in graph.blocks:
            print(block.block_index, len(block.elements), block.successors)

    graph = client.callgraph(
        source, working_directory=project_root, projection="shallow",
        main_file_only=True,
    )
    for edge in graph.edges:
        caller = graph.nodes[edge.caller_node]
        callee = graph.nodes[edge.callee_node]
        caller_name = ("<virtual root>" if caller.is_virtual_root else
                       caller.function.qualified_name if caller.HasField("function") else
                       caller.declaration_kind)
        callee_name = ("<virtual root>" if callee.is_virtual_root else
                       callee.function.qualified_name if callee.HasField("function") else
                       callee.declaration_kind)
        print(caller_name, "->", callee_name,
              "root-edge" if edge.is_virtual_root_edge else "call-edge")
```

`cfg` selects every concrete definition matching the exact qualified name, so overloaded functions with that same name can produce multiple graphs. Inspect each returned function symbol and its `type`/`function` signature before describing one overload; the exact qualified name does not disambiguate overloads. CFG block indices and call-graph node indices are local to that response. Check each CFG graph's `is_complete` and `availability`, and the call-graph response plus relevant node/edge `is_complete` and `availability`, before making claims from truncated semantic payloads. `main_file_only=True` narrows graph candidates and reports external call edges omitted on call-graph responses.

`client.traverse(source, working_directory=project_root, max_depth=..., max_nodes=..., projection="shallow", main_file_only=True)` provides preorder declaration/statement occurrences. Each non-root traversal item has a response-local `parent_index`; these indices describe this result's visitor structure and cannot be used as AST handles in another request. `depth_limited` reports deliberate depth pruning.

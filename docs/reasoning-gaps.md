# Reasoning with C++ through the console

The October 9 improvements address the reproduced correctness and console
adapter failures from Claude's capability report and the independent retest.
The implementation plan and verification are tracked in
[reasoning-gaps-progress.md](reasoning-gaps-progress.md). The complete syntax is
in [console-command-reference.md](console-command-reference.md).

## Run a reasoning script

Use a private or existing server endpoint with the current build and client:

```sh
uv run ctk --server unix:///tmp/ctk.sock --script analysis.ctks
uv run ctk --server unix:///tmp/ctk.sock -e 'print "ready"'
uv run ctk --server unix:///tmp/ctk.sock < analysis.ctks
```

Batch input is parsed completely before execution. Newlines or semicolons
separate statements; strings and scoped blocks retain their own syntax.
Execution stops on the first error and exits nonzero. `--continue-on-error`
executes later statements and still exits nonzero if any statement fails.
Successful text starting with `error:` remains a successful result. Batch input
bypasses the interactive editor and its completion work.

The following console examples use `examples/parse_match.cc`; substitute the
file or compilation database for the codebase being analyzed.

## Query typed rows across files

```text
let files = glob("examples/*.cc")
let functions = match functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("f") in $files
$functions.length
foreach $row in $functions do "${row.source_file}: ${row.f.decl_name} :: ${row.f.decl_type}" done
let unique = $functions.unique("f.symbol_identity").sort("f.decl_name")
foreach $row in $unique do $row.f.symbol_identity done
```

A path, a singleton list, and configured files honor the same `traversal`
setting. File lists retain independent native results with typed rows, count,
indexing, iteration and continuation. `unique` preserves the first matching
key; `sort` orders numbers numerically and strings lexically, with deterministic
mixed-type ordering. `filter("selector", expected)` selects equality matches.
These operations return ordinary lists of the original row values; one row's
binding can still be used as a native continuation target. Selectors can contain
dotted field paths. Missing or unrequested selector fields produce errors.

Retaining every file also retains its native snapshot. When only copied scalar
answers are needed, use a scoped block per file; native values that do not
survive its yield are released before the next file:

```text
let files = glob("server/src/application/*.cpp")
let summaries = foreach $file in $files do in parse $file { let rows = match functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("f"); yield foreach $row in $rows do "${row.source_file}: ${row.f.decl_name} :: ${row.f.value.node.return_type.description.spelling}" done; } done
$summaries.length
```

Use the repository compilation database for this repository example. The
12-file probe succeeds with this recipe under the default 2 GiB session budget.
Retaining all 12 native results exceeds that budget; the same typed aggregate
succeeds with an explicitly configured private 8 GiB budget. Limits remain
configurable and enforced. This recipe yields an outer list per file rather
than one flattened retained native collection.

Clang USRs distinguish overloads and allow header declarations to be deduplicated
across translation units. `symbol_identity` is empty for values that are not
named declarations or for which Clang cannot produce a USR; do not use an empty
key to distinguish unrelated values. This is a declaration identity, not a
whole-program cross-reference index.

```text
let parameters = match parmVarDecl().bind("p") in $functions.f
foreach $row in $parameters do "${row.source_file}: ${row.p.parameter_name} :: ${row.p.type_name}" done
foreach $row in $functions do (match parmVarDecl() in $row.f).length done
```

Each continuation's `source_match_index` refers to a row in its previous
**per-file** native result. It is not the flattened multi-file row index. Join
using the original parent collection, the input file and the local index. When
the continuation contains a row:

```text
let child = $parameters[0]
let file_parents = $functions.filter("source_file", $child.source_file)
let parent = $file_parents[$child.source_match_index]
$parent.f.decl_name
```

Keep the original parents for joins; sorting or deduplicating that parent list
changes its indices. Repeated input paths should be deduplicated before querying
if file provenance is used as a join key. Row metadata takes precedence over a
binding named `source_match_index` or `source_file`; access a colliding binding
through `$row.bindings["source_match_index"]`.

`save $functions to "functions.yaml"` and `load "functions.yaml" into $saved`
preserve copied semantic rows and source-file provenance. Detached snapshots
support count/index/iteration and field access through
`$saved[0].bindings.f.node`; they do not retain native continuation handles.

## Inspect availability before reading child fields

```text
let F = "examples/parse_match.cc"
let rows = match functionDecl(isDefinition()).bind("f") in $F
inspect $rows[0].f
$rows[0].f.value.node.fieldState("parameters")
$rows[0].f.value.node.return_type.description.spelling
$rows[0].f.value.node.name.fieldOr("identifier", "<nonidentifier>")
```

Match values intentionally contain immediate facts. Parameters, bodies,
operands and other child AST values can be `UNREQUESTED`; query them with a
follow-up matcher. `hasField` raises for an unrequested field, so it cannot
silently turn that omission into a claim that the C++ declaration lacks the
field. `fieldState` distinguishes presence, absence, inapplicability, unrequested,
unavailable and truncated data. `fieldOr` supplies its default for absent or
inapplicable fields, including inactive oneof branches, and raises for
unrequested, unavailable or truncated fields and misspelled names.

Names and declared types have common semantic paths for declaration kinds,
including parameters and records. Binding shortcuts `decl_name`, `decl_type`,
`parameter_name`, `record_name` and `type_name` supply scalar names/type text.

## Locate nodes and attribute calls

```text
let calls = match callExpr().bind("c") in $F
foreach $row in $calls do "${row.c.call_site.caller_name} -> ${row.c.call_site.static_callee_name}: ${row.c.call_site.dispatch}" done
$calls[0].c.location.valid
$calls[0].c.location.file
$calls[0].c.location.line
$calls[0].c.range.spelling_begin.line
$calls[0].c.range.expansion_begin.line
$rows[0].f.documentation
```

`location` and `range` are copied match metadata outside the semantic AST.
Coordinates are one-based physical source-buffer positions, valid only when
`valid` is true; `#line` remapping does not change them. Ranges expose spelling
and expansion endpoints, and points flag macro origins. Range endpoints follow
Clang's token source-range convention. Raw attached documentation is available
for declarations; ordinary comments depend on compiler comment parsing.

`call_site` records the nearest enclosing function, including a lambda's
`operator()`, rather than attributing all descendants to an outer function.
`DIRECT` identifies a statically selected nonvirtual call; explicitly qualified
virtual-method calls are direct. `INDIRECT` has no statically selected callee.
`VIRTUAL` records the selected virtual declaration while leaving the runtime
target unresolved. Global initializer calls can have no enclosing function.
Query all call sites before filtering direct callees when reporting coverage.

Selected lambda call-operator roots now traverse their body in `AsIs` mode
without duplicating body calls in whole-function traversal. Source-spelled
traversal still follows Clang's policy for implicit declarations.

## Query bases through the native matcher

For a codebase containing a `Derived` class:

```text
let bases = match cxxRecordDecl(hasName("Derived"), hasAnyBase(cxxBaseSpecifier(hasType(recordType(hasDeclaration(cxxRecordDecl().bind("base"))))))).bind("derived") in $F
foreach $row in $bases do $row.base.record_name done
```

The shallow `definition_bases` field remains explicitly unrequested. This
matcher retrieves a matching base declaration; it does not enumerate every
base automatically. String literal `value` remains byte data, preserving its
encoding rather than assuming all C++ literals contain UTF-8 text.

## Compose bounded graphs

```text
let tree = traverse $F depth 1 projection shallow main-file true
$tree.nodes.length
foreach $node in $tree.nodes do $node.depth done
$tree.depth_limited
let graph = callgraph $F main-file true projection shallow
$graph.nodes.length
$graph.edges.length
$graph.external_edges_omitted
$graph.is_complete
```

For a known function in the selected file:

```text
let flow = cfg one in $F projection shallow main-file true
$flow.graphs[0].function.qualified_name
$flow.graphs[0].blocks.length
$flow.graphs[0].entry_block
```

Console and Python graph builders default to **shallow** projection. Request
`projection recursive payload-depth 2 payload-nodes 100` for selected child
payloads. Semantic payload limits are independent of graph candidate depth,
node/edge/block limits, and the server response-byte budget. Payload-node limits
apply to each serialized semantic item; inspect availability/completeness when
reading limited expansions. Legacy raw protobuf requests that omit projection
retain recursive behavior for compatibility. Standalone graph commands retain
ProtoJSON output; assigned expressions expose typed fields.

`main-file true` scopes graph candidates to expansion locations in the main
file. A scoped call graph reports omitted external edges and is complete relative
to that requested scope. Header inclusion remains the default when this option
is omitted. Match queries use `isExpansionInMainFile()` explicitly. CFG and call
graphs remain Clang structural/static analyses rather than runtime execution
traces.

## Coverage of the reports

| Claude gap | Current resolution or analysis boundary |
|---|---|
| G1 Locations | Typed location and spelling/expansion ranges on bindings. |
| G2 Heavy payloads | Matches remain shallow; graph projection is explicit and independently bounded. Arbitrary field masks, count without materialized rows and partial publication on resource exhaustion are not added. |
| G3 Script execution | `-e`, `--script`, nonterminal stdin, line diagnostics and explicit process status. |
| G4 Collections/count | Typed aggregate/detached collections, unique/sort/filter and grouped expression counts. Arbitrary predicates and groupBy are not added. |
| G5 Common fields | Common declaration name/type fields and scalar parameter/record conveniences; child nodes use native follow-up matches. |
| G6 Absent branches | `fieldState` and `fieldOr` distinguish safe defaults from data that was never requested. |
| G7 Graph values/scope | Typed assigned traversal/CFG/callgraph values, shallow projection and main-file scope. Resource exhaustion remains an atomic error. |
| G8 Parent joins | Direct source_match_index and source_file access; join previous per-file rows explicitly. Parent bindings are not implicitly copied. |
| G9 Repository scale | Consistent bounded per-file native aggregates, independent cleanup, stable declaration keys, and existing configurable resource controls. A persistent whole-program caller/reference index is not added. |
| G10 Suspected defects | Multi-file count/navigation is fixed. Bases are unrequested, and literal bytes are intentional typed values. |
| G11 Comments/preprocessor | Attached documentation and macro spelling/expansion provenance. An includes inventory or exhaustive macro/preprocessor history is not added. |
| G12 Header scope | Explicit main-file matching/graph options preserve useful header-inclusive defaults. |

The independent review additionally found and verified fixes for selected lambda
roots, list traversal policy, discarded typed rows/provenance, hidden parent
indices, unrequested-field ambiguity, successful exits after errors and long
input completion delays. No memory leak or whole-program dynamic-dispatch
completeness is inferred from these tests.

## Evidence

Native regression tests cover lambda traversal, metadata and graph projection;
Python tests cover parsing, availability, collections, cleanup, snapshots and
batch status. Four new BDD scenarios exercise these behaviors through a real
private server. The complete-suite outcomes and independent payload/input
measurements are recorded in [reasoning-gaps-progress.md](reasoning-gaps-progress.md).

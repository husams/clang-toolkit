# Navigate retained native nodes

These console operations work with compiled, tree, and legacy engines. They use
the original pinned AST; exported JSON or detached rows cannot replace a native
binding. The native server scripting language does not gain these console forms.

## Immediate neighbours and matcher scopes

```text
peek children|parents [MATCHER] in TARGET [nodes NUMBER]
step children|parents [MATCHER] [at INDEX] in TARGET [nodes NUMBER]
match MATCHER in TARGET scope self|children|subtree
```

TARGET is a retained binding such as `$rows[0].cls`. Matchers can be inline or
saved references such as `$base_edges`. `peek` returns rows whose `.target` is the
immediate candidate and whose named bindings may refer to other nodes. `step`
returns `.target`, requiring one row unless a zero-based `at` selects it. Empty,
ambiguous, and out-of-range selections are errors; source references remain usable.
The name `target` is reserved for the navigation candidate.

Children follow immediate native visitor edges, including type locations and
implicit nodes. Parents mean AST containment, not base classes; auxiliary children
retain their visitor parent, while bare auxiliary bindings can lack parent lookup.
Navigation examines at most 10000 neighbours by default (`nodes` accepts 1..100000).
Limits and cancellation fail explicitly rather than establish absence.

`scope children` matches immediate children only; `self` tests the bound node and
`subtree` tests it and eligible descendants. Explicit scopes require retained
bindings. Nested predicates such as `hasDescendant` and `hasAncestor` keep their
normal Clang semantics: candidate scope is not a predicate traversal boundary.
Scoped matches keep automatic `root` and named bindings without adding `target`.

## List direct base classes

Run this complete script from the clang-toolkit repository root against a server
that supports navigation. The included fixture has one `demo::Leaf` definition.

```text
let tree = parse "examples/multiple_inheritance_navigation.cc"
let classes = match cxxRecordDecl(hasName("demo::Leaf"), isDefinition()).bind("cls") in $tree
let leaf = $classes[0].cls
let base_edges = cxxBaseSpecifier(hasType(cxxRecordDecl().bind("base")))
let bases = peek children $base_edges in $leaf
foreach edge in $bases do { print $edge.base.decl_name; }
let derived = step parents cxxRecordDecl() in $bases[0].target
print $derived.decl_name
let scoped = match $base_edges in $leaf scope children
print $scoped.length
```

Output: `demo::Left`, `demo::Right`, `demo::Leaf`, `2`. When adapting the script,
establish that the class match is nonempty before indexing it.

`.target` and automatic `.root` are `CXXBaseSpecifier` edges; `.base` is the
referenced class declaration. Continue inheritance traversal from `$edge.base`.
The class declaration is a semantic reference, not a containment child of its
specifier. This expression needs neither metadata filtering nor a second match
inside the loop. Whole-file and `scope self` matching still require Clang's
supported top-level matcher categories.

Clang's plain `hasType(cxxRecordDecl(...))` does not desugar a base written through
an alias. For aliases use:

```text
let base_edges = cxxBaseSpecifier(hasType(qualType(hasUnqualifiedDesugaredType(recordType(hasDeclaration(cxxRecordDecl().bind("base")))))))
```

`examples/multiple_inheritance_navigation.ctk` contains a complete ancestor walk:
append retained `.base` references to the work queue, then deduplicate the final
list by `symbol_identity`. Diamond inheritance can discover the same class twice.
Dedicated `bases`/`derived` axes and `seek` remain proposals.

## Stream or retain deliberately

Standalone `peek` streams provisional row objects and then a count. Assigned
`let bases = peek ...` is silent and exposes reusable native references only after
successful completion. Do not continue native navigation from detached streamed
payloads. Standalone `match ... do { ... }` can print scalar fields as each row
arrives; an assigned match retains native results.

`traverse TARGET [depth NUMBER] [nodes NUMBER]` accepts a path, opened file, parsed
tree, or any retained binding and streams native preorder visits. It includes the
root at depth zero; `traverse $leaf depth 0` inspects that root only. It preserves
the starting reference. Default depth is 64 (0..256), and default node budget is
10000 (1..100000). Context-dependent auxiliary values may be explicit leaves.
`let graph = traverse ...` explicitly collects semantic visit snapshots, which
are not new navigation handles. Visits remain provisional until completion and
terminal success; a node-limit failure may follow partial output.

## Maintained sources

- `docs/node-navigation.md`
- `docs/ast-traversal.md`
- `docs/console-command-reference.md`
- `examples/multiple_inheritance_navigation.ctk`
- `server/src/clang/native_navigation.cpp`
- `tests/unit/test_navigation.py`
- `tests/e2e/test_node_navigation_steps.py`
- `tests/e2e/test_node_traversal_steps.py`

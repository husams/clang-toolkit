# Navigation from bound nodes

Use an existing retained binding as the explicit starting node. Operations return
new references and preserve earlier variables; there is no current command.

    let tree = parse "examples/bound_node_navigation.cc"
    let records = match cxxRecordDecl(hasName("Box"), isDefinition()).bind("record") in $tree
    let box = $records[0].record
    let methods = peek children cxxMethodDecl() in $box
    let method = step children cxxMethodDecl(hasName("run")) in $box
    let body = step children compoundStmt() in $method
    peek children in $body
    let enclosing = step parents cxxMethodDecl() in $body
    let literals = match integerLiteral().bind("n") in $enclosing
    traverse $literals[0].n depth 0

Syntax: peek children|parents [MATCHER] in TARGET [nodes NUMBER].
Optional matchers test each immediate candidate itself; children never searches
grandchildren. Rows expose .target as the candidate plus explicit matcher
bindings. The name target is reserved for the candidate; a different nested
target binding is an error. Standalone peek streams
provisional rows, then reports the count. Assignment retains a collection using
the existing disk-backed row store when payloads grow.

Syntax: step children|parents [MATCHER] [at INDEX] in TARGET [nodes NUMBER].
Without at, exactly one row is required. Zero rows, ambiguity and an out-of-range
index are distinct errors. The index is zero-based after filtering. Selection
requires completion and terminal RPC success. Failure releases the new result
while preserving the source. Reusing $box, $method or $body returns to that saved
node. Nested matcher bindings never determine where a step moves.

Children follow native visitor edges, including implicit and type-location
entries; only depth-one candidates are enumerated. Decl/Stmt parent lookup uses
Clang's parent map and preserves multiple parents. Other supported map families
use native parent lookup. Auxiliary children selected by navigation retain their
exact visitor parent when Clang has no standalone parent-map identity. Bare
auxiliary bindings without that context fail explicitly. Parent-map construction
may inspect the full pinned tree. AST containment and inheritance are separate.

The node budget counts examined neighbours before filtering across all selected
source rows: default 10000; range 1..100000. Cancellation and limits can follow
provisional rows but never publish a successful collection. Existing server row,
per-event byte, retained-memory and snapshot limits apply. A leaf has an empty
children collection; a translation-unit root has an empty parents collection.

Python: client.peek(binding, axis="children", query="compoundStmt()") and
client.step(binding, axis="parents", at=0), with equivalent async methods.
peek accepts an on_row callback for individual provisional rows. Results preserve
caller ownership, revision guards and the original pinned snapshot, and support
continued matching, traversal and navigation without reparsing. Exported JSON
does not preserve native identity.

MatchRequest has an additive navigation axis and examined-node budget.
StreamNavigate uses the existing row/completion streaming contract.
Clients require a server supporting the new RPC.

## Match immediate children

`match MATCHER in $binding scope children` uses the same native depth-one child
walker through the ordinary streaming match RPC. It excludes the bound node and
grandchildren as outer candidates. Nested constraints such as `hasDescendant`
still inspect their normal relationships in the pinned AST context. Rows retain
the usual automatic `root` and explicit matcher bindings; this form adds no
`target` binding and reserves no matcher binding name.

Explicit scope requires a retained binding or aggregate binding selection. First
match a file or parsed tree to bind the desired root, then apply the scope to that
binding. `scope self` (alias `root_only`) and `scope subtree` expose the existing
native scopes. Omitting scope preserves the binding's original scope. Selection,
caller ownership and revision checks remain unchanged; scopes do not mutate the
source binding. Auxiliary immediate candidates retain their visitor parent for
each binding naming that candidate, so subsequent parent navigation works.

The child walker examines at most 10000 neighbours across selected source rows;
configured row, byte and retention limits also apply. Matching uses the requested
Clang matcher traversal policy against native visitor-edge candidates. Standalone
`match ... scope children do { ... }` runs its body for streamed provisional rows
with the same completion/failure contract as other match blocks.

The complete console example is `examples/match_children_scope.ctk`. It compares
two immediate methods with three recursively found methods (including the nested
class), excludes descendant literals from a method's immediate candidates, and
continues matching from the saved bindings.

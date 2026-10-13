# Match immediate children

Worktree: codex/bound-node-navigation, continuing the bound-node navigation delivery.

- [x] Add CHILDREN to the native binding-scope contract and generated bindings.
- [x] Reuse the native immediate-child visitor with ordinary match rows and binds.
- [x] Add explicit match scope syntax and preserve source references.
- [x] Add direct-versus-recursive, streaming, parent-alias and traversal-policy tests.
- [x] Finish complete native/Python/acceptance checks.
- [x] Execute the complete example in a real TTY console.

Example: examples/match_children_scope.ctk. The syntax operates on retained
bindings, including aggregate binding selections. Explicit self/root_only and
subtree use the existing scopes; omitted scope preserves the binding default.
Files and parsed trees can establish bindings first, then those nodes can be used
as explicit scoped roots. Scope limits candidate roots; matcher relationship
predicates still use the pinned AST context.

Validation: 352 native tests pass with a private TMPDIR and storage root, and
1148 Python tests pass. The complete acceptance run passed 127 cases; one SDK
case still expected base bindings to advertise no scope. It now expects CHILDREN
and exercises native type-location children through both sync and async SDKs.
The final SDK/navigation/traversal rerun passed all eight cases, covering all 128
distinct acceptance cases. An earlier native run lost an existing fixed-name
temporary fixture; the full run passed after isolating temporary files.

The real TTY console executed every statement in examples/match_children_scope.ctk
and exited successfully: two immediate methods versus three recursive methods,
one immediate return statement, zero method-level immediate literals versus one
recursive literal, two streamed method names, a self match, and reusable source
bindings. No current command is used.

Evidence: /private/tmp/ctk-children-console.log,
/private/tmp/ctk-children-native-all-isolated.log,
/private/tmp/ctk-children-python-all.log,
/private/tmp/ctk-children-e2e-all.log,
/private/tmp/ctk-children-e2e-final.log.

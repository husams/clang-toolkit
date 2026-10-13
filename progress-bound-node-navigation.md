# Bound-node navigation

Worktree: codex/bound-node-navigation, based on the tested streaming traversal delivery.

- [x] Add a streaming navigation contract with immediate children/parents.
- [x] Retain selected native nodes and preserve source ownership/revision.
- [x] Add Python peek/step and console syntax without current.
- [x] Test direct filtering, movement, ambiguity, empty results and lifetime.
- [x] Run native/Python suites and a real console demonstration.

Syntax: peek children [MATCHER] in TARGET; step children|parents [MATCHER] [at INDEX] in TARGET.
Children use native visitor edges; parents use native containment. Selection returns a new reference.

Validation: 348 native tests and 1146 Python tests pass. The complete acceptance
run passed 124 cases; two version cases failed because the fresh checkout lacked
generated client version metadata. Restoring that metadata with the normal build
helper and rerunning version checks passed all four selected cases, including both
failures. This covers all 126 distinct acceptance cases. The final navigation and
traversal rerun passed all five cases over Unix and TCP.

A real TTY console executed examples/bound_node_navigation.ctk: two immediate
methods excluding the nested method, downward steps to literal 7, streamed child
inspection, upward steps back to Box::run, and continued matching from the saved
method. Ambiguity preserves the original binding. No current command is used.

Evidence: /private/tmp/ctk-node-navigation-console.log,
/private/tmp/ctk-navigation-native-final.log,
/private/tmp/ctk-navigation-python-final.log,
/private/tmp/ctk-navigation-e2e-all.log,
/private/tmp/ctk-navigation-version-rerun.log,
/private/tmp/ctk-navigation-e2e-final.log.

Bare auxiliary nodes without native parent identity cannot provide parents;
auxiliary children selected as navigation targets retain their exact visitor
parent. Inheritance navigation remains separate future work. See
docs/node-navigation.md for semantics and limits.

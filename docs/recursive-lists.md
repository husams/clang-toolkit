# Recursive list functions

Direct self-recursive functions with list-pattern parameters compile to resumable
Python functions driven by a loop. This supports named functions and ordered
clause groups, multiple parameters, conditional branches, ordinary callbacks,
recursive calls inside larger expressions, and blocks with local bindings.
The compiled engine executes generated Python; it does not interpret body nodes.

See [the complete runnable example](../examples/recursive_lists.ctk). It implements
map and filter with tail-recursive accumulators, and reverse with non-tail
recursion followed by an ordinary list push. Actual output from the real compiled
console, also checked in real compiled/tree terminal acceptance tests:

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

## Direct Python loop specialization

The accumulator map/filter and push-based reverse forms in the example now emit
ordinary indexed Python loops. Recognition uses structure, so function and parameter
names can change. Map and filter append directly into their ordinary output list;
reverse traverses the snapshot in reverse order after accounting for descent.
There are no per-element generators, continuation requests, or saved frames on
these paths. The wrappers `map_list` and `filter_list` call the optimized accumulator
functions at fixed cost.

The exact generated functions, including execution accounting, are checked in:
[map_into](generated-list-loops/map_into.py),
[filter_into](generated-list-loops/filter_into.py), and
[reverse_list](generated-list-loops/reverse_list.py).
Their bound namespace supplies one shared execution guard per invocation. The
emitted map/filter functions are 15/16 lines and reverse is 18 lines. Traversal,
callback use, conditional filtering, and ordinary `append` calls remain visible;
source accounting and scope restoration live in the shared guard. No per-element
continuation objects are introduced.

Adjacent source steps use batched accounting when there are no cancellation hooks,
cleanup, or instrumented ticks. Exhausting a batch still fails at the exact original
source node. Other cases retain every individual cancellation/step check. Appending
an exact built-in scalar avoids allocating cycle-traversal sets; collections and
custom values retain the existing validation and diagnostics.

Each traversal takes one shallow snapshot after initial clause matching. Indexed
visits and private tail views reuse that snapshot; nested elements retain identity,
input mutation does not change subsequent visits, and appends still reject cycles.
Callback order, diagnostics, step budgets, cancellation, scopes, and the existing
reverse pending-work item limit remain enforced. Reverse has no physical pending
stack, but keeps the same logical limit and failure point. Both console engines
use this specialization.

Plain input/output lists and DSL runnable callbacks take the fast path. List
subclasses, Python callbacks, custom cancellation/observation/host hooks, foreground
resource scopes, and unrecognized function bodies retain existing execution.
If a callback replaces host evaluation during traversal, the next affected push
uses that evaluator and map/filter resume general execution with the current
lexical bindings. Standalone prototype property calls are not changed into console
`.push` calls.
The more general continuation transformation below remains available for other
recursive forms.

## Execution and sharing

A direct self call in tail position replaces the current execution frame.
A non-tail self call suspends a generated Python function, stores it on an
explicit continuation stack, and resumes it with the child's result. Neither
path grows the Python call stack with the list length. Tail calls retain no continuations; repeated console observations from one
source location are compressed. Non-tail calls retain the pending work and use
linear space in depth.
Ordinary argument evaluation order, clause order, checked arithmetic, execution
budgets and cancellation remain enforced.

Internal tails use a backing list plus start/stop offsets. Passing a tail directly
to another self call does not slice or copy it. Successful pattern matching
isolates borrowed tails on one private shallow snapshot per exposed backing list,
before any body operation or runtime hook can mutate that input. Subsequent
tails share the private backing. This preserves the independent-tail behavior
of ordinary pattern matching, including custom scalar operations and cancellation
hooks. Traversing an existing tail chain uses one linear-size snapshot, rather
than a new copy at every recursion level. Reintroducing a plain list as another
matched argument can require another snapshot; this does not promise linear
total space for arbitrary recursion. The smaller numeric specialization still
needs no copy.

Reading or escaping a tail through ordinary user code materializes a real list
and retains that list's identity for aliases and subsequent mutation. Closures
capturing a tail receive a real list. Nested elements retain their identity:
these are shallow-list semantics, not deep copies. List subclasses keep their
own slicing behavior rather than using plain-list cursors. Custom pattern
length, indexing and type hooks trigger the same snapshot protection before
they can mutate another matched argument.

## Boundaries

This transformation targets direct self calls in supported expressions and
blocks, not mutual recursion or recursion hidden inside opaque operations.
Defaults, keyword arguments around recursive calls, handlers/loops enclosing
recursive calls, and lexical self rebinding conservatively retain normal
execution. Arbitrary `Context.statement_observer` hooks also retain normal
execution because they can inspect and mutate every logical frame. These
fallbacks retain the ordinary 64-call depth limit.

Tail materialization and snapshots still allocate when an observable list is
needed. This does not optimize the cost of user-written output construction:
repeatedly flattening growing lists can remain quadratic. The supplied
accumulator/push examples avoid that cost. The numeric `total` specialization
remains available as its smaller indexed-loop fast path.

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

## Execution and sharing

A direct self call in tail position replaces the current execution frame.
A non-tail self call suspends a generated Python function, stores it on an
explicit continuation stack, and resumes it with the child's result. Neither
path grows the Python call stack with the list length. Tail calls retain no continuations; repeated console observations from one
source location are compressed. Non-tail calls retain the pending work and use
linear space in depth.
Ordinary argument evaluation order, clause order, checked arithmetic, execution
budgets and cancellation remain enforced.

Internal tails use an input list plus start/stop offsets. Passing a tail directly
to another self call does not slice or copy it. Before an opaque callback, host
operation, or callable-signature check can mutate an exposed backing list, all
live tails sharing that backing are redirected to one private shallow snapshot.
Subsequent tails share the private backing. This prevents mutation of the
original input from changing a tail that ordinary pattern matching already copied.

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

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
ordinary Python loops. Recognition uses structure, so function and parameter
names can change. Map and filter append directly into their ordinary output list;
reverse traverses the snapshot in reverse order after accounting for descent.
There are no per-element generators, continuation requests, or saved frames on
these paths. The wrappers `map_list` and `filter_list` call the optimized accumulator
functions at fixed cost.

For proven pure scalar callbacks, the compiler now selects direct `for`/`append`
loops with native arithmetic. The actual selected Python for the example is:
[map](generated-list-loops/plain_map.py),
[filter](generated-list-loops/plain_filter.py), and
[reverse](generated-list-loops/plain_reverse.py).
The generated functions contain only the ordinary transform/filter/append kernel.
One shared runtime runner calls the kernel once per nonempty chunk of at most 128
items and owns cancellation polls, exact source accounting and observer updates.
Filter returns its last predicate result for observer settlement; accepted counts
come from the output-length delta. Reverse's runner supplies elements in reverse
order, so its kernel uses the same ordinary forward `for` loop over that input.
The callable wrappers and one invocation guard still perform argument validation,
snapshotting and scope restoration outside those loops.

Before traversal, a single scan proves exact input types and integer bounds for
every callback subexpression. Supported map/filter expressions use one integer
parameter, literals, unary signs, arithmetic `+`, `-`, `*`, comparisons, boolean
negation and remainder by a nonzero literal. Remainder preserves the DSL's sign
rule for negative dividends. Interval proofs reject potentially overflowing
intermediate arithmetic. Scalar reverse needs no callback. Nested collections,
custom values, effects, dynamic callbacks and unsupported expressions use the
existing guarded execution, preserving identity, cycle checks and diagnostics.

The compiler hoists a conservative bound on the complete source-step cost. If the
remaining budget cannot cover it, the original guarded loop preserves the exact
first failing source node and partial output. The shared runner settles step
counts once per chunk of at most 128 elements; filter derives kept-item counts
from the output-length delta. Observer updates also happen outside the inner
loop. Reverse accounts for logical descent in one operation and unwind in
chunks, preserving its pending-work item limit without allocating a pending
stack. Each inner loop only evaluates the proven scalar expression or predicate
and appends. A persistent iterator feeds `islice` chunks without copying chunk
lists or revisiting the start of the snapshot. No per-item runtime guard,
callback invocation, scope dictionary or continuation is needed on the plain path.

Standard cancellation events are polled before each chunk and every 128 items
during the initial proof scan. Map/filter also poll before their base clause;
reverse polls before compressed descent. Cancellation remains cooperative: a
running chunk can finish at most 128 pure item operations before the next poll,
and the final reverse chunk can complete without another poll. Completed chunks
settle their exact source-step counts and observer state before cancellation is
reported. This path does not poll at every logical source tick. Custom hooks,
instrumented tick methods,
replaced callbacks and custom observers retain guarded execution with their
original ordering. The standard console observer's internal tail state is
updated directly; externally observable statement handling stays on the guarded
path. Original source locations and execution state are restored on exit.

The general compact dispatchers remain checked in for comparison:
[map_into](generated-list-loops/map_into.py),
[filter_into](generated-list-loops/filter_into.py), and
[reverse_list](generated-list-loops/reverse_list.py).

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

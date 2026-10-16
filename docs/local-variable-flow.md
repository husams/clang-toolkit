# Track a local variable through a function

`variableflow VARIABLE in FUNCTION` reuses two retained native bindings from the same parsed snapshot. It reports usage sites, possible reaching assignments at reads, initialization before each operation, and whether an assigned value can be read later before overwrite or exit. Shadowed names have distinct declaration identities.

Run the checked-in example with the compiled CTK console:

```text
ctk --script examples/local_usage.ctk
```

The source is [local_usage.cc](../examples/local_usage.cc); the complete script is [local_usage.ctk](../examples/local_usage.ctk). Its core operation is:

```text
let tree = parse "examples/local_usage.cc"
let functions = match functionDecl(isDefinition(), hasName("example")).bind("f") in tree
let variables = match varDecl(hasLocalStorage(), hasName("x")).bind("v") in functions[0].f
let report = variableflow variables[0].v in functions[0].f
print report
```

In this example, `x` is declared on line 4. Only the true branch assigns 10 on line 5, so line 6 has both a reaching assignment and an uninitialized possibility. The value assigned on line 7 is overwritten on line 8 before any read. The final read on line 9 receives the line 8 assignment.

The collected report contains `analysis`, `usages`, `facts`, `findings` and `completed`. Facts reference usage IDs; zero in `reaching_assignments` denotes an uninitialized possibility. `initialization` describes the state **before** the usage, including before writes. Native block and element positions determine execution order within a block; event IDs follow block order, which differs from source order. The example sorts usage locations for display. Its [actual terminal output](../examples/local_usage.output.txt) is checked in alongside the script.

Standalone commands stream `started`, provisional `usage` records, converged `fact` and `finding` records, then `completed`. Assignment explicitly collects the stream. Require terminal success and `completed.is_complete` before treating the requested analysis as complete. A resource error or cancellation can follow provisional records without completion. Unsupported storage effects produce incomplete completion and unknown facts without clean initialization or dead-store conclusions. An unsupported numeric expression invalidates numeric facts while preserving the separately supported initialization and liveness results.

The native server builds a CFG with individual expression steps and exception edges, computes forward reaching assignments to a fixed point, then backward may-liveness. It follows graph-reachable edges, including loops and short circuit paths. Witness block routes establish CFG reachability; correlated branch conditions may make a route infeasible at runtime. Calls use the graph's return/exception flow and do not expand callee bodies.

Supported scope: automatic, direct non-volatile integer and Boolean locals in CTK's supported C++ language modes; declarations and initialization, assignments, read-modify-write operations, branches, loops and short circuit expressions. Address taking, reference binding, captures, volatile access, catch parameters, cleanup attributes, assembly, coroutine effects, non-local jumps, indirect calls, unmodeled lvalue uses and unmodeled evaluation order produce explicit unknown/incomplete results. Pointers, references, non-integer types and alias/interprocedural effects are outside this model. A selected variable must belong to the selected concrete function definition.

`blocks` bounds CFG blocks (default 10,000; maximum 100,000). `events` bounds **all emitted events**, including metadata, facts and completion (default 10,000; maximum 100,000). `iterations` bounds analysis work, convergence and witness searches (default 100,000; maximum 1,000,000). Each event must fit the configured server message size. Native state and element counts also have fixed memory/work bounds. Retained references are checked for client ownership, revision and lifetime; invalid references never trigger reparsing.

Python provides async `variable_flow_stream(variable, function)`, callback `stream_variable_flow(variable, function, on_event=...)` and explicit collector `variable_flow(variable, function)`. The synchronous client supports callback streaming and collection. Close async iterators with `aclosing` when stopping early. Callbacks apply backpressure; finish or cancel before issuing another native query against the same snapshot, whose execution lane remains locked during streaming.

## Numeric value ranges

Add `values interval` to request inclusive numeric bounds before and after each usage:

```text
let report = variableflow variables[0].v in functions[0].f values interval
```

Run `ctk --script examples/value_ranges.ctk` from the repository root with the built server. The complete [loop and branches script](../examples/value_ranges.ctk) analyzes [value_ranges.cc](../examples/value_ranges.cc); its [actual terminal output](../examples/value_ranges.output.txt) is checked in. It follows `total` through two updates and a cap. The converged loop header and return have bounds `[0, 10]`; updates may temporarily reach 12 before clamping. Each row combines possible visits to a source site. Intervals can include values that no concrete execution produces, and unknown guards explore both edges. The model tracks the selected local without preserving relationships with other variables.

`analysis.value_domain` acknowledges `INTERVAL`. Each fact contains `value_before` and `value_after`, with `kind` equal to `INTERVAL`, `UNINITIALIZED`, `UNREACHABLE` or `UNKNOWN`. Interval `lower` and `upper` are inclusive, exact decimal strings; singleton intervals represent constants. `UNINITIALIZED` never means zero. Existing initialization facts remain separate: an interval describes initialized routes even when another route is uninitialized. Numeric reachability describes defined executions; an uninitialized read can remove all numeric routes while preserving the initialization warning.

The first numeric scope is direct non-volatile signed integers up to 128 bits, constant assignment, addition/subtraction, increments, supported integer conversions and comparisons. Integer promotions and computation types come from Clang. Unknown inputs of supported integer types retain their full type range. Unsupported input types, arithmetic or conversion, unsigned wrapping or potential signed overflow produce a finding, `UNKNOWN` numeric facts and incomplete completion. An unsupported input never means an unreachable route. Pointers, floating point, aliases and interprocedural value reasoning remain outside this model. Calls returning a supported integer type can supply an unknown input; their bodies are not expanded.

Native interval propagation refines comparison edges and joins routes. Delayed widening to type bounds ensures bounded growth, followed by narrowing to a stable result. Provisional widening states are never published as numeric facts. Existing work, cancellation, event-byte and count limits also cover the numeric pass, and expression recursion is limited to 128 levels. Finish the stream and check completion before relying on the report.

Python callers pass `value_domain="interval"` to the same collector, callback or async-iterator methods. Without this argument or the console clause, numeric fields remain absent. A requested domain or missing/malformed numeric payload that the server fails to acknowledge is rejected by the Python stream validator.

# Console library compilation and execution

Startup previously cached the parsed library tree only. Every fresh runtime
prepared that tree, parsed interpolation expressions, lowered the program and
embedded host blocks, compiled Python, and generated its source listing again.
The combined Earley parser is also expensive on complex libraries: profiling the
installed 209-line helper library remained inside parsing for several minutes
and was interrupted. Cold compilation of that library is still a limitation;
these changes target repeat startup and execution, without changing the grammar.

The compiled engine now attempts a disk lookup before lowering a library,
interpolation expression, or embedded host block. The cache contains generated
Python, interpreter-specific bytecode, and paths addressing operands in the
current prepared syntax tree. It does not persist runtime bindings, closures,
resources, or live host metadata. Import order, repeated assignment effects,
validation, rollback, source locations, and resource limits still apply.

The existing content/runtime fingerprint invalidates both syntax and executable
entries. Files are written atomically; malformed, unavailable, oversized or
unsafe executable entries are ignored. Executable files and their containing
cache directory must belong to the current user and exclude other writers.
Syntax and executable caches each retain at most 128 entries, with a 16 MiB
limit per entry. The tree engine retains its syntax-only cache.

Generated expressions no longer allocate a lambda just to charge an execution
step. A left-to-right Python expression charges the step before evaluating its
value. Boolean operations use Python short-circuiting with the existing checked
boolean conversions. Binding lookup/definition call the context directly;
property and index evaluation no longer need argument closures. Redundant
runtime helpers have been removed. Arithmetic, collection, scope and resource
checks remain because they implement the scripting language's semantics.

## Reproduce the measurements

```sh
uv run python scripts/benchmark_console_startup.py
uv run python scripts/benchmark_console_startup.py --library-dir ~/.ctk/lib
```

Each run starts with an empty temporary disk cache. The reported startup interval
includes runtime construction and library preload after module imports; it is
not a full terminal-launch measurement. Warm samples use fresh runtimes and the
same disk cache. Runtime samples reuse one context per sample to avoid measuring
context setup instead of expression execution.

Against baseline commit `97c4671`, a four-definition library containing arithmetic,
interpolation, short-circuiting and indexing gave these initial measurements:

| Measurement | Before | After |
| --- | ---: | ---: |
| Median warm runtime construction and preload, 3 samples | 208.6 ms | 3.28 ms |
| Median 20,000 arithmetic evaluations, 7 paired samples | 194.2 ms | 153.7 ms |

The runtime samples alternated baseline and changed compilers in the same
process using the same semantic implementation. Warm preload improved about
64 times; expression execution improved about 26 percent. These are local
microbenchmarks collected while validation was running, not general speedup
guarantees. No numerical improvement is claimed for cold parsing of the installed
helper library.

## Validation

Focused tests cover warm reuse without parsing/lowering, fresh bindings and
closures, host metadata, interpolation, nested imports, slice bounds, damaged
artifacts, permissions, source/compiler invalidation, pruning, rollback, execution
limits and tree/compiled engine equivalence.

The complete native suite was run against the existing unchanged native build:
409 passed and 113 failed out of 522. Failures include worker exits, snapshot
cache expectations and type/Clang assertions. The complete Python end-to-end
suite reported 29 passed and 188 failed; server fixtures report socket binding
rejected with `Operation not permitted`. These runs do not establish a green
native or end-to-end baseline. No C++ or API files are changed by this work.

The full Python unit suite was split across four pytest processes: 3,433 tests
passed, three failed and one was skipped. One failure was the generated-help
reference mismatch introduced by the documentation update; the source help entry
was corrected, and all 97 help tests then passed. The remaining two failures are
Darwin/Linux managed-server lifecycle checks. Both also fail on the untouched
baseline checkout: process inspection through `ps` is denied by this session,
so status cannot recognize the test server. The final focused run passed 128
tests; the final cache-only rerun passed all 20 tests after adding malformed-body
coverage. Whitespace validation passed.

Implementation lives on `perf/console-script-cache` in an isolated worktree.
The session could not write the original repository's Git metadata or create
its normal worktree, so a shared clone and its worktree were created under
`/tmp`. The original checkout's source and existing untracked files were
preserved.

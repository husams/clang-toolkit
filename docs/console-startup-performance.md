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
Libraries, interpolation templates and embedded blocks have separate cache
namespaces. Syntax and executable caches in each namespace retain at most 128
entries, with a 16 MiB limit per entry. Interpolation cannot evict a library's
parsed program. The tree engine uses syntax caching for programs and compiled
caching for interpolation.

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

Each run starts with an empty temporary disk cache. Every preload sample runs
in a new Python process. The process interval includes interpreter startup,
module imports, runtime construction, preload and process exit; the separately
reported preload interval excludes interpreter startup and imports. This does
not measure terminal setup or a server connection. Warm samples share only the
disk cache. Runtime samples reuse one context per sample to avoid measuring
context setup instead of expression execution.

Against baseline commit `97c4671`, a four-definition library containing arithmetic,
interpolation, short-circuiting and indexing gave these initial in-process measurements (before the fresh-process benchmark was added):

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

## Follow-up review

The review found and fixed two issues:

- Interpolation expressions and embedded block artifacts shared the library's
  cache budget. With a budget of two, one library containing two interpolation
  expressions evicted its own parsed program and reparsed at every startup.
  Separate library, template and block namespaces now preserve their independent
  working sets. Regression tests disable parsing and lowering during the warm
  load, including a library with two actual embedded batch blocks.
- Cache loading checked a pathname and then reopened it, and did not exclude
  non-regular files. A FIFO at a cache pathname could block startup. Reads now
  open without following symlinks and without blocking on FIFOs, check ownership,
  permissions, file type and size on the opened descriptor, and bound the read.
  Reads, atomic publication and pruning operate relative to a checked directory
  descriptor. Tests cover path replacement, FIFO recovery, untouched symlink
  targets and concurrent writers.

A new subprocess regression proves that cached syntax and bytecode are usable
in a different Python process without parsing or lowering and with fresh
argument bindings. The benchmark now launches a new interpreter for every
sample and reports both process lifetime and preload time. It also keeps cache
environment overrides local to the worker processes.

One local run of the reviewed code measured a 3.38-second cold process lifetime
and a 2.21-second median warm process lifetime. The preload portions were
1.035 seconds and 23 milliseconds respectively. Imports, interpreter startup,
and process exit remain outside the preload timing. These observations are
not a before/after speedup comparison and do not measure an interactive console
or server connection. The earlier 64-times figure applies only to the original
in-process preload microbenchmark.

Review validation: the complete Python unit suite, excluding the two previously
confirmed environment-blocked `test_server_lifecycle.py` cases, passed 3,442
tests with one skip. A final focused run covering cache, compiler, preloads,
handlers and generated help passed all 235 tests, including the additional
embedded-block and concurrent-writer regressions. Whitespace checks passed.
No C++ or protocol code changed during this review; the earlier native and
end-to-end validation limitations remain.

## Time until the console accepts input

The later startup investigation measured the actual workspace's first frame
and the redraws after two typed characters. The remaining delay came primarily
from building the legacy command parser during help import, followed by
synchronous autocomplete parser construction on the first keystroke. Loading
the installed, cached 209-line helper library took approximately 30-70 ms.

Help now documents the shipped native analysis grammar directly, removing the
old optional-extension probe and fallback descriptions. Contextual help uses
the active editor's tokenizer and updates only while its panel is visible.
Autocomplete runs through prompt_toolkit's threaded completion support so
grammar initialization and field discovery do not block input or redraws.

The investigation also reproduced a startup deadlock when a connection error
was printed before the workspace application was running. Rich's capture flush
re-entered the workspace stdout bridge while its printing lock was held.
Markdown rendering now uses a private in-memory output stream.

To reproduce the input measurements:

```sh
uv run python scripts/benchmark_console_input.py
uv run python scripts/benchmark_console_input.py --lib-dir ~/.ctk/lib --samples 3
```

Each sample launches a new Python process and runs the real workspace with
pipe input and a headless 140-column screen. It measures imports, history,
runtime construction, installed library preloading, layout, completion and key
redraws. It excludes uv and interpreter startup, terminal drawing, and backend
connections. Existing library caches are reused. No commands are submitted.

Three local samples against the previous review commit `20a113f` gave:

| Median time from worker start | Before | After |
| --- | ---: | ---: |
| First workspace frame | 1.201 s | 0.392 s |
| First typed character displayed | 1.964 s | 0.415 s |
| Second typed character displayed | 1.974 s | 0.444 s |

Cold autocomplete suggestions can still take longer than typing because the
completion parsers are initialized in the background. Cold library parsing
remains a separate limitation. These results do not promise identical terminal
or server behavior on other machines.

All 316 focused console tests passed, including new regressions for help imports
without parser construction, typing and redraws during blocked completion in
both engines, contextual help visibility/tokenization, and the redirected
output deadlock. The native server connection could not be validated in this
session because the environment rejected the Unix socket connection.

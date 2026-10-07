# Interactive console improvements

Scope: console help/completion, related grammar/runtime integration, documentation,
and tests. Base HEAD: `59e8ad7150551a9da0e9406530ffb70a9db506a3`.
Existing native analysis/cache changes and swap-file deletion are preserved.
The user subsequently authorized a scoped commit and local main integration;
remote pushing remains unauthorized.

## Story 1 — Detailed local help

- [x] Inspect current grammar/runtime and wiki guidance (the runtime wiki plan is stale).
- [x] Implement `help <topic>` and `<topic>?` through Lark, with offline usage,
  arguments/defaults/examples for declarative and legacy commands.
- [x] Verify local unknown-topic errors and document the complete supported surface.

## Story 2 — Contextual filesystem completion

- [x] Identify filesystem argument positions in the current grammar.
- [x] Add role-specific completion for files/directories with quoting and navigation.
- [x] Test relative/absolute/home paths, spaces, unfinished strings, and errors;
  preserve matcher/reference completion.
- [x] Exercise actual prompt input, BDD, and a real PTY; run Python and C++ gates.

## Verification

Both stories are implemented and verified. No C++ source was changed by this task.

- Python unit regression: **344 passed**.
- Full native/local BDD regression: **46 passed** (with permitted local socket access).
- Final focused console BDD rerun after the final behavior edits: **11 passed**.
- Ruff checks for task-owned edits and `git diff --check`: passed.
- `cmake --build --preset dev` and `dev-noclang`: passed, including serializer coverage.
- C++ `dev-noclang`: **109/109 passed** with local socket access.
- C++ `dev`: **242/248 passed** across the initial run and unrestricted rerun.
  Five network failures were sandbox socket restrictions and passed unrestricted.
  The six native-cache failures below persist unrestricted; the broader gate is
  **not green** and belongs to the existing unrelated native-cache work:
  - `ClangQuery.ReloadsValidatedNativeAstFromStorageAfterMemoryCacheReset`
  - `ClangQueryRegressions.CorruptStoredArtifactFallsBackToSourceParsing`
  - `ClangQueryRegressions.SessionPinKeepsLoadedArtifactUntilEngineDestruction`
  - `SnapshotClosure.CapturesHeadersAndReusesOnlyStronglyMatchingContent`
  - `SnapshotClosure.CapturesAndReloadsExplicitPchClosure`
  - `SnapshotClosure.CapturesAndReloadsNamedModuleClosure`
  These expect native artifacts/storage hits that the current dirty native code
  does not produce. No native-cache fix or unrelated staging was attempted.
- Real PTY, no running server: `help match`, `cursor open?`, unknown command/topic,
  Tab insertion into an unfinished quoted path with spaces, directory selection,
  typing a child prefix after the closing quote and Tab completion, then real
  `load ... into $name` and value display all succeeded. Clean `quit` exited 0.
- Initial `uv run` failed because its default cache was outside the sandbox;
  checks used the existing project environment, and the final unit gate also
  passed via `UV_CACHE_DIR=/tmp/ctk-console-uv-cache uv run --no-sync pytest tests/unit -q`.
  Socket tests passed once run
  with approved local socket access; restrictions are distinct from the six
  remaining native-cache product/test failures.

## Sources and delivery

- Current `cli/grammar.lark`, `cli/runtime/`, native analysis option defaults and
  generated protobuf descriptors drove the help reference; every help example
  is parsed in a test. [Command reference](docs/console-command-reference.md)
  is generated from the same `CommandHelp` entries and checked for drift.
- Consulted [wiki runtime plan](../wiki/pages/planning/clang-toolkit-interactive-runtime.md)
  and its wiki guidance/index before implementation; its transport/implementation
  boundary is historical, so current source and executed tests were authoritative.
- Preserved existing edits in shared grammar, highlighter, evaluator, completion
  candidates and REPL docs; compared with saved pre-task copies where applicable.
  The existing swap-file deletion remains. The scoped console commit integrates
  these stories into local main; nothing has been pushed.

## Local main integration

The shared checkout is already on main. Other project chats are idle, with no
active Git owner or staged edits observed. A separate candidate tree based on
the published HEAD excludes the pre-existing native grammar/adapter/highlighter
changes and unrelated native/client work. Help derives native option availability
from the current formal grammar, so the standalone commit does not advertise
unpublished extensions. The dirty checkout retains their detailed native help.
Legacy unavailable CFG/callgraph hooks report useful local errors.

Clean candidate validation (no uncommitted native modules or client edits):

- **327 Python unit tests passed**; **35 BDD tests passed** against a freshly
  built server using only published C++ source in the isolated candidate.
- Native build and scoped Ruff checks passed. Offline help, unavailable legacy
  analysis diagnostics, Tab completion of an unfinished quoted filename,
  loading that file and value display passed in a real isolated PTY.
- **216/219 C++ tests passed**. The published C++ source independently reproduces
  the three existing `ClangQuery`/`ClangQueryRegressions` artifact/storage-hit
  failures listed above. This confirms they are unrelated to console changes;
  the native cache gate remains not green.
- Initial fresh configuration hit sandbox DNS restrictions fetching ANTLR;
  reusing the already available, version-matched runtime and GoogleTest sources
  allowed the independent build without changing project dependencies.

Only the 19 console code/grammar/help/completion/test/documentation/progress
files are included. Shared files are staged by scoped patches against published
HEAD. Native extension hunks and generated native-help overlays remain in the
working tree with the unrelated native work. The commit containing this record
integrates the validated console changes directly into existing local main;
there is no branch switch or remote push.
